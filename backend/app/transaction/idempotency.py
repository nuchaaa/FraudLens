import json
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.app.shared.validation import utc


@dataclass(frozen=True)
class IdempotencyRecord:
    """A completed request, committed atomically with its business effects."""

    principal_id: UUID
    key: str
    request_sha256: str
    transaction_id: UUID
    response_json: str
    status_code: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not 1 <= len(self.key) <= 200 or self.key != self.key.strip():
            raise ValueError(
                "idempotency key must contain 1-200 characters without edge whitespace"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_sha256):
            raise ValueError("request digest must be lowercase SHA-256")
        if not 200 <= self.status_code < 300:
            raise ValueError("only successful completed requests are recorded")
        if not isinstance(json.loads(self.response_json), dict):
            raise ValueError("stored response must be a JSON object")
        object.__setattr__(self, "created_at", utc(self.created_at))
