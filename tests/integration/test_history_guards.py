from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.uow import PostgresUnitOfWork
from backend.app.cases.entities import CaseState, FraudCase
from backend.app.feedback.entities import AnalystDecision, AnalystVerdict
from backend.app.fraud.ports import ModelVersion
from backend.app.profile.entities import Customer, CustomerBehaviorProfile, ProfileSnapshot
from backend.app.risk.entities import RecommendedAction, RiskAssessment, RiskLevel
from backend.app.rules.contracts import RuleVersion
from backend.app.shared.errors import PersistenceConflict

pytestmark = pytest.mark.postgres


@pytest.fixture
def historical_records(db_engine, transaction):
    tx = replace(transaction, customer_id=uuid4())
    customer = Customer(tx.customer_id, tx.timestamp)
    profile = CustomerBehaviorProfile(customer.customer_id, tx.currency, tx.timestamp)
    model = ModelVersion("fixture-" + uuid4().hex, "test-features", tx.timestamp, "a" * 64)
    rule = RuleVersion("fixture-" + uuid4().hex, "Persistence test only")
    snapshot = ProfileSnapshot(uuid4(), uuid4(), profile)
    assessment = RiskAssessment(
        snapshot.assessment_id,
        tx.transaction_id,
        snapshot.snapshot_id,
        0.7,
        RiskLevel.HIGH,
        RecommendedAction.HOLD_AND_REVIEW,
        (),
        model.version,
        model.feature_version,
        rule.version,
        "test-policy",
        "hybrid",
        tx.timestamp,
    )
    case = FraudCase(uuid4(), tx.transaction_id, assessment.assessment_id, tx.timestamp)
    case = case.transition(CaseState.UNDER_REVIEW, uuid4(), tx.timestamp)
    feedback = AnalystDecision(
        uuid4(),
        tx.transaction_id,
        assessment.assessment_id,
        uuid4(),
        AnalystVerdict.NEEDS_INVESTIGATION,
        0.7,
        model.version,
        tx.timestamp,
        "Synthetic review",
    )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(customer)
        uow.transactions.add(tx)
        uow.models.add(model)
        uow.rules.add(rule)
        uow.snapshots.add(snapshot)
        uow.assessments.add(assessment)
        uow.cases.save(case)
        uow.feedback.add(feedback)
        uow.commit()
    return {
        "transactions": ("transaction_id", tx.transaction_id, "amount=1"),
        "profile_snapshots": ("snapshot_id", snapshot.snapshot_id, "profile='{}'::jsonb"),
        "risk_assessments": ("assessment_id", assessment.assessment_id, "score=0.1"),
        "fraud_cases": ("case_id", case.case_id, "created_at=created_at"),
        "case_transitions": ("case_id", case.case_id, "target='CLOSED'"),
        "analyst_decisions": ("decision_id", feedback.decision_id, "comment='rewritten'"),
        "model_versions": ("version", model.version, "artifact_sha256=repeat('b',64)"),
        "rule_versions": ("version", rule.version, "description='rewritten'"),
        "assessment": assessment,
    }


@pytest.mark.parametrize(
    "table",
    [
        "transactions",
        "profile_snapshots",
        "risk_assessments",
        "fraud_cases",
        "case_transitions",
        "analyst_decisions",
        "model_versions",
        "rule_versions",
    ],
)
def test_history_cannot_be_overwritten_with_direct_sql(db_engine, historical_records, table):
    key, record_id, mutation = historical_records[table]
    # All SQL identifiers and assignments come from the fixed test fixture above.
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {table} SET {mutation} WHERE {key}=:id"), {"id": record_id}
        )


def test_snapshot_is_bound_to_one_assessment(db_engine, historical_records):
    assessment = replace(historical_records["assessment"], assessment_id=uuid4())
    with pytest.raises(PersistenceConflict), PostgresUnitOfWork(db_engine) as uow:
        uow.assessments.add(assessment)
        uow.commit()


def test_assessment_cannot_use_wrong_model_feature_schema(db_engine, historical_records):
    assessment = replace(
        historical_records["assessment"],
        assessment_id=uuid4(),
        feature_version="incompatible-features",
    )
    with pytest.raises(PersistenceConflict), PostgresUnitOfWork(db_engine) as uow:
        uow.assessments.add(assessment)
        uow.commit()
