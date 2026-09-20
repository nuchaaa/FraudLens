import json
import math
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal, localcontext
from uuid import uuid4

import pytest

from backend.adapters.features.artifacts import (
    decode_context,
    encode_context,
    read_context,
    write_context,
)
from backend.app.features.context import (
    MAX_ACTIVITY_ROWS,
    ActivityHistoryLimit,
    ContextSource,
    FeatureContext,
    FeatureInputError,
)
from backend.app.features.engine import FEATURE_NAMES, extract_features, extract_many


@pytest.fixture
def feature_context(transaction, profile):
    activity = tuple(
        replace(
            transaction,
            transaction_id=uuid4(),
            timestamp=transaction.timestamp - timedelta(minutes=minutes),
            device_id="previous-device",
            recipient_id=uuid4() if minutes == 9 else transaction.recipient_id,
        )
        for minutes in (4, 5, 9, 10, 59, 60, 14_400)
    )
    return FeatureContext(
        uuid4(),
        transaction,
        profile,
        "Asia/Almaty",
        activity,
        transaction.timestamp + timedelta(hours=1),
        ContextSource.DECLARED_OFFLINE,
    )


def values(context):
    vector = extract_features(context)
    assert vector.version == "behavior-v1" and vector.names == FEATURE_NAMES
    assert len(vector.values) == 29 and all(math.isfinite(value) for value in vector.values)
    return dict(zip(vector.names, vector.values, strict=True))


def test_known_feature_values_and_exact_time_boundaries(feature_context):
    assert values(feature_context) == {
        "amount": 30000.0,
        "profile_missing": 0.0,
        "baseline_insufficient": 0.0,
        "long_history_count": 20.0,
        "short_history_count": 20.0,
        "amount_vs_customer_median": 1.0,
        "amount_vs_customer_mean": 0.9375,
        "robust_amount_deviation": 0.0,
        "mad_zero": 0.0,
        "mad_floor_applied": 0.0,
        "amount_vs_p95": 0.6,
        "short_term_vs_long_term_amount_ratio": 1.0,
        "short_baseline_insufficient": 0.0,
        "new_recipient": 0.0,
        "unusual_hour": 0.0,
        "hour_deviation": 0.0,
        "typical_hours_missing": 0.0,
        "transactions_last_5_min": 1.0,
        "transactions_last_10_min": 3.0,
        "transactions_last_hour": 5.0,
        "recipient_transactions_last_hour": 4.0,
        "activity_history_count": 7.0,
        "activity_history_missing": 0.0,
        "recipient_observed_age_days": 10.0,
        "recipient_activity_missing": 0.0,
        "device_changed": 1.0,
        "device_change_missing": 0.0,
        "device_not_seen_before": 1.0,
        "days_since_last_transfer": 4 / 1440,
    }


@pytest.mark.parametrize("count", [None, 0, 1, 4])
def test_missing_empty_and_insufficient_baselines_are_masked(feature_context, count):
    profile = (
        None
        if count is None
        else replace(
            feature_context.profile, observations=feature_context.profile.observations[:count]
        )
    )
    result = values(replace(feature_context, profile=profile, activity=()))
    assert result["profile_missing"] == (count is None)
    assert result["baseline_insufficient"] == result["short_baseline_insufficient"] == 1
    assert result["typical_hours_missing"] == result["activity_history_missing"] == 1
    assert result["device_change_missing"] == result["recipient_activity_missing"] == 1
    for name in (
        "amount_vs_customer_median",
        "amount_vs_customer_mean",
        "robust_amount_deviation",
        "amount_vs_p95",
        "new_recipient",
        "unusual_hour",
        "hour_deviation",
        "short_term_vs_long_term_amount_ratio",
        "device_changed",
        "days_since_last_transfer",
    ):
        assert result[name] == 0


def test_zero_mad_has_finite_explicit_floor_and_flag(feature_context):
    profile = replace(
        feature_context.profile,
        observations=tuple(
            replace(o, amount=Decimal("30000")) for o in feature_context.profile.observations
        ),
    )
    candidate = replace(feature_context.candidate, amount=Decimal("500000"))
    result = values(replace(feature_context, profile=profile, candidate=candidate))
    assert result["mad_zero"] == result["mad_floor_applied"] == 1
    assert result["robust_amount_deviation"] == 47_000_000
    assert result["amount_vs_customer_median"] == pytest.approx(500000 / 30000)


