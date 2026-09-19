from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.app.shared.validation import nonempty, probability, utc


class AnalystVerdict(StrEnum):
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    LEGITIMATE = "LEGITIMATE"
    NEEDS_INVESTIGATION = "NEEDS_INVESTIGATION"


@dataclass(frozen=True)
class AnalystDecision:
    decision_id: UUID
    transaction_id: UUID
    assessment_id: UUID
    analyst_id: UUID
    verdict: AnalystVerdict
    model_prediction: float
    model_version: str
    timestamp: datetime
    comment: str

    def __post_init__(self) -> None:
        probability(self.model_prediction)
        nonempty(self.model_version, "model_version")
        nonempty(self.comment, "comment")
        object.__setattr__(self, "timestamp", utc(self.timestamp))
