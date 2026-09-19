from dataclasses import dataclass

from backend.app.risk.entities import RecommendedAction, RiskLevel
from backend.app.shared.validation import nonempty, probability


@dataclass(frozen=True)
class DecisionPolicy:
    medium: float = 0.35
    high: float = 0.65
    critical: float = 0.85
    version: str = "decision-v1-experimental"

    def __post_init__(self) -> None:
        for score in (self.medium, self.high, self.critical):
            probability(score)
        if not 0 < self.medium < self.high < self.critical < 1:
            raise ValueError("thresholds must be strictly ordered within (0, 1)")
        nonempty(self.version, "version")

    def decide(self, score: float) -> tuple[RiskLevel, RecommendedAction]:
        probability(score)
        if score >= self.critical:
            return RiskLevel.CRITICAL, RecommendedAction.URGENT_REVIEW
        if score >= self.high:
            return RiskLevel.HIGH, RecommendedAction.HOLD_AND_REVIEW
        if score >= self.medium:
            return RiskLevel.MEDIUM, RecommendedAction.STEP_UP_VERIFICATION
        return RiskLevel.LOW, RecommendedAction.ALLOW
