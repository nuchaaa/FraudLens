from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.transaction.entities import Transaction


class ProfileUpdateAction(StrEnum):
    ACCEPT = "ACCEPT"
    ACCEPT_WITH_LOW_WEIGHT = "ACCEPT_WITH_LOW_WEIGHT"
    QUARANTINE = "QUARANTINE"
    REJECT_FROM_PROFILE = "REJECT_FROM_PROFILE"


@dataclass(frozen=True)
class GateDecision:
    action: ProfileUpdateAction
    reason: str


@dataclass(frozen=True)
class GatePolicy:
    """Conservative hypothesis, not a calibrated fraud model."""

    exceptional_ratio: Decimal = Decimal("10")
    minimum_history: int = 5

    def __post_init__(self) -> None:
        if not self.exceptional_ratio.is_finite() or self.exceptional_ratio <= 1:
            raise ValueError("exceptional ratio must be finite and exceed 1")
        if self.minimum_history < 1:
            raise ValueError("minimum history must be positive")


class ProfileUpdateGate:
    def __init__(self, policy: GatePolicy | None = None) -> None:
        self.policy = policy or GatePolicy()

    def evaluate(
        self,
        transaction: Transaction,
        profile: CustomerBehaviorProfile,
        verdict: AnalystVerdict | None,
    ) -> GateDecision:
        if (
            transaction.customer_id != profile.customer_id
            or transaction.currency != profile.currency
        ):
            raise ValueError("transaction and profile must have the same customer and currency")
        if transaction.timestamp < profile.as_of:
            raise ValueError("historical transactions require a profile replay")
        if any(o.transaction_id == transaction.transaction_id for o in profile.observations):
            raise ValueError("transaction already admitted to profile")
        if verdict == AnalystVerdict.CONFIRMED_FRAUD:
            return GateDecision(ProfileUpdateAction.REJECT_FROM_PROFILE, "CONFIRMED_FRAUD")
        if verdict != AnalystVerdict.LEGITIMATE:
            return GateDecision(ProfileUpdateAction.QUARANTINE, "UNVERIFIED")
        baseline = replace(profile, as_of=transaction.timestamp).long_term
        if baseline is None or baseline.count < self.policy.minimum_history:
            return GateDecision(ProfileUpdateAction.QUARANTINE, "INSUFFICIENT_TRUSTED_HISTORY")
        if transaction.amount / baseline.median >= self.policy.exceptional_ratio:
            return GateDecision(ProfileUpdateAction.QUARANTINE, "EXCEPTIONAL_LEGITIMATE_AMOUNT")
        return GateDecision(ProfileUpdateAction.ACCEPT, "CONFIRMED_ORDINARY_ACTIVITY")

    def apply(
        self,
        transaction: Transaction,
        profile: CustomerBehaviorProfile,
        verdict: AnalystVerdict | None,
    ) -> tuple[GateDecision, CustomerBehaviorProfile]:
        """Pure operation; trusted analyst identity and persistence belong to the use case."""
        decision = self.evaluate(transaction, profile, verdict)
        if decision.action != ProfileUpdateAction.ACCEPT:
            return decision, profile
        advanced = replace(profile, as_of=transaction.timestamp)
        observation = ProfileObservation(
            transaction.transaction_id,
            transaction.amount,
            transaction.timestamp,
            transaction.recipient_id,
        )
        return decision, replace(
            advanced,
            observations=(*advanced.window(profile.long_window_days), observation),
            version=profile.version + 1,
        )
