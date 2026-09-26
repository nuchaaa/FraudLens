"""Deterministic sequence evidence; never a probability, verdict or action."""

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from typing import Any
from uuid import UUID

from backend.app.features.context import FeatureContext
from backend.app.profile.read_model import ProfileReadPolicy, summarize_window
from backend.app.risk.entities import RiskReason
from backend.app.transaction.entities import Transaction

SEQUENCE_VERSION = "sequence-v1-experimental"


@dataclass(frozen=True)
class SequencePolicy:
    """Authored research thresholds; none are calibrated operating points."""

    window_hours: int = 24
    low_value_count: int = 4
    low_value_ceiling_ratio: Decimal = Decimal("1")
    low_value_cumulative_ratio: Decimal = Decimal("2")
    escalation_count: int = 4
    escalation_growth_ratio: Decimal = Decimal("2")
    escalation_cumulative_ratio: Decimal = Decimal("2")
    repeated_new_recipient_count: int = 3
    exposure_count: int = 3
    exposure_cumulative_ratio: Decimal = Decimal("5")

    def __post_init__(self) -> None:
        counts = (
            self.window_hours,
            self.low_value_count,
            self.escalation_count,
            self.repeated_new_recipient_count,
            self.exposure_count,
        )
        ratios = (
            self.low_value_ceiling_ratio,
            self.low_value_cumulative_ratio,
            self.escalation_growth_ratio,
            self.escalation_cumulative_ratio,
            self.exposure_cumulative_ratio,
        )
        if any(type(value) is not int or value < 1 for value in counts):
            raise ValueError("sequence counts and window must be positive integers")
        if self.low_value_count < 2 or self.escalation_count < 2:
            raise ValueError("sequence patterns require at least two transactions")
        if any(not value.is_finite() or value <= 0 for value in ratios):
            raise ValueError("sequence ratios must be finite and positive")
        if self.escalation_growth_ratio <= 1:
            raise ValueError("escalation growth ratio must exceed one")

    @property
    def fingerprint(self) -> str:
        document = json.dumps(
            {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in asdict(self).items()
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(document.encode()).hexdigest()


DEFAULT_SEQUENCE_POLICY = SequencePolicy()


class SequenceStatus(StrEnum):
    MATCHED = "MATCHED"
    NOT_MATCHED = "NOT_MATCHED"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class SequenceOutcome:
    code: str
    status: SequenceStatus
    observed_count: int
    observed_amount: Decimal
    observed_cumulative_ratio: Decimal | None
    observed_growth_ratio: Decimal | None
    threshold_count: int
    threshold_cumulative_ratio: Decimal | None
    threshold_growth_ratio: Decimal | None
    window_hours: int
    missing_indicators: tuple[str, ...]
    reason: RiskReason | None


@dataclass(frozen=True)
class SequenceResult:
    sequence_version: str
    context_id: str
    transaction_id: str
    policy: SequencePolicy
    policy_sha256: str
    thresholds_calibrated: bool
    outcomes: tuple[SequenceOutcome, ...]

    @property
    def reasons(self) -> tuple[RiskReason, ...]:
        return tuple(item.reason for item in self.outcomes if item.reason is not None)


def evaluate_sequence(
    context: FeatureContext, policy: SequencePolicy = DEFAULT_SEQUENCE_POLICY
) -> SequenceResult:
    """Evaluate candidate-inclusive temporal patterns from one already captured context."""
    candidate = context.candidate
    lower = candidate.timestamp - timedelta(hours=policy.window_hours)
    window = (*(tx for tx in context.activity if tx.timestamp > lower), candidate)
    profile = context.profile
    missing = []
    median: Decimal | None = None
    known_recipients: frozenset[UUID] = frozenset()
    if profile is None:
        missing.append("profile_missing")
    elif not profile.admission_workflow_verified:
        missing.append("profile_workflow_unverified")
    else:
        rolled = replace(
            profile,
            as_of=candidate.timestamp,
            observations=tuple(
                o for o in profile.observations if o.timestamp < candidate.timestamp
            ),
        )
        baseline = summarize_window(
            rolled,
            rolled.long_window_days,
            ProfileReadPolicy(version="profile-read-v1"),
        )
        if baseline.amounts is None or baseline.amounts.count < 5:
            missing.append("baseline_insufficient")
        else:
            median = baseline.amounts.median
            known_recipients = frozenset(baseline.known_recipients)
    if not context.activity:
        missing.append("activity_history_missing")
    missing_tuple = tuple(missing)
    outcomes = (
        _low_value(window, median, missing_tuple, policy),
        _escalation(window, median, missing_tuple, policy),
        _recipient_sequence(window, median, known_recipients, missing_tuple, policy),
        _cumulative_exposure(window, median, missing_tuple, policy),
    )
    return SequenceResult(
        SEQUENCE_VERSION,
        str(context.context_id),
        str(candidate.transaction_id),
        policy,
        policy.fingerprint,
        False,
        outcomes,
    )


def _outcome(
    code: str,
    *,
    matched: bool,
    count: int,
    amount: Decimal,
    cumulative_ratio: Decimal | None,
    growth_ratio: Decimal | None,
    threshold_count: int,
    threshold_cumulative_ratio: Decimal | None,
    threshold_growth_ratio: Decimal | None,
    window_hours: int,
    missing: tuple[str, ...],
    message: str,
) -> SequenceOutcome:
    status = (
        SequenceStatus.NOT_EVALUATED
        if missing
        else SequenceStatus.MATCHED
        if matched
        else SequenceStatus.NOT_MATCHED
    )
    return SequenceOutcome(
        code,
        status,
        count,
        amount,
        cumulative_ratio,
        growth_ratio,
        threshold_count,
        threshold_cumulative_ratio,
        threshold_growth_ratio,
        window_hours,
        missing,
        RiskReason(code, message) if status == SequenceStatus.MATCHED else None,
    )


def _low_value(
    window: tuple[Transaction, ...],
    median: Decimal | None,
    missing: tuple[str, ...],
    policy: SequencePolicy,
) -> SequenceOutcome:
    sequence = window[-policy.low_value_count :]
    total = sum((tx.amount for tx in sequence), Decimal())
    ratio = total / median if median else None
    matched = (
        median is not None
        and len(sequence) == policy.low_value_count
        and all(tx.amount <= median * policy.low_value_ceiling_ratio for tx in sequence)
        and ratio is not None
        and ratio >= policy.low_value_cumulative_ratio
    )
    return _outcome(
        "CUMULATIVE_LOW_VALUE_SEQUENCE",
        matched=matched,
        count=len(sequence),
        amount=total,
        cumulative_ratio=ratio,
        growth_ratio=None,
        threshold_count=policy.low_value_count,
        threshold_cumulative_ratio=policy.low_value_cumulative_ratio,
        threshold_growth_ratio=None,
        window_hours=policy.window_hours,
        missing=missing,
        message=(
            f"The latest {len(sequence)} individually baseline-sized transfers total "
            f"{ratio:.6g} times the trusted median inside {policy.window_hours} hours."
        )
        if ratio is not None
        else "",
    )


def _escalation(
    window: tuple[Transaction, ...],
    median: Decimal | None,
    missing: tuple[str, ...],
    policy: SequencePolicy,
) -> SequenceOutcome:
    sequence = window[-policy.escalation_count :]
    total = sum((tx.amount for tx in sequence), Decimal())
    ratio = total / median if median else None
    increasing = len(sequence) == policy.escalation_count and all(
        left.amount < right.amount for left, right in pairwise(sequence)
    )
    growth = sequence[-1].amount / sequence[0].amount if sequence else Decimal()
    matched = (
        median is not None
        and increasing
        and growth >= policy.escalation_growth_ratio
        and ratio is not None
        and ratio >= policy.escalation_cumulative_ratio
    )
    return _outcome(
        "GRADUAL_AMOUNT_ESCALATION",
        matched=matched,
        count=len(sequence),
        amount=total,
        cumulative_ratio=ratio,
        growth_ratio=growth,
        threshold_count=policy.escalation_count,
        threshold_cumulative_ratio=policy.escalation_cumulative_ratio,
        threshold_growth_ratio=policy.escalation_growth_ratio,
        window_hours=policy.window_hours,
        missing=missing,
        message=(
            f"The latest {len(sequence)} transfers strictly increase; last/first is "
            f"{growth:.6g} and cumulative/median is {ratio:.6g}."
        )
        if ratio is not None
        else "",
    )


def _recipient_sequence(
    window: tuple[Transaction, ...],
    median: Decimal | None,
    known_recipients: frozenset[UUID],
    missing: tuple[str, ...],
    policy: SequencePolicy,
) -> SequenceOutcome:
    candidate = window[-1]
    sequence = tuple(tx for tx in window if tx.recipient_id == candidate.recipient_id)
    total = sum((tx.amount for tx in sequence), Decimal())
    ratio = total / median if median else None
    matched = (
        median is not None
        and candidate.recipient_id not in known_recipients
        and len(sequence) >= policy.repeated_new_recipient_count
    )
    return _outcome(
        "REPEATED_NEW_RECIPIENT",
        matched=matched,
        count=len(sequence),
        amount=total,
        cumulative_ratio=ratio,
        growth_ratio=None,
        threshold_count=policy.repeated_new_recipient_count,
        threshold_cumulative_ratio=None,
        threshold_growth_ratio=None,
        window_hours=policy.window_hours,
        missing=missing,
        message=(
            f"Captured activity contains {len(sequence)} transfers to a recipient absent "
            f"from the trusted profile inside {policy.window_hours} hours."
        ),
    )


def _cumulative_exposure(
    window: tuple[Transaction, ...],
    median: Decimal | None,
    missing: tuple[str, ...],
    policy: SequencePolicy,
) -> SequenceOutcome:
    total = sum((tx.amount for tx in window), Decimal())
    ratio = total / median if median else None
    matched = (
        median is not None
        and len(window) >= policy.exposure_count
        and ratio is not None
        and ratio >= policy.exposure_cumulative_ratio
    )
    return _outcome(
        "CUMULATIVE_AMOUNT_EXPOSURE",
        matched=matched,
        count=len(window),
        amount=total,
        cumulative_ratio=ratio,
        growth_ratio=None,
        threshold_count=policy.exposure_count,
        threshold_cumulative_ratio=policy.exposure_cumulative_ratio,
        threshold_growth_ratio=None,
        window_hours=policy.window_hours,
        missing=missing,
        message=(
            f"Captured transfers total {ratio:.6g} times the trusted median inside "
            f"{policy.window_hours} hours."
        )
        if ratio is not None
        else "",
    )


def report(
    context: FeatureContext, policy: SequencePolicy = DEFAULT_SEQUENCE_POLICY
) -> dict[str, Any]:
    return asdict(evaluate_sequence(context, policy))
