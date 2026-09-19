from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.profile.gate import GatePolicy, ProfileUpdateAction, ProfileUpdateGate
from backend.app.transaction.entities import Transaction


def test_robust_statistics(profile: CustomerBehaviorProfile) -> None:
    stats = profile.long_term
    assert stats is not None
    assert stats.count == 20
    assert stats.median == Decimal("30000")
    assert stats.mad == Decimal("5000")
    assert stats.p95 == Decimal("50000")
    assert stats.mean == Decimal("32000")
    assert profile.short_term == stats
    assert profile.typical_hours == frozenset({12})


def test_short_long_windows_differ(profile: CustomerBehaviorProfile) -> None:
    old = replace(
        profile.observations[0],
        transaction_id=uuid4(),
        amount=Decimal("1000"),
        timestamp=profile.as_of - timedelta(days=40),
    )
    changed = replace(profile, observations=(*profile.observations, old))
    assert changed.long_term is not None and changed.long_term.count == 21
    assert changed.short_term is not None and changed.short_term.count == 20


def test_no_future_or_duplicate_observations(profile: CustomerBehaviorProfile) -> None:
    with pytest.raises(ValueError, match="future"):
        replace(profile, as_of=profile.as_of - timedelta(days=100))
    with pytest.raises(ValueError, match="duplicate"):
        replace(profile, observations=(*profile.observations, profile.observations[0]))


def test_empty_profile_has_no_invented_baseline(profile: CustomerBehaviorProfile) -> None:
    cold = replace(profile, observations=())
    assert cold.long_term is None
    assert cold.short_term is None
    assert cold.known_recipients == frozenset()


def test_confirmed_normal_activity_is_admitted(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    decision, updated = ProfileUpdateGate().apply(transaction, profile, AnalystVerdict.LEGITIMATE)
    assert decision.action == ProfileUpdateAction.ACCEPT
    assert updated.version == profile.version + 1
    assert len(updated.observations) == len(profile.observations) + 1
    assert len(profile.observations) == 20


def test_fraud_does_not_update_profile(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    decision, updated = ProfileUpdateGate().apply(
        transaction, profile, AnalystVerdict.CONFIRMED_FRAUD
    )
    assert decision.action == ProfileUpdateAction.REJECT_FROM_PROFILE
    assert updated is profile


def test_car_then_suspicious_transfer_preserves_baseline(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    gate = ProfileUpdateGate()
    car = replace(transaction, amount=Decimal("8000000"))
    car_decision, after_car = gate.apply(car, profile, AnalystVerdict.LEGITIMATE)
    assert car_decision.action == ProfileUpdateAction.QUARANTINE
    assert after_car is profile
    suspicious = replace(transaction, transaction_id=uuid4(), amount=Decimal("500000"))
    result, after_fraud = gate.apply(suspicious, after_car, AnalystVerdict.CONFIRMED_FRAUD)
    assert result.action == ProfileUpdateAction.REJECT_FROM_PROFILE
    assert after_fraud.long_term is not None
    assert after_fraud.long_term.median == Decimal("30000")
    assert suspicious.amount / after_fraud.long_term.median > 16


def test_unverified_escalating_sequence_cannot_train_profile(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    current = profile
    for amount in (50000, 70000, 100000, 150000, 250000, 500000):
        tx = replace(transaction, transaction_id=uuid4(), amount=Decimal(amount))
        decision, current = ProfileUpdateGate().apply(tx, current, None)
        assert decision.action == ProfileUpdateAction.QUARANTINE
    assert current is profile


def test_gradual_confirmed_drift_adapts(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    current = profile
    for day in range(1, 61):
        tx = replace(
            transaction,
            transaction_id=uuid4(),
            amount=Decimal(30000 + day * 1500),
            timestamp=transaction.timestamp + timedelta(days=day),
        )
        decision, current = ProfileUpdateGate().apply(tx, current, AnalystVerdict.LEGITIMATE)
        assert decision.action == ProfileUpdateAction.ACCEPT
    assert current.short_term is not None and current.long_term is not None
    assert current.short_term.median > Decimal("90000")
    assert Decimal("30000") < current.long_term.median < current.short_term.median


@pytest.mark.parametrize("verdict", [None, AnalystVerdict.NEEDS_INVESTIGATION])
def test_only_confirmed_legitimate_can_be_admitted(
    profile: CustomerBehaviorProfile, transaction: Transaction, verdict
) -> None:
    assert (
        ProfileUpdateGate().evaluate(transaction, profile, verdict).action
        == ProfileUpdateAction.QUARANTINE
    )


def test_cold_start_fails_closed(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    decision = ProfileUpdateGate().evaluate(
        transaction, replace(profile, observations=()), AnalystVerdict.LEGITIMATE
    )
    assert decision.reason == "INSUFFICIENT_TRUSTED_HISTORY"


def test_stale_profile_history_expires(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    future = replace(transaction, timestamp=transaction.timestamp + timedelta(days=181))
    decision = ProfileUpdateGate().evaluate(future, profile, AnalystVerdict.LEGITIMATE)
    assert decision.reason == "INSUFFICIENT_TRUSTED_HISTORY"


def test_mismatched_currency_customer_and_past_rejected(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    for tx in (
        replace(transaction, currency="USD"),
        replace(transaction, customer_id=uuid4()),
        replace(transaction, timestamp=transaction.timestamp - timedelta(days=1)),
    ):
        with pytest.raises(ValueError):
            ProfileUpdateGate().evaluate(tx, profile, AnalystVerdict.LEGITIMATE)


def test_duplicate_admission_rejected(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    _, updated = ProfileUpdateGate().apply(transaction, profile, AnalystVerdict.LEGITIMATE)
    with pytest.raises(ValueError, match="already admitted"):
        ProfileUpdateGate().apply(transaction, updated, AnalystVerdict.LEGITIMATE)


def test_gate_exact_threshold_quarantines(
    profile: CustomerBehaviorProfile, transaction: Transaction
) -> None:
    decision = ProfileUpdateGate().evaluate(
        replace(transaction, amount=Decimal("300000")), profile, AnalystVerdict.LEGITIMATE
    )
    assert decision.action == ProfileUpdateAction.QUARANTINE


@pytest.mark.parametrize("ratio", ["NaN", "Infinity", "1", "-1"])
def test_invalid_gate_policy(ratio: str) -> None:
    with pytest.raises(ValueError):
        GatePolicy(exceptional_ratio=Decimal(ratio))


def test_zero_mad_is_valid(profile: CustomerBehaviorProfile) -> None:
    steady = replace(
        profile,
        observations=tuple(replace(o, amount=Decimal("30000")) for o in profile.observations),
    )
    assert steady.long_term is not None and steady.long_term.mad == 0


def test_rolling_window_lower_bound_excluded(profile: CustomerBehaviorProfile) -> None:
    boundary = ProfileObservation(
        uuid4(), Decimal("30000"), profile.as_of - timedelta(days=30), uuid4()
    )
    changed = replace(profile, observations=(boundary,))
    assert changed.short_term is None
    assert changed.long_term is not None
