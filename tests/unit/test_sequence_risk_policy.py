from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.features.context import ContextSource, FeatureContext
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.risk.sequence_policy import SequenceRiskPolicy, decide_sequence_risk
from backend.app.risk.service import RiskPolicy, Strategy, evaluate_risk
from backend.app.sequence.engine import evaluate_sequence
from backend.app.transaction.entities import Transaction


def test_complete_low_value_sequence_raises_review_floor_without_rewriting_v1(
    transaction: Transaction, profile: CustomerBehaviorProfile, now: datetime
) -> None:
    recipient = uuid4()
    candidate = replace(
        transaction,
        recipient_id=recipient,
        amount=Decimal("25000"),
        timestamp=now + timedelta(hours=1),
    )
    prior = tuple(
        replace(candidate, transaction_id=uuid4(), timestamp=now + timedelta(minutes=10 * i))
        for i in range(5)
    )
    verified = replace(
        profile,
        admission_workflow_verified=True,
        admission_policy_version="test-oracle",
        learning_decision_id=uuid4(),
    )
    context = FeatureContext(
        uuid4(),
        candidate,
        verified,
        "Asia/Almaty",
        prior,
        candidate.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )
    base = evaluate_risk(
        context, RiskPolicy(Strategy.RULES_ONLY), clock=lambda: candidate.timestamp
    )
    sequence = evaluate_sequence(context)
    decision = decide_sequence_risk(base, sequence)
    assert base.level == "LOW"
    assert decision.level == "MEDIUM"
    assert decision.suggested_action == "STEP_UP_VERIFICATION"
    assert "CUMULATIVE_LOW_VALUE_SEQUENCE" in decision.matched_sequences
    assert decision.decision_source == "SEQUENCE_REVIEW_FLOOR"
    assert decision.calibrated is decision.production_eligible is False
    assert base.level == "LOW"  # Original versioned result remains unchanged.


def test_missing_sequence_evidence_abstains_and_mismatches_fail_closed(
    transaction: Transaction, now: datetime
) -> None:
    context = FeatureContext(
        uuid4(), transaction, None, "Asia/Almaty", (), now, ContextSource.DECLARED_OFFLINE
    )
    base = evaluate_risk(context, RiskPolicy(Strategy.RULES_ONLY), clock=lambda: now)
    sequence = evaluate_sequence(context)
    decision = decide_sequence_risk(base, sequence)
    assert decision.status == "INSUFFICIENT_EVIDENCE"
    assert decision.level is decision.suggested_action is None
    assert decision.decision_source == "ABSTAIN"
    assert len(decision.unavailable_sequences) == 4
    for incompatible in (
        replace(sequence, context_id=str(uuid4())),
        replace(sequence, policy_sha256="bad"),
        replace(sequence, outcomes=tuple(reversed(sequence.outcomes))),
    ):
        with pytest.raises(ValueError, match="incompatible"):
            decide_sequence_risk(base, incompatible)
    with pytest.raises(ValueError, match="unsupported"):
        SequenceRiskPolicy(version="risk-v1-experimental")
