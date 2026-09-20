from dataclasses import replace
from math import nextafter
from pathlib import Path
from uuid import uuid4

import pytest

from backend.adapters.features.artifacts import decode_context, encode_context, write_context
from backend.adapters.rules.__main__ import main
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import extract_features
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.rules.engine import (
    DEFAULT_POLICY,
    RulePolicy,
    RuleStatus,
    evaluate_context,
    evaluate_rules,
    report,
    specifications,
)
from backend.app.transaction.entities import Transaction


@pytest.fixture
def context(transaction: Transaction, profile: CustomerBehaviorProfile) -> FeatureContext:
    return FeatureContext(
        uuid4(),
        transaction,
        profile,
        "UTC",
        (),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )


def changed(context: FeatureContext, **updates: float) -> FeatureVector:
    vector = extract_features(context)
    values = dict(zip(vector.names, vector.values, strict=True))
    values.update(updates)
    return replace(vector, values=tuple(values[name] for name in vector.names))


@pytest.mark.parametrize(
    "value,matched", [(nextafter(10, 0), False), (10, True), (nextafter(10, 11), True)]
)
def test_amount_boundary(context: FeatureContext, value: float, matched: bool) -> None:
    vector = changed(context, amount_vs_customer_median=value)
    result = evaluate_rules(vector)
    assert (result.outcomes[0].status == RuleStatus.MATCHED) is matched
    assert specifications(DEFAULT_POLICY)[0].evaluate(vector) == result.outcomes[0].reason


@pytest.mark.parametrize("count,matched", [(4, False), (5, True), (6, True)])
def test_velocity_boundary(context: FeatureContext, count: int, matched: bool) -> None:
    vector = changed(
        context,
        transactions_last_5_min=count,
        transactions_last_10_min=count,
        transactions_last_hour=count,
        activity_history_count=count,
        activity_history_missing=0,
    )
    assert (evaluate_rules(vector).outcomes[2].status == RuleStatus.MATCHED) is matched


def test_cold_start_is_not_a_clean_verdict(context: FeatureContext) -> None:
    result = evaluate_context(replace(context, profile=None))
    assert all(item.status == RuleStatus.NOT_EVALUATED for item in result.outcomes)
    assert result.reasons == ()
    assert result.outcomes[0].missing_indicators == ("profile_missing", "baseline_insufficient")


def test_all_reasons_order_evidence_and_missing_masks(context: FeatureContext) -> None:
    vector = changed(
        context,
        amount_vs_customer_median=20,
        new_recipient=1,
        unusual_hour=1,
        typical_hours_missing=0,
        device_changed=1,
        device_change_missing=0,
        activity_history_missing=0,
        activity_history_count=6,
        transactions_last_5_min=6,
        transactions_last_10_min=6,
        transactions_last_hour=6,
    )
    result = evaluate_rules(vector)
    assert [r.code for r in result.reasons] == [
        "AMOUNT_ANOMALY",
        "NEW_RECIPIENT",
        "HIGH_VELOCITY",
        "UNUSUAL_TIME",
        "DEVICE_CHANGED",
    ]
    assert result.reasons[0].message == (
        "Amount is 20 times the admitted long-window median (threshold 10)."
    )
    assert result.outcomes[2].observed == 6
    masked = changed(
        context, device_changed=1, device_change_missing=1, unusual_hour=1, typical_hours_missing=1
    )
    assert evaluate_rules(masked).outcomes[3].status == RuleStatus.NOT_EVALUATED
    assert evaluate_rules(masked).outcomes[4].status == RuleStatus.NOT_EVALUATED


def test_policy_fingerprint_and_replay(context: FeatureContext) -> None:
    replay = decode_context(encode_context(context))
    assert report(context) == report(replay)
    assert RulePolicy(10, 5).fingerprint == DEFAULT_POLICY.fingerprint
    assert RulePolicy(11, 5).fingerprint != DEFAULT_POLICY.fingerprint
    assert RulePolicy(10, 6).fingerprint != DEFAULT_POLICY.fingerprint
    vector = changed(context, amount_vs_customer_median=10)
    assert evaluate_rules(vector).outcomes[0].status == RuleStatus.MATCHED
    assert evaluate_rules(vector, RulePolicy(11)).outcomes[0].status == RuleStatus.NOT_MATCHED


@pytest.mark.parametrize(
    "ratio,count", [(1, 5), (float("nan"), 5), (float("inf"), 5), (10, 0), (10, 1.5), (10, True)]
)
def test_invalid_policy(ratio: float, count: int) -> None:
    with pytest.raises(ValueError):
        RulePolicy(ratio, count)


@pytest.mark.parametrize("kind", ["version", "order", "flag", "negative", "count", "velocity"])
def test_incompatible_vectors(context: FeatureContext, kind: str) -> None:
    vector = extract_features(context)
    if kind == "version":
        vector = replace(vector, version="behavior-v2")
    elif kind == "order":
        vector = replace(vector, names=tuple(reversed(vector.names)))
    elif kind == "flag":
        vector = changed(context, new_recipient=0.5)
    elif kind == "negative":
        vector = changed(context, amount=-1)
    elif kind == "count":
        vector = changed(context, long_history_count=1.5)
    else:
        vector = changed(context, transactions_last_5_min=1)
    with pytest.raises(ValueError):
        evaluate_rules(vector)


def test_cli_replay_without_database(
    context: FeatureContext,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import json

    path = tmp_path / "context.json"
    write_context(path, context)
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", "invalid")
    monkeypatch.setenv("FRAUDLENS_API_PRINCIPALS", "invalid")
    assert main([str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["rule_version"] == "rules-v1"
    assert output["thresholds_calibrated"] is False
    assert output["policy_sha256"] == DEFAULT_POLICY.fingerprint
    assert main([str(path), "--amount-median-ratio", "nan"]) == 1
    assert main([str(tmp_path / "missing")]) == 1
