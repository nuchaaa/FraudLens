from dataclasses import replace
from datetime import datetime
from uuid import uuid4

import pytest

from backend.app.decision.policy import DecisionPolicy
from backend.app.risk.entities import RecommendedAction, RiskAssessment, RiskLevel
from backend.app.risk.strategies import (
    HybridRiskStrategy,
    MLOnlyRiskStrategy,
    RulesOnlyRiskStrategy,
)


@pytest.mark.parametrize(
    "score,level",
    [
        (0, RiskLevel.LOW),
        (0.3499, RiskLevel.LOW),
        (0.35, RiskLevel.MEDIUM),
        (0.65, RiskLevel.HIGH),
        (0.85, RiskLevel.CRITICAL),
        (1, RiskLevel.CRITICAL),
    ],
)
def test_threshold_boundaries(score: float, level: RiskLevel) -> None:
    assert DecisionPolicy().decide(score)[0] == level


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -0.01, 1.01])
def test_nonprobabilities_rejected(invalid: float) -> None:
    with pytest.raises(ValueError):
        DecisionPolicy().decide(invalid)
    with pytest.raises(ValueError):
        HybridRiskStrategy(invalid)
    with pytest.raises(ValueError):
        MLOnlyRiskStrategy().aggregate(invalid, 0.2)


def test_threshold_order() -> None:
    with pytest.raises(ValueError):
        DecisionPolicy(medium=0.7, high=0.6)


def test_risk_strategy_comparison() -> None:
    assert MLOnlyRiskStrategy().aggregate(0.8, 0.4) == 0.8
    assert RulesOnlyRiskStrategy().aggregate(0.8, 0.4) == 0.4
    assert HybridRiskStrategy(0.75).aggregate(0.8, 0.4) == pytest.approx(0.7)
    assert HybridRiskStrategy(0).aggregate(0.8, 0.4) == 0.4
    assert HybridRiskStrategy(1).aggregate(0.8, 0.4) == 0.8


def test_assessments_require_consistent_provenance(now: datetime) -> None:
    assessment = RiskAssessment(
        uuid4(),
        uuid4(),
        uuid4(),
        0.8,
        RiskLevel.HIGH,
        RecommendedAction.HOLD_AND_REVIEW,
        (),
        "model-v1",
        "features-v1",
        "rules-v1",
        "decision-v1",
        "hybrid",
        now,
    )
    for field in ("model_version", "feature_version", "rule_version", "policy_version", "strategy"):
        with pytest.raises(ValueError):
            replace(assessment, **{field: " "})
    with pytest.raises(ValueError, match="inconsistent"):
        replace(assessment, action=RecommendedAction.ALLOW)
