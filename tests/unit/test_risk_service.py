import json
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from math import nextafter
from pathlib import Path
from uuid import uuid4

import pytest

from backend.adapters.features.artifacts import decode_context, encode_context, write_context
from backend.adapters.risk.__main__ import main
from backend.app.decision.policy import DecisionPolicy
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import extract_features
from backend.app.fraud.ports import FraudPrediction
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.risk.entities import RecommendedAction, RiskLevel
from backend.app.risk.service import RiskPolicy, Strategy, evaluate_risk, score_rules
from backend.app.rules.engine import RulePolicy, RuleStatus, evaluate_context
from backend.app.transaction.entities import Transaction


class Model:
    def __init__(self, timestamp: datetime, score: float = 0.8) -> None:
        self.timestamp = timestamp
        self.score = score
        self.inputs: list[FeatureVector] = []

    def predict(self, features: FeatureVector) -> FraudPrediction:
        self.inputs.append(features)
        return FraudPrediction(self.score, "test-model", features.version, self.timestamp)


@pytest.fixture
def context(transaction: Transaction, profile: CustomerBehaviorProfile) -> FeatureContext:
    prior = replace(
        transaction, transaction_id=uuid4(), timestamp=transaction.timestamp - timedelta(minutes=1)
    )
    return FeatureContext(
        uuid4(),
        transaction,
        replace(profile, timezone="UTC"),
        "UTC",
        (prior,),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )


@pytest.mark.parametrize(
    "strategy,expected", [(Strategy.RULES_ONLY, 0), (Strategy.ML_ONLY, 0.8), (Strategy.HYBRID, 0.4)]
)
def test_three_strategies_same_facts(
    context: FeatureContext, strategy: Strategy, expected: float
) -> None:
    model = Model(context.captured_at)
    result = evaluate_risk(
        context, RiskPolicy(strategy), model=model, clock=lambda: context.captured_at
    )
    assert result.score == pytest.approx(expected)
    assert result.rule_score == 0
    assert result.unavailable_rules == ()
    assert result.status == "SCORED"
    assert (
        result.production_eligible
        is result.calibrated
        is result.operational_action_executed
        is False
    )
    assert result.features == extract_features(context)
    if strategy == Strategy.RULES_ONLY:
        assert model.inputs == []
        assert result.prediction is None
    else:
        assert model.inputs == [result.features]
        assert result.prediction is not None
        assert result.prediction.model_version == "test-model"


@pytest.mark.parametrize("strategy", list(Strategy))
def test_cold_start_never_becomes_zero_rule_score(
    context: FeatureContext, strategy: Strategy
) -> None:
    cold = replace(context, profile=None, activity=())
    result = evaluate_risk(
        cold,
        RiskPolicy(strategy),
        model=Model(context.captured_at),
        clock=lambda: context.captured_at,
    )
    assert result.rule_score is None
    assert len(result.unavailable_rules) == 5
    assert all(item.status == RuleStatus.NOT_EVALUATED for item in result.rules.outcomes)
    if strategy == Strategy.ML_ONLY:
        assert result.score == 0.8
        assert result.status == "SCORED"
    else:
        assert result.score is result.level is result.suggested_action is None
        assert result.status == "INSUFFICIENT_EVIDENCE"


def test_partial_evidence_preserved_without_renormalization(context: FeatureContext) -> None:
    changed = replace(
        context, candidate=replace(context.candidate, amount=Decimal("8000000")), activity=()
    )
    result = evaluate_risk(
        changed, RiskPolicy(Strategy.RULES_ONLY), clock=lambda: context.captured_at
    )
    assert result.rules.reasons[0].code == "AMOUNT_ANOMALY"
    assert result.unavailable_rules == ("HIGH_VELOCITY", "DEVICE_CHANGED")
    assert result.rule_score is result.score is result.suggested_action is None
    assert context.profile is not None
    assert result.profile_version == context.profile.version
    assert context.candidate.amount == Decimal("30000")
    assert len(context.profile.observations) == 20


def test_weighted_all_matches_and_stable_reasons(context: FeatureContext) -> None:
    candidate = replace(
        context.candidate,
        amount=Decimal("8000000"),
        recipient_id=uuid4(),
        timestamp=context.candidate.timestamp + timedelta(hours=5),
        device_id="changed",
    )
    prior = tuple(
        replace(
            context.activity[0],
            transaction_id=uuid4(),
            timestamp=candidate.timestamp - timedelta(seconds=i + 1),
        )
        for i in range(5)
    )
    changed = replace(context, candidate=candidate, activity=prior, captured_at=candidate.timestamp)
    policy = RiskPolicy(Strategy.RULES_ONLY)
    result = evaluate_risk(changed, policy, clock=lambda: changed.captured_at)
    assert result.score == 1
    assert result.level == RiskLevel.CRITICAL
    assert result.suggested_action == RecommendedAction.URGENT_REVIEW
    assert [reason.code for reason in result.rules.reasons] == [
        "AMOUNT_ANOMALY",
        "NEW_RECIPIENT",
        "HIGH_VELOCITY",
        "UNUSUAL_TIME",
        "DEVICE_CHANGED",
    ]
    assert result == evaluate_risk(
        decode_context(encode_context(changed)), policy, clock=lambda: changed.captured_at
    )
    amount_only = replace(context, candidate=replace(context.candidate, amount=Decimal("8000000")))
    assert evaluate_risk(
        amount_only, policy, clock=lambda: context.captured_at
    ).score == pytest.approx(0.4)