def test_maximum_money_and_small_baseline_remain_finite(feature_context):
    profile = replace(
        feature_context.profile,
        observations=tuple(
            replace(o, amount=Decimal("0.01")) for o in feature_context.profile.observations
        ),
    )
    result = values(
        replace(
            feature_context,
            profile=profile,
            candidate=replace(feature_context.candidate, amount=Decimal("9999999999999999.99")),
        )
    )
    assert result["robust_amount_deviation"] > 1e17


def test_short_window_missing_and_circular_hour_distance(feature_context):
    profile = replace(
        feature_context.profile,
        observations=tuple(
            replace(o, timestamp=o.timestamp - timedelta(days=40))
            for o in feature_context.profile.observations
        ),
    )
    candidate = replace(
        feature_context.candidate,
        timestamp=feature_context.candidate.timestamp + timedelta(hours=11),
    )
    result = values(
        replace(
            feature_context,
            profile=profile,
            candidate=candidate,
            captured_at=candidate.timestamp + timedelta(hours=1),
        )
    )
    assert result["short_baseline_insufficient"] == 1
    assert result["short_term_vs_long_term_amount_ratio"] == 0
    assert result["hour_deviation"] == 11 and result["unusual_hour"] == 1


def test_unqualified_hours_and_recipient_missing_are_explicit(feature_context):
    profile = replace(
        feature_context.profile,
        observations=tuple(
            replace(o, timestamp=o.timestamp - timedelta(hours=i))
            for i, o in enumerate(feature_context.profile.observations)
        ),
    )
    result = values(
        replace(
            feature_context,
            profile=profile,
            candidate=replace(feature_context.candidate, recipient_id=uuid4()),
        )
    )
    assert result["baseline_insufficient"] == 0 and result["new_recipient"] == 1
    assert result["typical_hours_missing"] == 1 and result["unusual_hour"] == 0
    assert result["recipient_activity_missing"] == 1 and result["recipient_observed_age_days"] == 0


def test_tied_last_devices_do_not_invent_chronological_order(feature_context):
    latest = feature_context.activity[-1]
    same_time = replace(
        latest, transaction_id=uuid4(), device_id=feature_context.candidate.device_id
    )
    result = values(replace(feature_context, activity=(*feature_context.activity, same_time)))
    assert result["device_change_missing"] == 1 and result["device_changed"] == 0
    assert result["device_not_seen_before"] == 0


def test_context_and_features_are_order_and_decimal_context_independent(feature_context):
    reversed_context = replace(
        feature_context,
        activity=tuple(reversed(feature_context.activity)),
        profile=replace(
            feature_context.profile,
            observations=tuple(reversed(feature_context.profile.observations)),
        ),
    )
    expected = extract_features(feature_context)
    assert encode_context(reversed_context) == encode_context(feature_context)
    with localcontext() as decimal_context:
        decimal_context.prec = 6
        assert extract_features(reversed_context) == expected
    with pytest.raises(FrozenInstanceError):
        feature_context.activity = ()


def test_offline_artifact_batch_matches_online_extraction_and_row_order(feature_context, tmp_path):
    changed = replace(
        feature_context,
        context_id=uuid4(),
        candidate=replace(
            feature_context.candidate, transaction_id=uuid4(), amount=Decimal("8000000")
        ),
    )
    paths = [tmp_path / "first.json", tmp_path / "second.json"]
    for path, context in zip(paths, (feature_context, changed), strict=True):
        write_context(path, context)
        assert read_context(path) == context
    assert extract_many(read_context(path) for path in paths) == (
        extract_features(feature_context),
        extract_features(changed),
    )
    with pytest.raises(FileExistsError):
        write_context(paths[0], changed)
    payload = json.loads(json.loads(paths[0].read_text())["payload"])
    assert isinstance(payload["candidate"]["amount"], str)
    assert payload["source"] == "declared_offline"


