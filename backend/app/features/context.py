"""Immutable input facts captured for one feature computation, not a fraud label."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.app.profile.entities import CustomerBehaviorProfile
from backend.app.shared.validation import utc
from backend.app.transaction.entities import Transaction

FEATURE_VERSION = "behavior-v1"
ACTIVITY_WINDOW_DAYS = 180
MAX_ACTIVITY_ROWS = 10_000


class FeatureInputError(ValueError):
    """Input facts cannot support a safe, reproducible feature computation."""


class ActivityHistoryLimit(FeatureInputError):
    """History exceeds the explicit v1 bound; never silently truncate it."""


class ContextSource(StrEnum):
    DATABASE_CAPTURE = "database_capture"
    DECLARED_OFFLINE = "declared_offline"


@dataclass(frozen=True)
class FeatureContext:
    context_id: UUID
    candidate: Transaction
    profile: CustomerBehaviorProfile | None
    customer_timezone: str
    activity: tuple[Transaction, ...]
    captured_at: datetime
    source: ContextSource
    feature_version: Literal["behavior-v1"] = "behavior-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "captured_at", utc(self.captured_at))
        ZoneInfo(self.customer_timezone)
        if self.feature_version != FEATURE_VERSION:
            raise FeatureInputError("unsupported feature version")
        if self.captured_at < self.candidate.timestamp:
            raise FeatureInputError("candidate event time is after capture time")
        if len(self.activity) > MAX_ACTIVITY_ROWS:
            raise ActivityHistoryLimit("activity history exceeds the v1 row limit")
        try:
            lower = self.candidate.timestamp - timedelta(days=ACTIVITY_WINDOW_DAYS)
        except OverflowError as exc:
            raise FeatureInputError("candidate time cannot represent the activity window") from exc
        if len({tx.transaction_id for tx in self.activity}) != len(self.activity):
            raise FeatureInputError("duplicate activity transaction")
        for tx in self.activity:
            if (
                tx.transaction_id == self.candidate.transaction_id
                or tx.customer_id != self.candidate.customer_id
                or tx.currency != self.candidate.currency
                or not lower < tx.timestamp < self.candidate.timestamp
            ):
                raise FeatureInputError(
                    "activity must be scoped, strictly prior and exclude candidate"
                )
        object.__setattr__(
            self,
            "activity",
            tuple(
                sorted(
                    self.activity,
                    key=lambda tx: (tx.timestamp, str(tx.transaction_id)),
                )
            ),
        )
        if self.profile is not None:
            if (
                self.profile.customer_id != self.candidate.customer_id
                or self.profile.currency != self.candidate.currency
                or self.profile.as_of > self.candidate.timestamp
            ):
                raise FeatureInputError(
                    "profile identity/currency or revision cutoff is incompatible"
                )
            if any(
                o.transaction_id == self.candidate.transaction_id for o in self.profile.observations
            ):
                raise FeatureInputError("candidate already admitted; use its pre-decision revision")
            # Normalize ordering as well as time, so persisted input artifacts are stable.
            object.__setattr__(
                self,
                "profile",
                replace(
                    self.profile,
                    observations=tuple(
                        sorted(
                            self.profile.observations,
                            key=lambda o: (o.timestamp, str(o.transaction_id)),
                        )
                    ),
                ),
            )