@pytest.mark.parametrize(
    "threshold,below,at",
    [
        (0.35, RiskLevel.LOW, RiskLevel.MEDIUM),
        (0.65, RiskLevel.MEDIUM, RiskLevel.HIGH),
        (0.85, RiskLevel.HIGH, RiskLevel.CRITICAL),
    ],
)
def test_composed_decision_boundaries(
    context: FeatureContext, threshold: float, below: RiskLevel, at: RiskLevel
) -> None:
    for score, level in ((nextafter(threshold, 0), below), (threshold, at)):
        result = evaluate_risk(
            context,
            RiskPolicy(Strategy.ML_ONLY),
            model=Model(context.captured_at, score),
            clock=lambda: context.captured_at,
        )
        assert result.level == level


@pytest.mark.parametrize(
    "change", ["weight", "rule_weights", "rule_threshold", "decision", "strategy"]
)
def test_full_policy_fingerprint(context: FeatureContext, change: str) -> None:
    policy = RiskPolicy()
    changed = {
        "weight": replace(policy, model_weight=0.7),
        "rule_weights": replace(policy, rule_weights=(0.3, 0.25, 0.25, 0.1, 0.1)),
        "rule_threshold": replace(policy, rules=RulePolicy(11)),
        "decision": replace(policy, decision=DecisionPolicy(medium=0.4)),
        "strategy": replace(policy, strategy=Strategy.RULES_ONLY),
    }[change]
    assert changed.fingerprint != policy.fingerprint
    assert replace(policy, rules=RulePolicy(10)).fingerprint == policy.fingerprint


@pytest.mark.parametrize(
    "updates",
    [
        {"version": "risk-v2"},
        {"strategy": "hybrid"},
        {"model_weight": float("nan")},
        {"model_weight": 0},
        {"model_weight": 1},
        {"rule_weights": (0.5, 0.5)},
        {"rule_weights": (0.4, 0.15, 0.25, 0.1, 0.2)},
        {"rule_weights": (0.5, 0.15, 0.25, 0.1, 0)},
        {"rule_weights": (float("inf"), 0.15, 0.25, 0.1, 0.1)},
        {"decision": DecisionPolicy(version="decision-v2")},
    ],
)
def test_invalid_policies(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(RiskPolicy(), **updates)


@pytest.mark.parametrize("kind", ["order", "version", "feature", "policy", "hash", "status"])
def test_incompatible_rule_results(context: FeatureContext, kind: str) -> None:
    result = evaluate_context(context)
    if kind == "order":
        result = replace(result, outcomes=tuple(reversed(result.outcomes)))
    elif kind == "version":
        result = replace(result, rule_version="rules-v2")
    elif kind == "feature":
        result = replace(result, feature_version="ulb-pca-v1")
    elif kind == "policy":
        result = replace(result, policy=RulePolicy(11))
    elif kind == "hash":
        result = replace(result, policy_sha256="bad")
    else:
        result = replace(
            result, outcomes=(replace(result.outcomes[0], status="bogus"), *result.outcomes[1:])
        )
    with pytest.raises(ValueError, match="incompatible"):
        score_rules(result, RiskPolicy())


def test_missing_failed_and_incompatible_model_do_not_fallback(context: FeatureContext) -> None:
    with pytest.raises(ValueError, match="requires"):
        evaluate_risk(context, RiskPolicy())

    class Failed:
        def predict(self, features: FeatureVector) -> FraudPrediction:
            raise RuntimeError("model failed")

    with pytest.raises(RuntimeError, match="model failed"):
        evaluate_risk(context, RiskPolicy(), model=Failed())

    class WrongVersion:
        def predict(self, features: FeatureVector) -> FraudPrediction:
            return FraudPrediction(0.5, "test-model", "ulb-pca-v1", context.captured_at)

    with pytest.raises(ValueError, match="version"):
        evaluate_risk(context, RiskPolicy(), model=WrongVersion())
    with pytest.raises(ValueError, match="precede"):
        evaluate_risk(
            context,
            RiskPolicy(Strategy.RULES_ONLY),
            clock=lambda: context.captured_at - timedelta(seconds=1),
        )
    with pytest.raises(ValueError, match="precede"):
        evaluate_risk(
            context,
            RiskPolicy(),
            model=Model(context.captured_at + timedelta(seconds=1)),
            clock=lambda: context.captured_at,
        )


def test_rules_cli_without_model_or_database(
    context: FeatureContext,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "context.json"
    write_context(path, context)
    monkeypatch.setenv("FRAUDLENS_DATABASE_URL", "invalid")
    monkeypatch.setenv("FRAUDLENS_API_PRINCIPALS", "invalid")
    args = ["--context", str(path), "--strategy", "rules_only"]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["score"] == 0
    assert result["suggested_action"] == "ALLOW"
    assert result["operational_action_executed"] is False
    assert result["prediction"] is None
    assert main([*args, "--model-weight", "nan"]) == 1
    assert main([*args, "--bundle", "invalid"]) == 1
    assert main(["--context", str(path), "--strategy", "hybrid"]) == 1
    assert main(["--context", str(path / "absent"), "--strategy", "rules_only"]) == 1
