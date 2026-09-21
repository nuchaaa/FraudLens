from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.delivery import PostgresDeliveryQueue, PostgresRecordingConsumer
from backend.adapters.database.uow import PostgresUnitOfWork
from backend.app.shared.delivery import DeliveryPolicy, dispatch
from backend.app.shared.events import DomainEvent, EventType

pytestmark = pytest.mark.postgres


@pytest.fixture
def queue_engine(db_engine):
    # Separate schema: other integration tests intentionally retain pending events.
    from alembic import command
    from alembic.config import Config

    from backend.adapters.database.base import create_database_engine

    schema = "delivery_" + uuid4().hex
    with db_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_database_engine(
        db_engine.url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(
            hide_password=False
        )
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv(
            "FRAUDLENS_DATABASE_URL", engine.url.render_as_string(hide_password=False)
        )
        command.upgrade(Config("alembic.ini"), "head")
    try:
        yield engine
    finally:
        engine.dispose()
        with db_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def add(engine, *, version=1):
    event = DomainEvent(
        uuid4(),
        EventType.TRANSACTION_RECEIVED,
        uuid4(),
        datetime.now(UTC) - timedelta(seconds=1),
        uuid4(),
        schema_version=version,
    )
    with PostgresUnitOfWork(engine) as uow:
        uow.outbox.add(event)
        uow.commit()
    return event


def expire(engine, event_id):
    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE outbox_delivery SET lease_until=clock_timestamp()-interval '1 second'
            WHERE event_id=:id"""),
            {"id": event_id},
        )


def due(engine, event_id):
    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE outbox_delivery SET available_at=clock_timestamp()-interval '1 second'
            WHERE event_id=:id"""),
            {"id": event_id},
        )


def test_concurrent_claims_are_disjoint_and_batch_bounded(queue_engine):
    engine = queue_engine
    events = [add(engine) for _ in range(8)]
    queue = PostgresDeliveryQueue(engine)
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: queue.claim(), range(8)))
    claims = [claim for claim in claims if claim is not None]
    assert len({claim.event.event_id for claim in claims}) == len(claims)
    assert len(claims) > 0
    for claim in claims:
        assert queue.acknowledge(claim)
    run = dispatch(queue, PostgresRecordingConsumer(engine), limit=2)
    assert run.claimed <= 2
    assert queue.status()["published"] == len(claims) + run.published
    assert len(events) == 8


def test_crash_after_handling_deduplicates_and_stale_token_cannot_ack(queue_engine):
    event = add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    consumer = PostgresRecordingConsumer(queue_engine)
    first = queue.claim()
    assert first is not None
    consumer.publish(first.event)  # committed local effect, crash before ack
    assert queue.claim() is None
    expire(queue_engine, event.event_id)
    assert not queue.acknowledge(first)
    second = queue.claim()
    assert second is not None and second.token != first.token and second.attempt == 2
    assert not queue.fail(first)
    consumer.publish(second.event)
    assert queue.acknowledge(second)
    assert not queue.acknowledge(second)
    with queue_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM consumer_receipts")) == 1
    assert queue.status()["published"] == 1


def test_crash_before_handling_final_lease_expiry_dead_letters(queue_engine):
    event = add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine, DeliveryPolicy(max_attempts=1))
    claim = queue.claim()
    assert claim is not None
    expire(queue_engine, event.event_id)
    assert queue.claim() is None
    assert queue.status()["dead"] == 1
    assert queue.status()["dead_letters"][0]["error"] == "attempts_exhausted"
    assert not queue.acknowledge(claim)


def test_retry_backoff_and_failure_exhaustion(queue_engine):
    event = add(queue_engine, version=2)
    queue = PostgresDeliveryQueue(queue_engine, DeliveryPolicy(max_attempts=2))
    consumer = PostgresRecordingConsumer(queue_engine)
    assert dispatch(queue, consumer).failed == 1
    assert queue.claim() is None
    with queue_engine.connect() as conn:
        assert conn.scalar(text("SELECT available_at > clock_timestamp() FROM outbox_delivery"))
        assert conn.scalar(text("SELECT count(*) FROM consumer_receipts")) == 0
    due(queue_engine, event.event_id)
    assert dispatch(queue, consumer).failed == 1
    assert queue.status()["dead"] == 1
    assert queue.status()["pending"] == 0


def test_uncommitted_and_rolled_back_events_are_not_delivered(queue_engine):
    queue = PostgresDeliveryQueue(queue_engine)
    event = DomainEvent(uuid4(), EventType.PROFILE_UPDATED, uuid4(), datetime.now(UTC), uuid4())
    with PostgresUnitOfWork(queue_engine) as uow:
        uow.outbox.add(event)
        assert queue.claim() is None
    assert queue.claim() is None
    with queue_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM outbox_delivery")) == 0


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE outbox_events SET attempts=attempts+1",
        "UPDATE outbox_events SET payload='[]',event_type='Other'",
        "UPDATE outbox_delivery SET token=gen_random_uuid(),lease_until=clock_timestamp()",
        "DELETE FROM outbox_delivery",
        "TRUNCATE outbox_delivery",
        "UPDATE consumer_receipts SET consumer_id='Other'",
        "DELETE FROM consumer_receipts",
        "TRUNCATE consumer_receipts",
    ],
)
def test_published_and_receipt_history_is_immutable(queue_engine, statement):
    add(queue_engine)
    assert (
        dispatch(
            PostgresDeliveryQueue(queue_engine), PostgresRecordingConsumer(queue_engine)
        ).published
        == 1
    )
    with pytest.raises(IntegrityError), queue_engine.begin() as conn:
        conn.execute(text(statement))


