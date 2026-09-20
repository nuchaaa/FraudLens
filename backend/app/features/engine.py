"""One pure, versioned transformation used by online preparation and offline replay."""

from collections.abc import Iterable
from dataclasses import replace
from datetime import timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from zoneinfo import ZoneInfo

from backend.app.features.context import FEATURE_VERSION, FeatureContext
from backend.app.features.contracts import FeatureVector
from backend.app.profile.read_model import ProfileReadPolicy, summarize_window

FEATURE_NAMES = (
    "amount",
    "profile_missing",
    "baseline_insufficient",
    "long_history_count",
    "short_history_count",
    "amount_vs_customer_median",
    "amount_vs_customer_mean",
    "robust_amount_deviation",
    "mad_zero",
    "mad_floor_applied",
    "amount_vs_p95",
    "short_term_vs_long_term_amount_ratio",
    "short_baseline_insufficient",
    "new_recipient",
    "unusual_hour",
    "hour_deviation",
    "typical_hours_missing",
    "transactions_last_5_min",
    "transactions_last_10_min",
    "transactions_last_hour",
    "recipient_transactions_last_hour",
    "activity_history_count",
    "activity_history_missing",
    "recipient_observed_age_days",
    "recipient_activity_missing",
    "device_changed",
    "device_change_missing",
    "device_not_seen_before",
    "days_since_last_transfer",
)


def extract_features(context: FeatureContext) -> FeatureVector:
    # Fixed precision/rounding makes results independent of ambient Decimal settings.
    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
        return _extract(context)


def _extract(context: FeatureContext) -> FeatureVector:
    tx = context.candidate
    values: dict[str, Decimal | int | bool] = dict.fromkeys(FEATURE_NAMES, 0)
    values.update(
        amount=tx.amount,
        profile_missing=context.profile is None,
        baseline_insufficient=True,
        short_baseline_insufficient=True,
        typical_hours_missing=True,
    )
    policy = ProfileReadPolicy(
        version="profile-read-v1",
        minimum_history=5,
        minimum_hour_count=2,
        minimum_hour_share=Decimal("0.10"),
    )  # Explicit policy values are part of behavior-v1, independent of future defaults.
    if context.profile is not None:
        profile = replace(
            context.profile,
            as_of=tx.timestamp,
            observations=tuple(
                o for o in context.profile.observations if o.timestamp < tx.timestamp
            ),
        )
        long_term = summarize_window(profile, profile.long_window_days, policy)
        short_term = summarize_window(profile, profile.short_window_days, policy)
        values.update(long_history_count=long_term.count, short_history_count=short_term.count)
        baseline = long_term.amounts
        if baseline is not None and baseline.count >= policy.minimum_history:
            values.update(
                baseline_insufficient=False,
                amount_vs_customer_median=tx.amount / baseline.median,
                amount_vs_customer_mean=tx.amount / baseline.mean,
                robust_amount_deviation=abs(tx.amount - baseline.median)
                / max(baseline.mad, Decimal("0.01")),
                mad_zero=baseline.mad == 0,
                mad_floor_applied=baseline.mad < Decimal("0.01"),
                amount_vs_p95=tx.amount / baseline.p95,
                new_recipient=tx.recipient_id not in long_term.known_recipients,
            )
            if short_term.amounts is not None and short_term.count >= policy.minimum_history:
                values.update(
                    short_baseline_insufficient=False,
                    short_term_vs_long_term_amount_ratio=short_term.amounts.median
                    / baseline.median,
                )
            if long_term.typical_local_hours:
                hour = tx.timestamp.astimezone(ZoneInfo(profile.timezone)).hour
                distance = min(
                    min(abs(hour - typical), 24 - abs(hour - typical))
                    for typical in long_term.typical_local_hours
                )
                values.update(
                    typical_hours_missing=False, hour_deviation=distance, unusual_hour=distance != 0
                )
    activity = context.activity
    values.update(activity_history_count=len(activity), activity_history_missing=not activity)
    for minutes, name in (
        (5, "transactions_last_5_min"),
        (10, "transactions_last_10_min"),
        (60, "transactions_last_hour"),
    ):
        lower = tx.timestamp - timedelta(minutes=minutes)
        values[name] = sum(item.timestamp > lower for item in activity)
    recipient_activity = tuple(item for item in activity if item.recipient_id == tx.recipient_id)
    values["recipient_transactions_last_hour"] = sum(
        item.timestamp > tx.timestamp - timedelta(hours=1) for item in recipient_activity
    )
    values["recipient_activity_missing"] = not recipient_activity
    if recipient_activity:
        age = tx.timestamp - recipient_activity[0].timestamp
        values["recipient_observed_age_days"] = _days(age)
    values["device_change_missing"] = True
    if activity:
        last_time = activity[-1].timestamp
        devices_at_last_time = {item.device_id for item in activity if item.timestamp == last_time}
        # Tied different devices have no defensible order. Do not choose one by UUID.
        if len(devices_at_last_time) == 1:
            values["device_changed"] = tx.device_id not in devices_at_last_time
            values["device_change_missing"] = False
        values["device_not_seen_before"] = all(item.device_id != tx.device_id for item in activity)
        values["days_since_last_transfer"] = _days(tx.timestamp - last_time)
    return FeatureVector(
        FEATURE_VERSION, FEATURE_NAMES, tuple(float(values[name]) for name in FEATURE_NAMES)
    )


def _days(delta: timedelta) -> Decimal:
    return (
        Decimal(delta.days)
        + (Decimal(delta.seconds) + Decimal(delta.microseconds) / 1_000_000) / 86_400
    )


def extract_many(contexts: Iterable[FeatureContext]) -> tuple[FeatureVector, ...]:
    """Preserve dataset row order; no second training-only feature implementation."""
    return tuple(extract_features(context) for context in contexts)
