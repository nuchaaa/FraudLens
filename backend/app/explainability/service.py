"""Factual presentation of model attributions, distinct from rules and hybrid policy."""

import math
from dataclasses import dataclass, field

from backend.app.explainability.contracts import SCORE_ATOL, ExplainableFraudModel, ModelExplanation
from backend.app.risk.entities import RiskReason
from backend.app.risk.service import ExperimentalRiskResult, Strategy

# Feature absence masks mirror behavior-v1; a numeric placeholder is not an observed fact.
BASELINE = ("profile_missing", "baseline_insufficient")
AVAILABILITY = {
    "amount_vs_customer_median": BASELINE,
    "amount_vs_customer_mean": BASELINE,
    "robust_amount_deviation": BASELINE,
    "mad_zero": BASELINE,
    "mad_floor_applied": BASELINE,
    "amount_vs_p95": BASELINE,
    "short_term_vs_long_term_amount_ratio": (*BASELINE, "short_baseline_insufficient"),
    "new_recipient": BASELINE,
    "unusual_hour": (*BASELINE, "typical_hours_missing"),
    "hour_deviation": (*BASELINE, "typical_hours_missing"),
    "transactions_last_5_min": ("activity_history_missing",),
    "transactions_last_10_min": ("activity_history_missing",),
    "transactions_last_hour": ("activity_history_missing",),
    "recipient_transactions_last_hour": ("activity_history_missing", "recipient_activity_missing"),
    "recipient_observed_age_days": ("recipient_activity_missing",),
    "device_changed": ("activity_history_missing", "device_change_missing"),
    "device_not_seen_before": ("activity_history_missing",),
    "days_since_last_transfer": ("activity_history_missing",),
}
LABELS = {
    "amount": "Transaction amount in the captured currency",
    "profile_missing": "Profile absence indicator",
    "baseline_insufficient": "Insufficient baseline indicator",
    "long_history_count": "Admitted long-window observation count",
    "short_history_count": "Admitted short-window observation count",
    "amount_vs_customer_median": "Amount divided by admitted long-window median",
    "amount_vs_customer_mean": "Amount divided by admitted long-window mean",
    "robust_amount_deviation": "Absolute amount deviation divided by floored MAD",
    "mad_zero": "Zero MAD indicator",
    "mad_floor_applied": "MAD denominator floor indicator",
    "amount_vs_p95": "Amount divided by admitted long-window p95",
    "short_term_vs_long_term_amount_ratio": "Short-window median divided by long-window median",
    "short_baseline_insufficient": "Insufficient short baseline indicator",
    "new_recipient": "Recipient absent from admitted history indicator",
    "unusual_hour": "Hour outside frequency-qualified admitted hours indicator",
    "hour_deviation": "Distance to nearest typical admitted hour",
    "typical_hours_missing": "Unavailable typical hours indicator",
    "transactions_last_5_min": "Captured prior transfers strictly within five minutes",
    "transactions_last_10_min": "Captured prior transfers strictly within ten minutes",
    "transactions_last_hour": "Captured prior transfers strictly within one hour",
    "recipient_transactions_last_hour": "Captured prior recipient transfers within one hour",
    "activity_history_count": "Captured raw activity count",
    "activity_history_missing": "Unavailable captured activity indicator",
    "recipient_observed_age_days": "Recipient observed activity age in bounded history, in days",
    "recipient_activity_missing": "Unavailable recipient activity indicator",
    "device_changed": "Device differs from last unambiguous captured device indicator",
    "device_change_missing": "Unavailable device comparison indicator",
    "device_not_seen_before": "Device absent from captured activity indicator",
    "days_since_last_transfer": "Days since last captured transfer",
}


@dataclass(frozen=True)
class ReadableContribution:
    feature: str
    value: float
    contribution: float
    missing_indicators: tuple[str, ...]
    message: str


def readable_contributions(explanation: ModelExplanation) -> tuple[ReadableContribution, ...]:
    values = dict(zip(explanation.features.names, explanation.features.values, strict=True))
    rows = []
    for name, value, contribution in zip(
        explanation.features.names,
        explanation.features.values,
        explanation.contributions,
        strict=True,
    ):
        missing = tuple(flag for flag in AVAILABILITY.get(name, ()) if values[flag] == 1)
        fact = (
            f"{LABELS[name]}: unavailable; encoded value {value:.6g} is a placeholder."
            if missing
            else f"{LABELS[name]}: encoded value {value:.6g}."
        )
        direction = (
            "adds to"
            if contribution > 0
            else "subtracts from"
            if contribution < 0
            else "does not change"
        )
        message = f"{fact} Model attribution {direction} the raw margin ({contribution:+.6g})."
        rows.append(ReadableContribution(name, value, contribution, missing, message))
    # Stable feature order breaks magnitude ties. All values remain in technical output.
    return tuple(sorted(rows, key=lambda row: -abs(row.contribution))[:5])


@dataclass(frozen=True)
class RiskExplanation:
    model: ModelExplanation | None
    top_model_contributions: tuple[ReadableContribution, ...]
    rule_reasons: tuple[RiskReason, ...]
    unavailable_rules: tuple[str, ...]
    version: str = field(default="explanation-v1-experimental", init=False)
    production_eligible: bool = field(default=False, init=False)
    calibrated: bool = field(default=False, init=False)
    causal: bool = field(default=False, init=False)
    scope: str = field(default="model_output_only_not_rule_or_hybrid_score", init=False)


def explain_risk(
    result: ExperimentalRiskResult,
    *,
    model: ExplainableFraudModel | None = None,
) -> RiskExplanation:
    explanation = None
    if result.policy.strategy != Strategy.RULES_ONLY:
        if model is None or result.prediction is None:
            raise ValueError("model explanation requires original model prediction")
        explanation = model.explain(result.features)
        if (
            explanation.features != result.features
            or explanation.model_version != result.prediction.model_version
            or not math.isclose(
                explanation.uncalibrated_score,
                result.prediction.probability,
                abs_tol=SCORE_ATOL,
                rel_tol=0,
            )
        ):
            raise ValueError("explanation does not match evaluated model, vector or score")
    return RiskExplanation(
        explanation,
        readable_contributions(explanation) if explanation else (),
        result.rules.reasons,
        result.unavailable_rules,
    )
