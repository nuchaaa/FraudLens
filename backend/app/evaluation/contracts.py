import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.features.context import FeatureContext
from backend.app.feedback.entities import AnalystVerdict
from backend.app.risk.service import Strategy
from backend.app.shared.validation import nonempty, utc


class EvaluationUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationRecord:
    evaluation_id: UUID
    transaction_id: UUID
    customer_id: UUID
    currency: str
    actor_id: UUID
    created_at: datetime
    response_json: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", utc(self.created_at))
        document = json.loads(self.response_json)
        if (
            document.get("schema_version") != "experimental-evaluation-v1"
            or document.get("evaluation_id") != str(self.evaluation_id)
            or document.get("transaction_id") != str(self.transaction_id)
            or document.get("customer_id") != str(self.customer_id)
            or document.get("currency") != self.currency
            or document.get("actor_id") != str(self.actor_id)
            or document.get("created_at") != self.created_at.isoformat()
            or document.get("production_eligible") is not False
        ):
            raise ValueError("inconsistent evaluation envelope")


class EvaluationEngine(Protocol):
    def render(
        self,
        context: FeatureContext,
        strategy: Strategy,
        manifest_sha256: str | None,
    ) -> str:
        """Produce verified risk/explanation/context/provenance JSON or fail without writes."""
        ...


@dataclass(frozen=True)
class ReviewFeedback:
    feedback_id: UUID
    case_id: UUID
    actor_id: UUID
    verdict: AnalystVerdict
    timestamp: datetime
    comment: str
    sequence: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", utc(self.timestamp))
        nonempty(self.comment, "comment")
        if self.sequence < 1 or len(self.comment) > 2000:
            raise ValueError("invalid feedback sequence or comment size")
        if not isinstance(self.verdict, AnalystVerdict):
            raise ValueError("unsupported verdict")
