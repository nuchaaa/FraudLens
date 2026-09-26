import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from backend.adapters.features.artifacts import write_context
from backend.adapters.sequence.__main__ import main
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.rules.engine import RuleStatus, evaluate_context
from backend.app.sequence.engine import (
    DEFAULT_SEQUENCE_POLICY,
    SequencePolicy,
    SequenceStatus,
    evaluate_sequence,
)
from backend.app.transaction.entities import Transaction


def verified(profile: CustomerBehaviorProfile) -> CustomerBehaviorProfile:
    return replace(
        profile,
        admission_workflow_verified=True,
        admission_policy_version="profile-learning-v1-experimental",
        learning_decision_id=uuid4(),
    )


def context_with_amounts(
    candidate: Transaction,
    profile: CustomerBehaviorProfile,
    amounts: tuple[str, ...],
    *,
    recipient=None,
) -> FeatureContext:
    recipient = recipient or candidate.recipient_id
    activity = tuple(
        replace(
            candidate,
            transaction_id=uuid4(),
            amount=Decimal(amount),
            recipient_id=recipient,
            timestamp=candidate.timestamp - timedelta(minutes=len(amounts) - index),
        )
        for index, amount in enumerate(amounts)
    )
    return FeatureContext(
        uuid4(),
        candidate,
        verified(profile),
        "UTC",
        activity,
        candidate.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )


def test_low_and_slow_sequence_matches_while_amount_rule_does_not(transaction, profile):
    candidate = replace(transaction, amount=Decimal("25000"), recipient_id=uuid4())
    context = context_with_amounts(candidate, profile, ("10000", "15000", "20000"))
    rules = evaluate_context(context)
    sequence = evaluate_sequence(context)
    assert rules.outcomes[0].status == RuleStatus.NOT_MATCHED
    assert sequence.outcomes[0].status == SequenceStatus.MATCHED
    assert sequence.outcomes[0].observed_count == 4
    assert sequence.outcomes[0].observed_amount == Decimal("70000")
    assert sequence.outcomes[0].observed_cumulative_ratio == Decimal("70000") / Decimal("30000")
    assert sequence.outcomes[0].observed_growth_ratio is None
    assert sequence.thresholds_calibrated is False
    assert sequence.reasons[0].code == "CUMULATIVE_LOW_VALUE_SEQUENCE"


def test_gradual_escalation_and_cumulative_exposure_are_separate(transaction, profile):
    candidate = replace(transaction, amount=Decimal("40000"))
    context = context_with_amounts(candidate, profile, ("10000", "20000", "30000"))
    outcomes = evaluate_sequence(context).outcomes
    assert outcomes[1].status == SequenceStatus.MATCHED
    assert outcomes[3].status == SequenceStatus.NOT_MATCHED
    assert outcomes[1].observed_growth_ratio == Decimal("4")
    assert outcomes[1].reason is not None
    assert "strictly increase" in outcomes[1].reason.message


def test_repeated_recipient_requires_absence_from_trusted_profile(transaction, profile):
    new_recipient = uuid4()
    candidate = replace(transaction, amount=Decimal("10000"), recipient_id=new_recipient)
    context = context_with_amounts(candidate, profile, ("9000", "9500"), recipient=new_recipient)
    outcome = evaluate_sequence(context).outcomes[2]
    assert outcome.status == SequenceStatus.MATCHED
    known = replace(candidate, recipient_id=profile.observations[0].recipient_id)
    known_context = context_with_amounts(
        known, profile, ("9000", "9500"), recipient=known.recipient_id
    )
    assert evaluate_sequence(known_context).outcomes[2].status == SequenceStatus.NOT_MATCHED


def test_strict_window_excludes_lower_boundary(transaction, profile):
    policy = replace(DEFAULT_SEQUENCE_POLICY, exposure_cumulative_ratio=Decimal("2"))
    inside = replace(
        transaction,
        transaction_id=uuid4(),
        amount=Decimal("35000"),
        timestamp=transaction.timestamp - timedelta(hours=24) + timedelta(microseconds=1),
    )
    boundary = replace(
        transaction,
        transaction_id=uuid4(),
        amount=Decimal("1000000"),
        timestamp=transaction.timestamp - timedelta(hours=24),
    )
    context = FeatureContext(
        uuid4(),
        transaction,
        verified(profile),
        "UTC",
        (boundary, inside),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )
    outcome = evaluate_sequence(context, policy).outcomes[3]
    assert outcome.observed_count == 2
    assert outcome.observed_amount == Decimal("65000")
    assert outcome.status == SequenceStatus.NOT_MATCHED


@pytest.mark.parametrize("profile_state", ["missing", "unverified", "insufficient"])
def test_missing_or_untrusted_baseline_never_becomes_clean_verdict(
    transaction, profile, profile_state
):
    selected = verified(profile)
    if profile_state == "missing":
        selected = None
    elif profile_state == "unverified":
        selected = profile
    else:
        selected = replace(verified(profile), observations=profile.observations[:4])
    prior = replace(
        transaction, transaction_id=uuid4(), timestamp=transaction.timestamp - timedelta(1)
    )
    context = FeatureContext(
        uuid4(),
        transaction,
        selected,
        "UTC",
        (prior,),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )
    result = evaluate_sequence(context)
    assert all(outcome.status == SequenceStatus.NOT_EVALUATED for outcome in result.outcomes)
    assert result.reasons == ()


def test_empty_raw_activity_is_explicitly_not_evaluated(transaction, profile):
    context = FeatureContext(
        uuid4(),
        transaction,
        verified(profile),
        "UTC",
        (),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )
    result = evaluate_sequence(context)
    assert all("activity_history_missing" in item.missing_indicators for item in result.outcomes)


def test_policy_validation_and_fingerprint():
    assert DEFAULT_SEQUENCE_POLICY.fingerprint == SequencePolicy().fingerprint
    assert (
        replace(DEFAULT_SEQUENCE_POLICY, window_hours=12).fingerprint
        != DEFAULT_SEQUENCE_POLICY.fingerprint
    )
    for changed in (
        {"window_hours": 0},
        {"low_value_count": 1},
        {"escalation_growth_ratio": Decimal("1")},
        {"exposure_cumulative_ratio": Decimal("NaN")},
    ):
        with pytest.raises(ValueError):
            replace(DEFAULT_SEQUENCE_POLICY, **changed)


def test_saved_context_cli_replays_without_database(
    transaction, profile, tmp_path: Path, monkeypatch, capsys
):
    context = context_with_amounts(transaction, profile, ("10000", "20000", "30000"))
    path = tmp_path / "context.json"
    write_context(path, context)
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", "invalid")
    assert main([str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["sequence_version"] == "sequence-v1-experimental"
    assert result["thresholds_calibrated"] is False
    assert main([str(tmp_path / "missing")]) == 1
