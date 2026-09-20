from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.uow import PostgresUnitOfWork
from backend.app.audit.entities import AuditEvent
from backend.app.cases.entities import CaseState, FraudCase
from backend.app.feedback.entities import AnalystDecision, AnalystVerdict
from backend.app.fraud.ports import ModelVersion
from backend.app.profile.entities import Customer, CustomerBehaviorProfile, ProfileSnapshot
from backend.app.profile.gate import ProfileUpdateGate
from backend.app.risk.entities import RecommendedAction, RiskAssessment, RiskLevel, RiskReason
from backend.app.rules.contracts import RuleVersion
from backend.app.shared.errors import (
    ConcurrentUpdate,
    HistoryConflict,
    IdempotencyConflict,
    PersistenceConflict,
)
from backend.app.shared.events import DomainEvent, EventType
from backend.app.transaction.entities import Transaction
from backend.app.transaction.idempotency import IdempotencyRecord

pytestmark = pytest.mark.postgres


@pytest.fixture
def stored(db_engine: Engine, profile: CustomerBehaviorProfile, transaction: Transaction):
    # Each test owns distinct IDs even when run repeatedly against the same disposable database.
    customer_id = uuid4()
    profile = replace(profile, customer_id=customer_id)
    transaction = replace(transaction, customer_id=customer_id)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(customer_id, profile.as_of - timedelta(days=200)))
        for o in profile.observations:
            uow.transactions.add(
                replace(
                    transaction,
                    transaction_id=o.transaction_id,
                    amount=o.amount,
                    timestamp=o.timestamp,
                    recipient_id=o.recipient_id,
                )
            )
        uow.profiles.save(profile, expected_version=0)
        uow.transactions.add(transaction)
        uow.commit()
    return profile, transaction


def add_assessment(uow, profile, transaction):
    model = ModelVersion("test-" + uuid4().hex, "features-v1", profile.as_of, "a" * 64)
    rule = RuleVersion("rule-" + uuid4().hex, "Synthetic persistence fixture, not a trained model")
    assessment_id, snapshot_id = uuid4(), uuid4()
    snapshot = ProfileSnapshot(snapshot_id, assessment_id, profile)
    assessment = RiskAssessment(
        assessment_id,
        transaction.transaction_id,
        snapshot_id,
        0.8,
        RiskLevel.HIGH,
        RecommendedAction.HOLD_AND_REVIEW,
        (RiskReason("AMOUNT_ANOMALY", "Synthetic test explanation"),),
        model.version,
        model.feature_version,
        rule.version,
        "policy-v1",
        "hybrid",
        profile.as_of,
    )
    uow.models.add(model)
    uow.rules.add(rule)
    uow.snapshots.add(snapshot)
    uow.assessments.add(assessment)
    return model, rule, snapshot, assessment


def test_complete_roundtrip(db_engine: Engine, stored) -> None:
    profile, tx = stored
    with PostgresUnitOfWork(db_engine) as uow:
        model, rule, snapshot, assessment = add_assessment(uow, profile, tx)
        case = FraudCase(uuid4(), tx.transaction_id, assessment.assessment_id, tx.timestamp)
        case = case.transition(CaseState.UNDER_REVIEW, uuid4(), tx.timestamp)
        uow.cases.save(case)
        feedback = AnalystDecision(
            uuid4(),
            tx.transaction_id,
            assessment.assessment_id,
            uuid4(),
            AnalystVerdict.LEGITIMATE,
            0.72,
            model.version,
            tx.timestamp,
            "Verified synthetic purchase",
        )
        audit = AuditEvent(
            uuid4(),
            feedback.analyst_id,
            "ANALYST_DECISION",
            tx.transaction_id,
            uuid4(),
            tx.timestamp,
            "Confirmed legitimate",
        )
        event = DomainEvent(
            uuid4(),
            EventType.ANALYST_DECISION_MADE,
            tx.transaction_id,
            tx.timestamp,
            audit.correlation_id,
            (("decision", "LEGITIMATE"),),
        )
        uow.feedback.add(feedback)
        uow.audit.add(audit)
        uow.outbox.add(event)
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.transactions.get(tx.transaction_id) == tx
        assert uow.profiles.get(profile.customer_id, "KZT") == profile
        assert uow.customers.get(profile.customer_id).customer_id == profile.customer_id
        assert uow.models.get(model.version) == model
        assert uow.rules.get(rule.version) == rule
        assert uow.snapshots.get(snapshot.snapshot_id) == snapshot
        assert uow.assessments.get(assessment.assessment_id) == assessment
        assert uow.cases.get(case.case_id) == case
        assert uow.feedback.get(feedback.decision_id) == feedback
        assert uow.audit.get(audit.audit_id) == audit
        assert uow.outbox.get(event.event_id).event == event


