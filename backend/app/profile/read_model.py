"""Descriptive views of admitted history, never a risk score or permission to learn."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.app.profile.entities import (
    AmountStatistics,
    CustomerBehaviorProfile,
    amount_statistics,
)


class ProfileQueryError(ValueError):
    """An invalid cutoff or missing explicit version for a historical query."""


class ProfileHistoryUnavailable(ValueError):
    """The selected revision cannot reconstruct the requested event-time history."""


class BaselineStatus(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    EMPTY = "EMPTY"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    SUFFICIENT_HISTORY = "SUFFICIENT_HISTORY"


@dataclass(frozen=True)
class ProfileReadPolicy:
    # Descriptive, uncalibrated defaults. Count does not establish legitimacy.
    version: str = "profile-read-v1"
    minimum_history: int = 5
    minimum_hour_count: int = 2
    minimum_hour_share: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        if self.minimum_history < 1 or self.minimum_hour_count < 1:
            raise ValueError("minimum counts must be positive")
        if not self.minimum_hour_share.is_finite() or not 0 < self.minimum_hour_share <= 1:
            raise ValueError("hour share must be in (0, 1]")


@dataclass(frozen=True)
class BehaviorWindow:
    days: int
    count: int
    amounts: AmountStatistics | None
    observations_per_day: Decimal
    local_hour_counts: tuple[int, ...]
    typical_local_hours: tuple[int, ...]
    known_recipients: tuple[UUID, ...]


def summarize_window(
    profile: CustomerBehaviorProfile,
    days: int,
    policy: ProfileReadPolicy,
) -> BehaviorWindow:
    observations = profile.window(days)
    counts = Counter(o.timestamp.astimezone(ZoneInfo(profile.timezone)).hour for o in observations)
    typical = tuple(
        hour
        for hour in range(24)
        if counts[hour] >= policy.minimum_hour_count
        and Decimal(counts[hour]) >= policy.minimum_hour_share * len(observations)
    )
    return BehaviorWindow(
        days,
        len(observations),
        amount_statistics(observations),
        Decimal(len(observations)) / days,
        tuple(counts[hour] for hour in range(24)),
        typical,
        tuple(sorted({o.recipient_id for o in observations}, key=str)),
    )


@dataclass(frozen=True)
class ProfileView:
    customer_id: UUID
    currency: str
    as_of: datetime
    version: int | None
    revision_as_of: datetime | None
    timezone: str
    status: BaselineStatus
    policy: ProfileReadPolicy
    long_term: BehaviorWindow
    short_term: BehaviorWindow
