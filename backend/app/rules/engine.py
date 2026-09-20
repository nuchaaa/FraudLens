"""Deterministic descriptive rules; no probability, verdict or profile admission."""

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from backend.app.features.context import FEATURE_VERSION, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import FEATURE_NAMES, extract_features
from backend.app.risk.entities import RiskReason

RULE_VERSION = "rules-v1"


@dataclass(frozen=True)
class RulePolicy:
    """Uncalibrated research thresholds, recorded with every evaluation."""

    amount_median_ratio: float = 10.0
    prior_transfers_5_min: int = 5

    def __post_init__(self) -> None:
        import math

        if not math.isfinite(self.amount_median_ratio) or self.amount_median_ratio <= 1:
            raise ValueError("amount ratio must be finite and greater than one")
        if type(self.prior_transfers_5_min) is not int or self.prior_transfers_5_min < 1:
            raise ValueError("velocity threshold must be a positive integer")

    @property
    def fingerprint(self) -> str:
        document = json.dumps(
            {
                "amount_median_ratio": float(self.amount_median_ratio),
                "prior_transfers_5_min": self.prior_transfers_5_min,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return hashlib.sha256(document.encode()).hexdigest()


DEFAULT_POLICY = RulePolicy()


class RuleStatus(StrEnum):
    MATCHED = "MATCHED"
    NOT_MATCHED = "NOT_MATCHED"
    NOT_EVALUATED = "NOT_EVALUATED"


def validated_values(features: FeatureVector) -> dict[str, float]:
    if features.version != FEATURE_VERSION or features.names != FEATURE_NAMES:
        raise ValueError("rules-v1 requires the exact ordered behavior-v1 contract")
    values = dict(zip(features.names, features.values, strict=True))
    flags = (
        "profile_missing",
        "baseline_insufficient",
        "short_baseline_insufficient",
        "mad_zero",
        "mad_floor_applied",
        "new_recipient",
        "unusual_hour",
        "typical_hours_missing",
        "activity_history_missing",
        "recipient_activity_missing",
        "device_changed",
        "device_change_missing",
        "device_not_seen_before",
    )
    if any(values[name] not in (0, 1) for name in flags):
        raise ValueError("feature flags must be binary")
    if any(value < 0 for value in features.values):
        raise ValueError("behavior-v1 values must be nonnegative")
    for name in (
        "transactions_last_5_min",
        "transactions_last_10_min",
        "transactions_last_hour",
        "recipient_transactions_last_hour",
        "activity_history_count",
        "long_history_count",
        "short_history_count",
    ):
        if not float(values[name]).is_integer():
            raise ValueError("history counts must be integers")
    if not (
        values["transactions_last_5_min"]
        <= values["transactions_last_10_min"]
        <= values["transactions_last_hour"]
        <= values["activity_history_count"]
    ):
        raise ValueError("velocity counts are inconsistent")
    return values


@dataclass(frozen=True)
class RuleOutcome:
    code: str
    status: RuleStatus
    feature: str
    observed: float
    threshold: float
    missing_indicators: tuple[str, ...]
    reason: RiskReason | None


@dataclass(frozen=True)
class ThresholdSpecification:
    code: str
    feature: str
    threshold: float
    missing_indicators: tuple[str, ...]
    message: str

    def outcome(self, features: FeatureVector) -> RuleOutcome:
        values = validated_values(features)
        missing = tuple(name for name in self.missing_indicators if values[name] == 1)
        observed = values[self.feature]
        matched = not missing and observed >= self.threshold
        status = (
            RuleStatus.NOT_EVALUATED
            if missing
            else RuleStatus.MATCHED
            if matched
            else RuleStatus.NOT_MATCHED
        )
        return RuleOutcome(
            self.code,
            status,
            self.feature,
            observed,
            self.threshold,
            missing,
            RiskReason(self.code, self.message.format(value=observed, threshold=self.threshold))
            if matched
            else None,
        )

    def evaluate(self, features: FeatureVector) -> RiskReason | None:
        """Satisfies the existing FraudSpecification port; reports retain missingness."""
        return self.outcome(features).reason


def specifications(policy: RulePolicy) -> tuple[ThresholdSpecification, ...]:
    return (
        ThresholdSpecification(
            "AMOUNT_ANOMALY",
            "amount_vs_customer_median",
            policy.amount_median_ratio,
            ("profile_missing", "baseline_insufficient"),
            "Amount is {value:.6g} times the admitted long-window median "
            "(threshold {threshold:g}).",
        ),
        ThresholdSpecification(
            "NEW_RECIPIENT",
            "new_recipient",
            1,
            ("profile_missing", "baseline_insufficient"),
            "Recipient is absent from the admitted long-window history.",
        ),
        ThresholdSpecification(
            "HIGH_VELOCITY",
            "transactions_last_5_min",
            policy.prior_transfers_5_min,
            ("activity_history_missing",),
            "Captured activity contains {value:g} prior transfers strictly within five minutes.",
        ),
        ThresholdSpecification(
            "UNUSUAL_TIME",
            "unusual_hour",
            1,
            ("profile_missing", "baseline_insufficient", "typical_hours_missing"),
            "Transaction hour is outside the admitted history's frequency-qualified hours.",
        ),
        ThresholdSpecification(
            "DEVICE_CHANGED",
            "device_changed",
            1,
            ("activity_history_missing", "device_change_missing"),
            "Device differs from the last unambiguous device in captured activity.",
        ),
    )


@dataclass(frozen=True)
class RuleResult:
    rule_version: str
    feature_version: str
    policy: RulePolicy
    policy_sha256: str
    outcomes: tuple[RuleOutcome, ...]

    @property
    def reasons(self) -> tuple[RiskReason, ...]:
        return tuple(item.reason for item in self.outcomes if item.reason is not None)


def evaluate_rules(features: FeatureVector, policy: RulePolicy = DEFAULT_POLICY) -> RuleResult:
    validated_values(features)
    return RuleResult(
        RULE_VERSION,
        features.version,
        policy,
        policy.fingerprint,
        tuple(spec.outcome(features) for spec in specifications(policy)),
    )


def evaluate_context(context: FeatureContext, policy: RulePolicy = DEFAULT_POLICY) -> RuleResult:
    return evaluate_rules(extract_features(context), policy)


def report(context: FeatureContext, policy: RulePolicy = DEFAULT_POLICY) -> dict[str, object]:
    """JSON-ready local report, retaining input identity and policy; no live lookups."""
    return {
        "context_id": str(context.context_id),
        "transaction_id": str(context.candidate.transaction_id),
        "profile_version": context.profile.version if context.profile else None,
        "admission_workflow_verified": False,
        "thresholds_calibrated": False,
        **asdict(evaluate_context(context, policy)),
    }
