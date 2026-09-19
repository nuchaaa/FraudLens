from dataclasses import dataclass
from typing import Protocol

from backend.app.shared.validation import probability


class RiskAggregation(Protocol):
    def aggregate(self, model_score: float, rule_score: float) -> float: ...


class MLOnlyRiskStrategy:
    def aggregate(self, model_score: float, rule_score: float) -> float:
        probability(model_score)
        probability(rule_score)
        return model_score


class RulesOnlyRiskStrategy:
    def aggregate(self, model_score: float, rule_score: float) -> float:
        probability(model_score)
        probability(rule_score)
        return rule_score


@dataclass(frozen=True)
class HybridRiskStrategy:
    """Convex combination; weight must be explicitly selected by the caller."""

    model_weight: float

    def __post_init__(self) -> None:
        probability(self.model_weight)

    def aggregate(self, model_score: float, rule_score: float) -> float:
        probability(model_score)
        probability(rule_score)
        return self.model_weight * model_score + (1 - self.model_weight) * rule_score
