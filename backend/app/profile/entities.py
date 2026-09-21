from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.app.shared.validation import currency_code, positive_amount, utc


@dataclass(frozen=True)
class Customer:
    customer_id: UUID
    created_at: datetime
    timezone: str = "Asia/Almaty"

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", utc(self.created_at))
        ZoneInfo(self.timezone)


@dataclass(frozen=True)
class ProfileObservation:
    """A previously admitted observation; never an unreviewed transaction."""

    transaction_id: UUID
    amount: Decimal
    timestamp: datetime
    recipient_id: UUID

    def __post_init__(self) -> None:
        positive_amount(self.amount)
        object.__setattr__(self, "timestamp", utc(self.timestamp))


@dataclass(frozen=True)
class AmountStatistics:
    count: int
    median: Decimal
    mad: Decimal
    p95: Decimal
    mean: Decimal


def amount_statistics(observations: tuple[ProfileObservation, ...]) -> AmountStatistics | None:
    if not observations:
        return None
    amounts = sorted(o.amount for o in observations)
    center = Decimal(median(amounts))
    deviations = sorted(abs(value - center) for value in amounts)
    # Nearest-rank p95; avoids float conversions for financial amounts.
    rank = (95 * len(amounts) + 99) // 100
    return AmountStatistics(
        count=len(amounts),
        median=center,
        mad=Decimal(median(deviations)),
        p95=amounts[rank - 1],
        mean=sum(amounts, Decimal("0")) / len(amounts),
    )


@dataclass(frozen=True)
class CustomerBehaviorProfile:
    customer_id: UUID
    currency: str
    as_of: datetime
    observations: tuple[ProfileObservation, ...] = ()
    version: int = 1
    timezone: str = "Asia/Almaty"
    long_window_days: int = 180
    short_window_days: int = 30
    admission_workflow_verified: bool = False
    admission_policy_version: str | None = None
    learning_decision_id: UUID | None = None

    def __post_init__(self) -> None:
        currency_code(self.currency)
        object.__setattr__(self, "as_of", utc(self.as_of))
        ZoneInfo(self.timezone)
        if self.version < 1 or not 0 < self.short_window_days <= self.long_window_days:
            raise ValueError("invalid profile version or window")
        if self.admission_workflow_verified != (
            self.admission_policy_version is not None and self.learning_decision_id is not None
        ):
            raise ValueError("verified profile provenance must be complete")
        if len({o.transaction_id for o in self.observations}) != len(self.observations):
            raise ValueError("duplicate profile observation")
        if any(o.timestamp > self.as_of for o in self.observations):
            raise ValueError("profile must not contain future observations")

    def window(self, days: int) -> tuple[ProfileObservation, ...]:
        cutoff = self.as_of - timedelta(days=days)
        return tuple(o for o in self.observations if cutoff < o.timestamp <= self.as_of)

    @property
    def long_term(self) -> AmountStatistics | None:
        return amount_statistics(self.window(self.long_window_days))

    @property
    def short_term(self) -> AmountStatistics | None:
        return amount_statistics(self.window(self.short_window_days))

    @property
    def known_recipients(self) -> frozenset[UUID]:
        return frozenset(o.recipient_id for o in self.window(self.long_window_days))

    @property
    def typical_hours(self) -> frozenset[int]:
        """Legacy observed-hour set; read_model supplies frequency-qualified descriptive hours."""
        return frozenset(
            o.timestamp.astimezone(ZoneInfo(self.timezone)).hour
            for o in self.window(self.long_window_days)
        )


@dataclass(frozen=True)
class ProfileSnapshot:
    snapshot_id: UUID
    assessment_id: UUID
    profile: CustomerBehaviorProfile