def test_skip_locked_and_crashed_claim_transaction_rolls_back(queue_engine):
    event = add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    with queue_engine.connect() as conn, conn.begin():
        conn.execute(text("SELECT * FROM outbox_delivery FOR UPDATE"))
        assert queue.claim() is None
    claim = queue.claim()
    assert claim is not None and claim.event == event


def test_ack_failure_rolls_back_publication_then_receipt_is_replayed(queue_engine):
    add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    claim = queue.claim()
    consumer = PostgresRecordingConsumer(queue_engine)
    assert claim is not None
    consumer.publish(claim.event)
    with queue_engine.begin() as conn:
        conn.execute(
            text("""CREATE TRIGGER test_failure BEFORE UPDATE ON outbox_delivery
            FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()""")
        )
    with pytest.raises(IntegrityError):
        queue.acknowledge(claim)
    with queue_engine.begin() as conn:
        assert conn.scalar(text("SELECT published_at FROM outbox_events")) is None
        conn.execute(text("DROP TRIGGER test_failure ON outbox_delivery"))
    consumer.publish(claim.event)
    assert queue.acknowledge(claim)


def test_exact_batch_limit_and_legacy_helpers_cannot_bypass_lease(queue_engine):
    for _ in range(3):
        add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    consumer = PostgresRecordingConsumer(queue_engine)
    run = dispatch(queue, consumer, limit=2)
    assert run.claimed == run.published == 2
    assert queue.status()["pending"] == 1
    claim = queue.claim()
    assert claim is not None
    for method in ("record_attempt", "mark_published"):
        with pytest.raises(ValueError), PostgresUnitOfWork(queue_engine) as uow:
            if method == "record_attempt":
                uow.outbox.record_attempt(claim.event.event_id)
            else:
                uow.outbox.mark_published(claim.event.event_id, datetime.now(UTC))
    consumer.publish(claim.event)
    assert queue.acknowledge(claim)


def test_claim_failure_rolls_back_attempt_and_lease(queue_engine):
    add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    with queue_engine.begin() as conn:
        conn.execute(
            text("""CREATE TRIGGER test_failure BEFORE UPDATE ON outbox_delivery
            FOR EACH ROW EXECUTE FUNCTION fraudlens_reject_history_change()""")
        )
    with pytest.raises(IntegrityError):
        queue.claim()
    with queue_engine.begin() as conn:
        assert conn.scalar(text("SELECT attempts FROM outbox_events")) == 0
        assert conn.scalar(text("SELECT token FROM outbox_delivery")) is None
        conn.execute(text("DROP TRIGGER test_failure ON outbox_delivery"))
    assert queue.claim().attempt == 1


def test_cli_records_only_committed_events(queue_engine):
    import json
    import os
    import subprocess
    import sys

    add(queue_engine)
    env = dict(
        os.environ, FRAUDLENS_DATABASE_URL=queue_engine.url.render_as_string(hide_password=False)
    )
    run = subprocess.run(
        [sys.executable, "-m", "backend.adapters.events", "run", "--limit", "1"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(run.stdout) == {"claimed": 1, "published": 1, "failed": 0, "stale": 0}
    status = subprocess.run(
        [sys.executable, "-m", "backend.adapters.events", "status"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(status.stdout)["published"] == 1


def test_migration_backfills_pending_and_published_without_receipt_invention(queue_engine):
    from alembic import command
    from alembic.config import Config

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv(
            "FRAUDLENS_DATABASE_URL", queue_engine.url.render_as_string(hide_password=False)
        )
        command.downgrade(Config("alembic.ini"), "0006_safe_profile_learning")
        with queue_engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO outbox_events
                (event_id,event_type,aggregate_id,occurred_at,correlation_id,payload,
                 schema_version,attempts,published_at)
                SELECT gen_random_uuid(),'TransactionReceived',gen_random_uuid(),
                clock_timestamp()-interval '1 second',gen_random_uuid(),'[]',1,0,
                CASE WHEN n=1 THEN clock_timestamp() ELSE NULL END FROM generate_series(1,2) n
            """)
            )
        command.upgrade(Config("alembic.ini"), "head")
    queue = PostgresDeliveryQueue(queue_engine)
    assert queue.status()["published"] == queue.status()["pending"] == 1
    with queue_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM consumer_receipts")) == 0
    assert dispatch(queue, PostgresRecordingConsumer(queue_engine)).published == 1


def test_unknown_envelope_does_not_block_valid_event(queue_engine):
    with queue_engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO outbox_events
            (event_id,event_type,aggregate_id,occurred_at,correlation_id,payload,schema_version)
            VALUES(gen_random_uuid(),'FutureEvent',gen_random_uuid(),
            clock_timestamp()-interval '1 second',gen_random_uuid(),'[]',1)""")
        )
    add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)
    assert dispatch(queue, PostgresRecordingConsumer(queue_engine)).published == 1
    assert queue.status()["dead_letters"][0]["error"] == "unsupported_envelope"


@pytest.mark.parametrize("fail", [False, True])
def test_worker_reports_stale_completion_after_handler_outlives_lease(queue_engine, fail):
    event = add(queue_engine)
    queue = PostgresDeliveryQueue(queue_engine)

    class SlowHandler:
        def publish(self, event):
            expire(queue_engine, event.event_id)
            if fail:
                raise RuntimeError("private exception contents must not be stored")

    run = dispatch(queue, SlowHandler(), limit=1)
    assert run.stale == 1 and run.published == run.failed == 0
    assert queue.status()["expired_leases"] == 1
    second = queue.claim()
    assert second.event.event_id == event.event_id and second.attempt == 2