@pytest.mark.parametrize(
    "mutation", ["candidate", "future", "boundary", "currency", "customer", "duplicate"]
)
def test_dirty_activity_cannot_silently_become_features(feature_context, mutation):
    tx = feature_context.activity[0]
    if mutation == "candidate":
        tx = feature_context.candidate
    elif mutation == "future":
        tx = replace(tx, timestamp=feature_context.candidate.timestamp + timedelta(seconds=1))
    elif mutation == "boundary":
        tx = replace(tx, timestamp=feature_context.candidate.timestamp - timedelta(days=180))
    elif mutation == "currency":
        tx = replace(tx, currency="USD")
    elif mutation == "customer":
        tx = replace(tx, customer_id=uuid4())
    with pytest.raises(FeatureInputError):
        replace(feature_context, activity=(tx, tx) if mutation == "duplicate" else (tx,))


@pytest.mark.parametrize("mutation", ["future", "currency", "customer", "candidate"])
def test_profile_mismatch_or_self_admission_is_rejected(feature_context, mutation):
    profile = feature_context.profile
    if mutation == "future":
        profile = replace(profile, as_of=profile.as_of + timedelta(seconds=1))
    elif mutation == "currency":
        profile = replace(profile, currency="USD")
    elif mutation == "customer":
        profile = replace(profile, customer_id=uuid4())
    else:
        profile = replace(
            profile,
            observations=(
                replace(
                    profile.observations[0], transaction_id=feature_context.candidate.transaction_id
                ),
            ),
        )
    with pytest.raises(FeatureInputError):
        replace(feature_context, profile=profile)


def test_profile_simultaneous_observations_are_excluded(feature_context):
    simultaneous = replace(
        feature_context.profile.observations[0],
        transaction_id=uuid4(),
        timestamp=feature_context.candidate.timestamp,
        amount=Decimal("8000000"),
    )
    changed = replace(
        feature_context,
        profile=replace(
            feature_context.profile,
            observations=(*feature_context.profile.observations, simultaneous),
        ),
    )
    assert extract_features(changed) == extract_features(feature_context)


def test_context_bounds_and_versions(feature_context):
    with pytest.raises(FeatureInputError, match="version"):
        replace(feature_context, feature_version="unsupported")
    with pytest.raises(FeatureInputError, match="capture"):
        replace(
            feature_context, captured_at=feature_context.candidate.timestamp - timedelta(seconds=1)
        )
    with pytest.raises(ActivityHistoryLimit):
        replace(feature_context, activity=(feature_context.activity[0],) * (MAX_ACTIVITY_ROWS + 1))


def test_artifacts_reject_corruption_unknown_versions_and_fields(feature_context):
    import hashlib

    envelope = json.loads(encode_context(feature_context))
    for changes in (
        {"sha256": "0" * 64},
        {"schema_version": 99},
        {"feature_version": "future"},
        {"extra": True},
    ):
        with pytest.raises(FeatureInputError):
            decode_context(json.dumps({**envelope, **changes}))
    payload = json.loads(envelope["payload"])
    payload["candidate"]["unexpected_label"] = "FRAUD"
    document = json.dumps(payload)
    with pytest.raises(FeatureInputError, match="invalid"):
        decode_context(
            json.dumps(
                {
                    **envelope,
                    "payload": document,
                    "sha256": hashlib.sha256(document.encode()).hexdigest(),
                }
            )
        )


def test_artifact_resource_limits_and_invalid_utf8(feature_context, tmp_path, monkeypatch):
    from backend.adapters.features import artifacts

    monkeypatch.setattr(artifacts, "MAX_ARTIFACT_BYTES", 100)
    with pytest.raises(FeatureInputError, match="exceeds"):
        encode_context(feature_context)
    with pytest.raises(FeatureInputError, match="exceeds"):
        decode_context("x" * 101)
    path = tmp_path / "oversized.json"
    path.write_bytes(b"x" * 101)
    with pytest.raises(FeatureInputError, match="exceeds"):
        read_context(path)
    path.write_bytes(b"\xff")
    with pytest.raises(FeatureInputError, match="UTF-8"):
        read_context(path)
