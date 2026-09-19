from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.transaction.entities import Channel, Transaction


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 19, 7, 0, tzinfo=UTC)


@pytest.fixture
def customer_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def recipient_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def transaction(now: datetime, customer_id: UUID, recipient_id: UUID) -> Transaction:
    return Transaction(
        uuid4(),
        customer_id,
        recipient_id,
        Decimal("30000"),
        "KZT",
        now,
        Channel.MOBILE,
        "synthetic-device-001",
    )


@pytest.fixture
def profile(now: datetime, customer_id: UUID, recipient_id: UUID) -> CustomerBehaviorProfile:
    observations = tuple(
        ProfileObservation(uuid4(), Decimal(amount), now - timedelta(days=i + 1), recipient_id)
        for i, amount in enumerate(["20000", "25000", "30000", "35000", "50000"] * 4)
    )
    return CustomerBehaviorProfile(customer_id, "KZT", now, observations)
