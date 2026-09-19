from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.app.shared.validation import nonempty, utc


@dataclass(frozen=True)
class AuditEvent:
    audit_id: UUID
    actor_id: UUID
    action: str
    entity_id: UUID
    correlation_id: UUID
    timestamp: datetime
    detail: str

    def __post_init__(self) -> None:
        nonempty(self.action, "action")
        nonempty(self.detail, "detail")
        object.__setattr__(self, "timestamp", utc(self.timestamp))
