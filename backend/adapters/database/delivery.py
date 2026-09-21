"""Short queue transactions, database-clock leases and fenced completion."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.adapters.database.history import PostgresOutboxRepository
from backend.adapters.database.models import ConsumerReceiptRow, OutboxDeliveryRow, OutboxRow
from backend.app.shared.delivery import DeliveryClaim, DeliveryPolicy
from backend.app.shared.events import DomainEvent


class PostgresDeliveryQueue:
    def __init__(self, engine: Engine, policy: DeliveryPolicy | None = None) -> None:
        self.engine = engine
        self.policy = policy or DeliveryPolicy()

    def claim(self) -> DeliveryClaim | None:
        with Session(self.engine) as session, session.begin():
            # A bounded sweep also retires crashed final attempts. No handler runs here.
            rows = session.scalars(
                select(OutboxDeliveryRow)
                .join(OutboxRow)
                .where(
                    OutboxDeliveryRow.completed_at.is_(None),
                    OutboxDeliveryRow.dead_at.is_(None),
                    OutboxRow.published_at.is_(None),
                    OutboxDeliveryRow.available_at <= func.clock_timestamp(),
                    (OutboxDeliveryRow.lease_until.is_(None))
                    | (OutboxDeliveryRow.lease_until <= func.clock_timestamp()),
                )
                .order_by(OutboxDeliveryRow.available_at, OutboxDeliveryRow.event_id)
                .limit(100)
                .with_for_update(skip_locked=True, of=OutboxDeliveryRow)
            ).all()
            for row in rows:
                now = session.scalar(select(func.clock_timestamp()))
                assert now is not None
                source = session.get(OutboxRow, row.event_id)
                assert source is not None
                if source.attempts >= self.policy.max_attempts:
                    row.dead_at = now
                    row.last_error = "attempts_exhausted"
                    row.token = row.lease_until = None
                    continue
                try:
                    event = PostgresOutboxRepository(session).get(row.event_id)
                except (ValueError, TypeError):
                    # An unreadable/future envelope must not poison the whole queue.
                    row.dead_at = now
                    row.last_error = "unsupported_envelope"
                    row.token = row.lease_until = None
                    continue
                assert event is not None
                row.token = uuid4()
                row.lease_until = now + timedelta(seconds=self.policy.lease_seconds)
                session.execute(
                    update(OutboxRow)
                    .where(OutboxRow.event_id == row.event_id)
                    .values(attempts=OutboxRow.attempts + 1)
                )
                return DeliveryClaim(event.event, row.token, event.attempts + 1, row.lease_until)
        return None

    def _finish(self, claim: DeliveryClaim, *, success: bool) -> bool:
        with Session(self.engine) as session, session.begin():
            row = session.scalar(
                select(OutboxDeliveryRow)
                .where(OutboxDeliveryRow.event_id == claim.event.event_id)
                .with_for_update()
            )
            now = session.scalar(select(func.clock_timestamp()))
            assert now is not None
            if (
                row is None
                or row.token != claim.token
                or row.lease_until is None
                or row.lease_until <= now
                or row.completed_at is not None
                or row.dead_at is not None
            ):
                return False
            event = PostgresOutboxRepository(session).get(row.event_id)
            assert event is not None
            if event.published_at is not None:
                return False
            if success:
                session.execute(
                    update(OutboxRow)
                    .where(OutboxRow.event_id == row.event_id)
                    .values(published_at=now)
                )
                row.completed_at = now
            else:
                row.last_error = "handler_failed"
                if event.attempts >= self.policy.max_attempts:
                    row.dead_at = now
                else:
                    row.available_at = now + timedelta(seconds=self.policy.delay(event.attempts))
            row.token = row.lease_until = None
            return True

    def acknowledge(self, claim: DeliveryClaim) -> bool:
        return self._finish(claim, success=True)

    def fail(self, claim: DeliveryClaim) -> bool:
        return self._finish(claim, success=False)

    def status(self) -> dict[str, object]:
        with Session(self.engine) as session:
            counts = session.execute(
                select(
                    func.count().filter(OutboxRow.published_at.is_not(None)),
                    func.count().filter(OutboxDeliveryRow.dead_at.is_not(None)),
                    func.count().filter(
                        OutboxRow.published_at.is_(None), OutboxDeliveryRow.dead_at.is_(None)
                    ),
                    func.count().filter(OutboxDeliveryRow.lease_until > func.clock_timestamp()),
                    func.count().filter(OutboxDeliveryRow.lease_until <= func.clock_timestamp()),
                )
                .select_from(OutboxDeliveryRow)
                .join(OutboxRow)
            ).one()
            dead = session.execute(
                select(OutboxDeliveryRow.event_id, OutboxDeliveryRow.last_error, OutboxRow.attempts)
                .join(OutboxRow)
                .where(OutboxDeliveryRow.dead_at.is_not(None))
                .order_by(OutboxDeliveryRow.dead_at, OutboxDeliveryRow.event_id)
                .limit(100)
            ).all()
            return {
                "destination": "local-recording-v1",
                "published": counts[0],
                "dead": counts[1],
                "pending": counts[2],
                "leased": counts[3],
                "expired_leases": counts[4],
                "dead_letters": [
                    {"event_id": str(key), "error": error, "attempts": attempts}
                    for key, error, attempts in dead
                ],
            }


class PostgresRecordingConsumer:
    """The receipt IS the local effect; no external notification or fraud action."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def publish(self, event: DomainEvent) -> None:
        if event.schema_version != 1:
            raise ValueError("unsupported event schema")
        with Session(self.engine) as session, session.begin():
            stored = PostgresOutboxRepository(session).get(event.event_id)
            if stored is None or stored.event != event:
                raise ValueError("consumer requires the committed immutable event")
            session.execute(
                insert(ConsumerReceiptRow)
                .values(
                    consumer_id="local-recording-v1",
                    event_id=event.event_id,
                    recorded_at=func.clock_timestamp(),
                )
                .on_conflict_do_nothing()
            )
