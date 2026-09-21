"""Bounded at-least-once delivery; implementations own short queue transactions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.shared.events import DomainEvent, EventPublisher


@dataclass(frozen=True)
class DeliveryPolicy:
    lease_seconds: int = 60
    max_attempts: int = 5
    retry_seconds: int = 5
    max_retry_seconds: int = 3600

    def __post_init__(self) -> None:
        if not 1 <= self.lease_seconds <= 3600 or not 1 <= self.max_attempts <= 100:
            raise ValueError("invalid lease or attempt bound")
        if not 1 <= self.retry_seconds <= self.max_retry_seconds <= 86400:
            raise ValueError("invalid retry bounds")

    def delay(self, attempt: int) -> int:
        return min(self.max_retry_seconds, self.retry_seconds * (1 << max(0, attempt - 1)))


@dataclass(frozen=True)
class DeliveryClaim:
    event: DomainEvent
    token: UUID
    attempt: int
    expires_at: datetime


class DeliveryQueue(Protocol):
    def claim(self) -> DeliveryClaim | None: ...
    def acknowledge(self, claim: DeliveryClaim) -> bool: ...
    def fail(self, claim: DeliveryClaim) -> bool: ...


@dataclass(frozen=True)
class DeliveryRun:
    claimed: int
    published: int
    failed: int
    stale: int


def dispatch(queue: DeliveryQueue, handler: EventPublisher, *, limit: int = 100) -> DeliveryRun:
    if not 1 <= limit <= 1000:
        raise ValueError("delivery limit must be between 1 and 1000")
    claimed = published = failed = stale = 0
    for _ in range(limit):
        claim = queue.claim()
        if claim is None:
            break
        claimed += 1
        try:
            handler.publish(claim.event)
        except Exception:
            # Intentionally retain only a fixed category; never log payloads/secrets.
            if queue.fail(claim):
                failed += 1
            else:
                stale += 1
        else:
            if queue.acknowledge(claim):
                published += 1
            else:
                stale += 1
    return DeliveryRun(claimed, published, failed, stale)
