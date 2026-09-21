from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.explainability.contracts import ModelExplanation, sigmoid
from backend.app.explainability.service import LABELS, explain_risk, readable_contributions
from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import FEATURE_NAMES, extract_features
from backend.app.fraud.ports import FraudPrediction
from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.risk.service import RiskPolicy, Strategy, evaluate_risk
from backend.app.transaction.entities import Transaction


@pytest.fixture
def context(transaction: Transaction, profile: CustomerBehaviorProfile) -> FeatureContext:
    return FeatureContext(
        uuid4(),
        transaction,
        replace(profile, timezone="UTC"),
        "UTC",
        (),
        transaction.timestamp,
        ContextSource.DECLARED_OFFLINE,
    )


@pytest.fixture
def explanation(context: FeatureContext) -> ModelExplanation:
    return ModelExplanation("test-model", extract_features(context), (0.0,) * 29, 0, 0, 0.5)


@pytest.mark.parametrize(
    "change",
    [
        "nan",
        "infinity",
        "base",
        "margin",
        "score",
        "additivity",
        "link",
        "length",
        "order",
        "version",
        "model",
    ],
)
def test_invalid_explanation(explanation: ModelExplanation, change: str) -> None:
    changes = {
        "nan": {"contributions": (float("nan"),) + (0.0,) * 28},
        "infinity": {"contributions": (float("inf"),) + (0.0,) * 28},
        "base": {"base_value": float("inf")},
        "margin": {"raw_margin": float("nan")},
        "score": {"uncalibrated_score": 1.1},
        "additivity": {"base_value": 1},
        "link": {"uncalibrated_score": 0.8},
        "length": {"contributions": (0.0,)},
        "order": {"features": replace(explanation.features, names=tuple(reversed(FEATURE_NAMES)))},
        "version": {"features": replace(explanation.features, version="ulb-pca-v1")},
        "model": {"model_version": " "},
    }
    with pytest.raises(ValueError):
        replace(explanation, **changes[change])


@pytest.mark.parametrize("margin", [-1000.0, -10.0, 0.0, 10.0, 1000.0])
def test_stable_link_and_tolerance(explanation: ModelExplanation, margin: float) -> None:
    result = replace(
        explanation, base_value=margin, raw_margin=margin, uncalibrated_score=sigmoid(margin)
    )
    assert 0 <= result.uncalibrated_score <= 1
    replace(result, base_value=margin + 1e-7)
    with pytest.raises(ValueError, match="reconstruct"):
        replace(result, base_value=margin + 0.01)


def test_stable_rank_ties_and_signed_messages(explanation: ModelExplanation) -> None:
    assert tuple(LABELS) == FEATURE_NAMES
    values = (0.5, -0.5, 0.5, -0.5) + (0.0,) * 25
    result = readable_contributions(replace(explanation, contributions=values))
    assert tuple(row.feature for row in result) == FEATURE_NAMES[:5]
    assert "adds to" in result[0].message
    assert "subtracts from" in result[1].message
    assert "does not change" in result[4].message


@pytest.mark.parametrize(
    "name",
    [
        "amount_vs_customer_median",
        "unusual_hour",
        "device_changed",
        "recipient_observed_age_days",
        "short_term_vs_long_term_amount_ratio",
    ],
)
def test_missing_values_are_placeholders(context: FeatureContext, name: str) -> None:
    cold = replace(context, profile=None)
    values = tuple(1.0 if feature == name else 0 for feature in FEATURE_NAMES)
    result = ModelExplanation("test-model", extract_features(cold), values, -1, 0, 0.5)
    row = readable_contributions(result)[0]
    assert row.feature == name
    assert row.value == 0
    assert row.missing_indicators
    assert "unavailable" in row.message and "placeholder" in row.message
    assert "account age" not in row.message


def test_zero_mad_not_mislabelled_unavailable(context: FeatureContext) -> None:
    assert context.profile
    profile = replace(
        context.profile,
        observations=tuple(
            replace(o, amount=Decimal("30000")) for o in context.profile.observations
        ),
    )
    features = extract_features(replace(context, profile=profile))
    contributions = tuple(1.0 if name == "robust_amount_deviation" else 0 for name in FEATURE_NAMES)
    result = ModelExplanation("test-model", features, contributions, -1, 0, 0.5)
    row = readable_contributions(result)[0]
    assert not row.missing_indicators
    assert "floored MAD" in row.message
    assert features.values[FEATURE_NAMES.index("mad_floor_applied")] == 1


class Explainable:
    def __init__(self, explanation: ModelExplanation, timestamp: datetime) -> None:
        self.explanation = explanation
        self.timestamp = timestamp

    def predict(self, features: FeatureVector) -> FraudPrediction:
        return FraudPrediction(0.5, "test-model", features.version, self.timestamp)

    def explain(self, features: FeatureVector) -> ModelExplanation:
        return self.explanation


@pytest.mark.parametrize("mode", list(Strategy))
def test_explanation_keeps_rules_and_model_separate(
    context: FeatureContext, explanation: ModelExplanation, mode: Strategy
) -> None:
    model = Explainable(explanation, context.captured_at)
    result = evaluate_risk(
        context, RiskPolicy(mode), model=model, clock=lambda: context.captured_at
    )
    output = explain_risk(result, model=model)
    assert output.rule_reasons == result.rules.reasons
    assert output.unavailable_rules == result.unavailable_rules
    assert output.causal is output.calibrated is output.production_eligible is False
    if mode == Strategy.RULES_ONLY:
        assert output.model is None
        assert output.top_model_contributions == ()
    else:
        assert output.model == explanation
        if mode == Strategy.HYBRID:
            assert result.score is None
            assert output.model is not None


@pytest.mark.parametrize("change", ["missing", "model", "vector", "score", "failure"])
def test_mismatched_explanation_fails(
    context: FeatureContext, explanation: ModelExplanation, change: str
) -> None:
    model = Explainable(explanation, context.captured_at)
    result = evaluate_risk(context, RiskPolicy(), model=model, clock=lambda: context.captured_at)
    if change == "missing":
        with pytest.raises(ValueError, match="requires"):
            explain_risk(result)
        return
    if change == "model":
        model.explanation = replace(explanation, model_version="another-model")
    elif change == "vector":
        model.explanation = replace(
            explanation,
            features=replace(
                explanation.features, values=(999.0, *explanation.features.values[1:])
            ),
        )
    elif change == "score":
        model.explanation = replace(
            explanation, base_value=1, raw_margin=1, uncalibrated_score=sigmoid(1)
        )
    else:

        class Failed(Explainable):
            def explain(self, features: FeatureVector) -> ModelExplanation:
                raise ValueError("explanation failed")

        model = Failed(explanation, context.captured_at)
    with pytest.raises(ValueError):
        explain_risk(result, model=model)


def test_contribution_sum_overflow_is_rejected(explanation: ModelExplanation) -> None:
    with pytest.raises(ValueError, match="overflow"):
        replace(explanation, contributions=(1e308, 1e308) + (0.0,) * 27)
