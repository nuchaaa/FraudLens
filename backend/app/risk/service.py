"""Experimental read-only risk composition; scores are not fraud probabilities."""

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from backend.app.decision.policy import DecisionPolicy
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import extract_features
from backend.app.fraud.ports import FraudModel, FraudPrediction
from backend.app.fraud.service import predict_experimental_context
from backend.app.risk.entities import RecommendedAction, RiskLevel
from backend.app.risk.strategies import (
    HybridRiskStrategy,
    MLOnlyRiskStrategy,
    RulesOnlyRiskStrategy,
)
from backend.app.rules.engine import (
    RULE_VERSION,
    RulePolicy,
    RuleResult,
    RuleStatus,
    evaluate_rules,
)
from backend.app.shared.validation import probability, utc

RISK_VERSION = "risk-v1-experimental"
RULE_CODES = ("AMOUNT_ANOMALY", "NEW_RECIPIENT", "HIGH_VELOCITY", "UNUSUAL_TIME", "DEVICE_CHANGED")


class Strategy(StrEnum):
    RULES_ONLY = "rules_only"
    ML_ONLY = "ml_only"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class RiskPolicy:
    """Authored demonstration parameters, never fitted or calibrated thresholds."""

    strategy: Strategy = Strategy.HYBRID
    model_weight: float = 0.5
    rule_weights: tuple[float, ...] = (0.4, 0.15, 0.25, 0.1, 0.1)
    rules: RulePolicy = field(default_factory=RulePolicy)
    decision: DecisionPolicy = field(default_factory=DecisionPolicy)
    version: str = RISK_VERSION

    def __post_init__(self) -> None:
        if self.version != RISK_VERSION or not isinstance(self.strategy, Strategy):
            raise ValueError("unsupported risk policy version or strategy")
        probability(self.model_weight)
        if self.strategy == Strategy.HYBRID and not 0 < self.model_weight < 1:
            raise ValueError("hybrid requires both components; use an explicit single strategy")
        if not isinstance(self.rule_weights, tuple) or len(self.rule_weights) != len(RULE_CODES):
            raise ValueError("rule weights must follow the five rules-v1 codes")
        for weight in self.rule_weights:
            probability(weight)
            if weight <= 0:
                raise ValueError("each rule must have positive weight")
        if not math.isclose(math.fsum(self.rule_weights), 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("rule weights must sum to one")
        if self.decision.version != "decision-v1-experimental":
            raise ValueError("unsupported decision policy version")

    @property
    def fingerprint(self) -> str:
        payload = asdict(self)
        # Canonical numeric representation makes equivalent integer/float settings identical.
        payload["model_weight"] = float(self.model_weight)
        payload["rule_weights"] = tuple(float(w) for w in self.rule_weights)
        payload["rules"]["amount_median_ratio"] = float(self.rules.amount_median_ratio)
        for name in ("medium", "high", "critical"):
            payload["decision"][name] = float(payload["decision"][name])
        payload["rule_codes"] = RULE_CODES
        payload["rule_version"] = RULE_VERSION
        payload["missing_policy"] = "abstain_if_required_rule_unavailable"
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


@dataclass(frozen=True)
class ExperimentalRiskResult:
    context_id: UUID
    transaction_id: UUID
    profile_version: int | None
    context_source: ContextSource
    captured_at: datetime
    features: FeatureVector
    rules: RuleResult
    policy: RiskPolicy
    policy_sha256: str
    prediction: FraudPrediction | None
    rule_score: float | None
    score: float | None
    level: RiskLevel | None
    suggested_action: RecommendedAction | None
    unavailable_rules: tuple[str, ...]
    status: str
    evaluated_at: datetime
    production_eligible: bool = field(default=False, init=False)
    calibrated: bool = field(default=False, init=False)
    operational_action_executed: bool = field(default=False, init=False)
    admission_workflow_verified: bool = field(default=False, init=False)


def score_rules(result: RuleResult, policy: RiskPolicy) -> float | None:
    if (
        result.rule_version != RULE_VERSION
        or result.feature_version != "behavior-v1"
        or tuple(item.code for item in result.outcomes) != RULE_CODES
        or result.policy != policy.rules
        or result.policy_sha256 != policy.rules.fingerprint
        or any(not isinstance(item.status, RuleStatus) for item in result.outcomes)
    ):
        raise ValueError("incompatible rule results")
    if any(item.status == RuleStatus.NOT_EVALUATED for item in result.outcomes):
        return None
    # Normalize only the complete fixed set, never a subset of available rules.
    return math.fsum(
        weight
        for item, weight in zip(result.outcomes, policy.rule_weights, strict=True)
        if item.status == RuleStatus.MATCHED
    ) / math.fsum(policy.rule_weights)


def evaluate_risk(
    context: FeatureContext,
    policy: RiskPolicy,
    *,
    model: FraudModel | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ExperimentalRiskResult:
    features = extract_features(context)
    rules = evaluate_rules(features, policy.rules)
    rule_score = score_rules(rules, policy)
    prediction = None
    if policy.strategy != Strategy.RULES_ONLY:
        if model is None:
            raise ValueError("selected strategy requires an explicit experimental model")
        prediction = predict_experimental_context(model, context)
    score = None
    if policy.strategy == Strategy.ML_ONLY:
        assert prediction is not None
        # The unused operand repeats the known value; no missing score is fabricated.
        score = MLOnlyRiskStrategy().aggregate(prediction.probability, prediction.probability)
    elif rule_score is not None:
        if policy.strategy == Strategy.RULES_ONLY:
            score = RulesOnlyRiskStrategy().aggregate(rule_score, rule_score)
        else:
            assert prediction is not None
            score = HybridRiskStrategy(policy.model_weight).aggregate(
                prediction.probability, rule_score
            )
    level, action = policy.decision.decide(score) if score is not None else (None, None)
    timestamp = utc(clock())
    if timestamp < context.captured_at or (prediction and timestamp < prediction.timestamp):
        raise ValueError("evaluation cannot precede input capture or inference")
    return ExperimentalRiskResult(
        context.context_id,
        context.candidate.transaction_id,
        context.profile.version if context.profile else None,
        context.source,
        context.captured_at,
        features,
        rules,
        policy,
        policy.fingerprint,
        prediction,
        rule_score,
        score,
        level,
        action,
        tuple(item.code for item in rules.outcomes if item.status == RuleStatus.NOT_EVALUATED),
        "SCORED" if score is not None else "INSUFFICIENT_EVIDENCE",
        timestamp,
    )
