"""Experimental risk-v2 decision floor for independently evaluable sequence signals.

This policy does not change risk-v1's score, turn a signal into a probability, or
authorize a banking action. It only raises the suggested review level.
"""

import hashlib
import json
from dataclasses import dataclass

from backend.app.risk.entities import RecommendedAction, RiskLevel
from backend.app.risk.service import ExperimentalRiskResult, Strategy
from backend.app.sequence.engine import (
    SEQUENCE_VERSION,
    SequenceResult,
    SequenceStatus,
)

VERSION = "risk-v2-sequence-experimental"
SEQUENCE_CODES = (
    "CUMULATIVE_LOW_VALUE_SEQUENCE",
    "GRADUAL_AMOUNT_ESCALATION",
    "REPEATED_NEW_RECIPIENT",
    "CUMULATIVE_AMOUNT_EXPOSURE",
)


@dataclass(frozen=True)
class SequenceRiskPolicy:
    """Authored review floor, not a calibrated operating threshold."""

    minimum_level: RiskLevel = RiskLevel.MEDIUM
    version: str = VERSION

    def __post_init__(self) -> None:
        if self.version != VERSION or self.minimum_level != RiskLevel.MEDIUM:
            raise ValueError("unsupported sequence risk policy")

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "version": self.version,
                "minimum_level": self.minimum_level,
                "sequence_version": SEQUENCE_VERSION,
                "sequence_codes": SEQUENCE_CODES,
                "missing_policy": (
                    "matched_complete_signal_only; otherwise retain risk-v1 or abstain"
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class SequenceRiskDecision:
    policy_version: str
    policy_sha256: str
    base_policy_sha256: str
    sequence_policy_sha256: str
    status: str
    level: RiskLevel | None
    suggested_action: RecommendedAction | None
    matched_sequences: tuple[str, ...]
    unavailable_sequences: tuple[str, ...]
    decision_source: str
    calibrated: bool = False
    production_eligible: bool = False
    operational_action_executed: bool = False


DEFAULT_POLICY = SequenceRiskPolicy()


def decide_sequence_risk(
    base: ExperimentalRiskResult,
    sequence: SequenceResult,
    policy: SequenceRiskPolicy = DEFAULT_POLICY,
) -> SequenceRiskDecision:
    """Preserve risk-v1 unless an exact, complete sequence signal requires review."""
    if (
        base.policy.strategy != Strategy.RULES_ONLY
        or base.policy_sha256 != base.policy.fingerprint
        or base.prediction is not None
        or str(base.context_id) != sequence.context_id
        or str(base.transaction_id) != sequence.transaction_id
        or sequence.sequence_version != SEQUENCE_VERSION
        or sequence.policy_sha256 != sequence.policy.fingerprint
        or sequence.thresholds_calibrated is not False
        or tuple(item.code for item in sequence.outcomes) != SEQUENCE_CODES
        or any(not isinstance(item.status, SequenceStatus) for item in sequence.outcomes)
        or any(
            item.status == SequenceStatus.MATCHED
            and (item.missing_indicators or item.reason is None)
            for item in sequence.outcomes
        )
    ):
        raise ValueError("incompatible sequence risk evidence")
    matched = tuple(
        item.code for item in sequence.outcomes if item.status == SequenceStatus.MATCHED
    )
    unavailable = tuple(
        item.code for item in sequence.outcomes if item.status == SequenceStatus.NOT_EVALUATED
    )
    # An independently complete sequence match may demand review even if some
    # amount/device rules are unavailable. Missing sequence inputs never match.
    elevated = bool(matched) and base.level in (None, RiskLevel.LOW)
    level = policy.minimum_level if elevated else base.level
    action = RecommendedAction.STEP_UP_VERIFICATION if elevated else base.suggested_action
    return SequenceRiskDecision(
        policy.version,
        policy.fingerprint,
        base.policy_sha256,
        sequence.policy_sha256,
        "SCORED" if level is not None else "INSUFFICIENT_EVIDENCE",
        level,
        action,
        matched,
        unavailable,
        "SEQUENCE_REVIEW_FLOOR" if elevated else "RISK_V1" if level else "ABSTAIN",
    )
