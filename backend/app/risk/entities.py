from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.app.shared.validation import nonempty, probability, utc


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(StrEnum):
    ALLOW = "ALLOW"
    STEP_UP_VERIFICATION = "STEP_UP_VERIFICATION"
    HOLD_AND_REVIEW = "HOLD_AND_REVIEW"
    URGENT_REVIEW = "URGENT_REVIEW"


@dataclass(frozen=True)
class RiskReason:
    code: str
    message: str

    def __post_init__(self) -> None:
        nonempty(self.code, "code")
        nonempty(self.message, "message")


@dataclass(frozen=True)
class RiskAssessment:
    assessment_id: UUID
    transaction_id: UUID
    profile_snapshot_id: UUID
    score: float
    level: RiskLevel
    action: RecommendedAction
    reasons: tuple[RiskReason, ...]
    model_version: str
    feature_version: str
    rule_version: str
    policy_version: str
    strategy: str
    timestamp: datetime

    def __post_init__(self) -> None:
        probability(self.score)
        for name in (
            "model_version",
            "feature_version",
            "rule_version",
            "policy_version",
            "strategy",
        ):
            nonempty(getattr(self, name), name)
        object.__setattr__(self, "timestamp", utc(self.timestamp))
        expected_action = {
            RiskLevel.LOW: RecommendedAction.ALLOW,
            RiskLevel.MEDIUM: RecommendedAction.STEP_UP_VERIFICATION,
            RiskLevel.HIGH: RecommendedAction.HOLD_AND_REVIEW,
            RiskLevel.CRITICAL: RecommendedAction.URGENT_REVIEW,
        }[self.level]
        if self.action != expected_action:
            raise ValueError("risk level and recommended action are inconsistent")
