from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from backend.app.shared.validation import nonempty, utc


class EventType(StrEnum):
    TRANSACTION_RECEIVED = "TransactionReceived"
    RISK_EVALUATED = "RiskEvaluated"
    TRANSACTION_FLAGGED = "TransactionFlagged"
    CASE_REVIEW_CHANGED = "CaseReviewChanged"
    FRAUD_CASE_CREATED = "FraudCaseCreated"
    ANALYST_DECISION_MADE = "AnalystDecisionMade"
    TRANSACTION_CONFIRMED_LEGITIMATE = "TransactionConfirmedLegitimate"
    TRANSACTION_CONFIRMED_FRAUD = "TransactionConfirmedFraud"
    PROFILE_UPDATE_REQUESTED = "ProfileUpdateRequested"
    PROFILE_UPDATED = "ProfileUpdated"
    PROFILE_TRANSACTION_QUARANTINED = "ProfileTransactionQuarantined"
    PROFILE_TRANSACTION_REJECTED = "ProfileTransactionRejected"


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    event_type: EventType
    aggregate_id: UUID
    occurred_at: datetime
    correlation_id: UUID
    payload: tuple[tuple[str, str], ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "occurred_at", utc(self.occurred_at))
        if self.schema_version < 1:
            raise ValueError("event schema version must be positive")
        if len({key for key, _ in self.payload}) != len(self.payload):
            raise ValueError("duplicate event payload key")
        for key, _ in self.payload:
            nonempty(key, "payload key")


@dataclass(frozen=True)
class OutboxEvent:
    event: DomainEvent
    attempts: int = 0
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.attempts < 0:
            raise ValueError("attempts cannot be negative")
        if self.published_at is not None:
            published = utc(self.published_at)
            if published < self.event.occurred_at:
                raise ValueError("publication cannot precede event creation")
            object.__setattr__(self, "published_at", published)


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
