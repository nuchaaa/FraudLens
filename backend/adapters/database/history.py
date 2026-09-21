from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from backend.adapters.database.models import AuditRow, FeedbackRow, OutboxDeliveryRow, OutboxRow
from backend.adapters.database.repository_base import Repository
from backend.app.audit.entities import AuditEvent
from backend.app.feedback.entities import AnalystDecision, AnalystVerdict
from backend.app.shared.events import DomainEvent, EventType, OutboxEvent
from backend.app.shared.validation import utc


class PostgresAuditRepository(Repository):
    def add(self, event: AuditEvent) -> None:
        self.session.add(AuditRow(**asdict(event)))
        self.session.flush()

    def get(self, audit_id: UUID) -> AuditEvent | None:
        row = self.session.get(AuditRow, audit_id)
        return (
            AuditEvent(
                row.audit_id,
                row.actor_id,
                row.action,
                row.entity_id,
                row.correlation_id,
                row.timestamp,
                row.detail,
            )
            if row
            else None
        )


class PostgresFeedbackRepository(Repository):
    def add(self, decision: AnalystDecision) -> None:
        self.session.add(FeedbackRow(**asdict(decision)))
        self.session.flush()

    def get(self, decision_id: UUID) -> AnalystDecision | None:
        row = self.session.get(FeedbackRow, decision_id)
        return (
            AnalystDecision(
                row.decision_id,
                row.transaction_id,
                row.assessment_id,
                row.analyst_id,
                AnalystVerdict(row.verdict),
                row.model_prediction,
                row.model_version,
                row.timestamp,
                row.comment,
            )
            if row
            else None
        )


class PostgresOutboxRepository(Repository):
    def add(self, event: DomainEvent) -> None:
        self.session.add(OutboxRow(**asdict(event)))
        self.session.flush()

    def get(self, event_id: UUID) -> OutboxEvent | None:
        row = self.session.get(OutboxRow, event_id, populate_existing=True)
        if row is None:
            return None
        return OutboxEvent(
            DomainEvent(
                row.event_id,
                EventType(row.event_type),
                row.aggregate_id,
                row.occurred_at,
                row.correlation_id,
                tuple((k, v) for k, v in row.payload),
                row.schema_version,
            ),
            row.attempts,
            row.published_at,
        )

    def pending(self, *, limit: int = 100) -> tuple[OutboxEvent, ...]:
        """Read only: does not claim events or provide a dispatcher lease."""
        if not 1 <= limit <= 1000:
            raise ValueError("pending limit must be between 1 and 1000")
        ids = self.session.scalars(
            select(OutboxRow.event_id)
            .where(OutboxRow.published_at.is_(None))
            .order_by(OutboxRow.occurred_at, OutboxRow.event_id)
            .limit(limit)
        )
        return tuple(event for event_id in ids if (event := self.get(event_id)) is not None)

    def record_attempt(self, event_id: UUID) -> None:
        self._unleased(event_id)
        result = self.session.execute(
            update(OutboxRow)
            .where(OutboxRow.event_id == event_id, OutboxRow.published_at.is_(None))
            .values(attempts=OutboxRow.attempts + 1)
            .returning(OutboxRow.event_id)
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("event is missing or already published")

    def mark_published(self, event_id: UUID, at: datetime) -> None:
        delivery = self._unleased(event_id)
        result = self.session.execute(
            update(OutboxRow)
            .where(OutboxRow.event_id == event_id, OutboxRow.published_at.is_(None))
            .values(published_at=utc(at))
            .returning(OutboxRow.event_id)
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("event is missing or already published")
        delivery.completed_at = utc(at)
        self.session.flush()

    def _unleased(self, event_id: UUID) -> OutboxDeliveryRow:
        """Legacy repository helpers cannot bypass an active worker or dead letter."""
        row = self.session.scalar(
            select(OutboxDeliveryRow)
            .where(OutboxDeliveryRow.event_id == event_id)
            .with_for_update()
        )
        if row is None or row.token is not None or row.dead_at or row.completed_at:
            raise ValueError("event is missing, leased or terminal")
        return row
