"""Versioned JSON encoding for immutable profile snapshots; amounts remain decimal strings."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation


def encode_profile(profile: CustomerBehaviorProfile) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "customer_id": str(profile.customer_id),
        "currency": profile.currency,
        "as_of": profile.as_of.isoformat(),
        "version": profile.version,
        "timezone": profile.timezone,
        "long_window_days": profile.long_window_days,
        "short_window_days": profile.short_window_days,
        "observations": [
            {
                "transaction_id": str(o.transaction_id),
                "amount": str(o.amount),
                "timestamp": o.timestamp.isoformat(),
                "recipient_id": str(o.recipient_id),
            }
            for o in profile.observations
        ],
    }


def decode_profile(value: dict[str, Any]) -> CustomerBehaviorProfile:
    if value["schema_version"] != 1:
        raise ValueError("unsupported stored profile schema")
    return CustomerBehaviorProfile(
        customer_id=UUID(value["customer_id"]),
        currency=value["currency"],
        as_of=datetime.fromisoformat(value["as_of"]),
        version=value["version"],
        timezone=value["timezone"],
        long_window_days=value["long_window_days"],
        short_window_days=value["short_window_days"],
        observations=tuple(
            ProfileObservation(
                UUID(o["transaction_id"]),
                Decimal(o["amount"]),
                datetime.fromisoformat(o["timestamp"]),
                UUID(o["recipient_id"]),
            )
            for o in value["observations"]
        ),
    )