@pytest.mark.parametrize("fail", [False, True])
def test_no_commit_or_exception_rolls_back_all(
    db_engine: Engine, transaction: Transaction, fail: bool
):
    tx = replace(transaction, customer_id=uuid4())
    event = DomainEvent(
        uuid4(), EventType.TRANSACTION_RECEIVED, tx.transaction_id, tx.timestamp, uuid4()
    )
    try:
        with PostgresUnitOfWork(db_engine) as uow:
            uow.customers.add(Customer(tx.customer_id, tx.timestamp))
            uow.transactions.add(tx)
            uow.outbox.add(event)
            if fail:
                raise RuntimeError("simulated interruption")
    except RuntimeError as error:
        assert str(error) == "simulated interruption"
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.customers.get(tx.customer_id) is None
        assert uow.transactions.get(tx.transaction_id) is None
        assert uow.outbox.get(event.event_id) is None


def test_commit_failure_rolls_back_other_writes(db_engine: Engine, stored):
    profile, tx = stored
    event = DomainEvent(uuid4(), EventType.RISK_EVALUATED, tx.transaction_id, tx.timestamp, uuid4())
    snapshot = ProfileSnapshot(uuid4(), uuid4(), profile)
    with pytest.raises(PersistenceConflict), PostgresUnitOfWork(db_engine) as uow:
        uow.outbox.add(event)
        uow.snapshots.add(snapshot)  # Deferred FK requires the corresponding assessment at commit.
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.outbox.get(event.event_id) is None
        assert uow.snapshots.get(snapshot.snapshot_id) is None


def test_profile_admission_roundtrip_and_stale_writer(db_engine: Engine, stored):
    profile, tx = stored
    _, updated = ProfileUpdateGate().apply(tx, profile, AnalystVerdict.LEGITIMATE)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.profiles.save(updated, expected_version=1)
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(profile.customer_id, "KZT") == updated
    with pytest.raises(ConcurrentUpdate), PostgresUnitOfWork(db_engine) as uow:
        uow.profiles.save(updated, expected_version=1)


def test_competing_profile_writers_serialize(db_engine: Engine, stored):
    profile, tx = stored
    _, updated = ProfileUpdateGate().apply(tx, profile, AnalystVerdict.LEGITIMATE)
    locked, competing = Event(), Event()

    def first():
        with PostgresUnitOfWork(db_engine) as uow:
            uow.profiles.save(updated, expected_version=1)
            locked.set()
            assert competing.wait(5)
            uow.commit()

    def second():
        assert locked.wait(5)
        with pytest.raises(ConcurrentUpdate), PostgresUnitOfWork(db_engine) as uow:
            competing.set()
            uow.profiles.save(updated, expected_version=1)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(first), pool.submit(second)]
        for future in futures:
            future.result(timeout=10)


def test_profile_cannot_rewrite_or_remove_admitted_observations(db_engine: Engine, stored):
    profile, _ = stored
    changed = replace(profile.observations[0], amount=Decimal("1"))
    for observations in (profile.observations[1:], (changed, *profile.observations[1:])):
        with pytest.raises(HistoryConflict), PostgresUnitOfWork(db_engine) as uow:
            uow.profiles.save(
                replace(profile, version=2, observations=observations), expected_version=1
            )


def test_expired_observations_remain_in_history(db_engine: Engine, stored):
    profile, _ = stored
    advanced = replace(
        profile, as_of=profile.as_of + timedelta(days=200), observations=(), version=2
    )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.profiles.save(advanced, expected_version=1)
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(profile.customer_id, "KZT") == advanced
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM profile_observations WHERE customer_id=:id"),
                {"id": profile.customer_id},
            ).scalar_one()
            == 20
        )


def test_transaction_duplicate_and_currency_constraint(db_engine: Engine, stored):
    _, tx = stored
    with pytest.raises(PersistenceConflict), PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(tx)
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO transactions SELECT :id, customer_id, recipient_id,
            amount, 'usd', timestamp, channel, device_id, status
            FROM transactions WHERE transaction_id=:old"""),
            {"id": uuid4(), "old": tx.transaction_id},
        )


def test_scoped_idempotency(db_engine: Engine, stored):
    _, tx = stored
    principal = uuid4()
    record = IdempotencyRecord(
        principal, "request-1", "a" * 64, tx.transaction_id, '{"accepted":true}', 201, tx.timestamp
    )
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.idempotency.acquire(principal, record.key, record.request_sha256) is None
        uow.idempotency.add(record)
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.idempotency.acquire(principal, record.key, record.request_sha256) == record
        assert uow.idempotency.acquire(uuid4(), record.key, "b" * 64) is None
    with pytest.raises(IdempotencyConflict), PostgresUnitOfWork(db_engine) as uow:
        uow.idempotency.acquire(principal, record.key, "b" * 64)


def test_idempotency_rolls_back_with_transaction(db_engine: Engine, transaction: Transaction):
    tx = replace(transaction, customer_id=uuid4())
    record = IdempotencyRecord(
        uuid4(), "request", "a" * 64, tx.transaction_id, "{}", 201, tx.timestamp
    )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(tx.customer_id, tx.timestamp))
        uow.transactions.add(tx)
        uow.idempotency.add(record)
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.idempotency.get(record.principal_id, record.key) is None


def test_same_key_concurrent_requests_share_one_outcome(db_engine: Engine, stored):
    _, tx = stored
    record = IdempotencyRecord(
        uuid4(), "shared", "a" * 64, tx.transaction_id, "{}", 201, tx.timestamp
    )
    claimed, waiting = Event(), Event()

    def first():
        with PostgresUnitOfWork(db_engine) as uow:
            assert (
                uow.idempotency.acquire(record.principal_id, record.key, record.request_sha256)
                is None
            )
            claimed.set()
            assert waiting.wait(5)
            uow.idempotency.add(record)
            uow.commit()

    def second():
        assert claimed.wait(5)
        with PostgresUnitOfWork(db_engine) as uow:
            waiting.set()
            assert (
                uow.idempotency.acquire(record.principal_id, record.key, record.request_sha256)
                == record
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in [pool.submit(first), pool.submit(second)]:
            future.result(timeout=10)


def test_case_history_append_and_conflict(db_engine: Engine, stored):
    profile, tx = stored
    with PostgresUnitOfWork(db_engine) as uow:
        *_, assessment = add_assessment(uow, profile, tx)
        case = FraudCase(uuid4(), tx.transaction_id, assessment.assessment_id, tx.timestamp)
        uow.cases.save(case)
        uow.commit()
    reviewed = case.transition(CaseState.UNDER_REVIEW, uuid4(), tx.timestamp)
    with PostgresUnitOfWork(db_engine) as uow:
        uow.cases.save(reviewed)
        uow.commit()
    with pytest.raises(ConcurrentUpdate), PostgresUnitOfWork(db_engine) as uow:
        uow.cases.save(case)
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO case_transitions
            VALUES (:id, 2, 'UNDER_REVIEW', 'CLOSED', :actor, :at)"""),
            {"id": case.case_id, "actor": uuid4(), "at": tx.timestamp},
        )


@pytest.mark.parametrize(
    "operation",
    [
        "UPDATE audit_events SET detail='rewritten' WHERE audit_id=:id",
        "DELETE FROM audit_events WHERE audit_id=:id",
        "TRUNCATE audit_events",
    ],
)
def test_database_rejects_audit_mutation(db_engine: Engine, now: datetime, operation: str):
    event = AuditEvent(uuid4(), uuid4(), "TEST", uuid4(), uuid4(), now, "Original history")
    with PostgresUnitOfWork(db_engine) as uow:
        uow.audit.add(event)
        uow.commit()
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(text(operation), {"id": event.audit_id})
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.audit.get(event.audit_id) == event


def test_outbox_envelope_immutable_delivery_metadata_updates(db_engine: Engine, now: datetime):
    event = DomainEvent(uuid4(), EventType.RISK_EVALUATED, uuid4(), now, uuid4())
    with PostgresUnitOfWork(db_engine) as uow:
        uow.outbox.add(event)
        uow.commit()
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("UPDATE outbox_events SET payload='[]', event_type='Other' WHERE event_id=:id"),
            {"id": event.event_id},
        )
    with PostgresUnitOfWork(db_engine) as uow:
        uow.outbox.record_attempt(event.event_id)
        uow.outbox.mark_published(event.event_id, now + timedelta(seconds=1))
        uow.commit()
    with PostgresUnitOfWork(db_engine) as uow:
        saved = uow.outbox.get(event.event_id)
        assert saved.event == event and saved.attempts == 1 and saved.published_at is not None
        assert all(item.event.event_id != event.event_id for item in uow.outbox.pending())


def test_unit_of_work_cannot_be_reused(db_engine: Engine):
    uow = PostgresUnitOfWork(db_engine)
    with uow:
        pass
    with pytest.raises(RuntimeError, match="reused"), uow:
        pass
