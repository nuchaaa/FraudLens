"""Authored synthetic fixture, not sampled bank data or a validated fraud population."""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.transaction.entities import Channel, Transaction

GENERATOR_VERSION = "synthetic-behavior-v1"
START = datetime(2025, 1, 1, tzinfo=UTC)


def identity(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"fraudlens/{GENERATOR_VERSION}/{value}")


@dataclass(frozen=True)
class LabeledEvent:
    transaction: Transaction
    available_at: datetime
    label_available_at: datetime
    label: int

    def __post_init__(self) -> None:
        if type(self.label) is not int or self.label not in (0, 1):
            raise ValueError("label must be binary")
        for value in (self.available_at, self.label_available_at):
            if value.tzinfo is None or value < self.transaction.timestamp:
                raise ValueError("availability must be aware and no earlier than event time")
        if self.label_available_at < self.available_at:
            raise ValueError("label cannot precede event availability")


@dataclass(frozen=True)
class SyntheticDataset:
    events: tuple[LabeledEvent, ...]
    profiles: tuple[CustomerBehaviorProfile, ...]
    held_out_customers: frozenset[UUID]
    seed: int
    days: int


def generate(seed: int = 17, *, days: int = 100, customers: int = 24) -> SyntheticDataset:
    if days < 20 or customers < 8:
        raise ValueError("fixture requires at least 20 days and eight customers")
    rng = random.Random(seed)
    events: list[LabeledEvent] = []
    profiles: list[CustomerBehaviorProfile] = []
    ids = [identity(f"{seed}/customer/{i}") for i in range(customers)]
    for index, customer in enumerate(ids):
        base = rng.uniform(15_000, 90_000)
        recipient = identity(f"{seed}/{index}/known")
        warmup = tuple(
            ProfileObservation(
                identity(f"{seed}/{index}/warmup/{j}"),
                Decimal(str(round(base * rng.uniform(0.6, 1.4), 2))),
                START - timedelta(days=j + 1) + timedelta(hours=12),
                recipient,
            )
            for j in range(20)
        )
        # Authored pre-experiment normal history only; no event labels authorize updates.
        profiles.append(CustomerBehaviorProfile(customer, "KZT", START, warmup, timezone="UTC"))
        for day in range(days):
            fraud = int(rng.random() < 0.08)  # Latent simulation choice, not a rule result.
            hour = rng.randrange(24) if fraud else rng.choice([9, 10, 12, 14, 16, 18, 22])
            timestamp = START + timedelta(days=day, hours=hour, minutes=rng.randrange(60))
            multiplier = rng.lognormvariate(1.0 if fraud else 0.0, 0.9)
            if not fraud and rng.random() < 0.025:
                multiplier *= 40  # Legitimate exceptions overlap fraud amounts.
            new_recipient = rng.random() < (0.6 if fraud else 0.18)
            device = "alternate" if rng.random() < (0.55 if fraud else 0.12) else "usual"
            tx = Transaction(
                identity(f"{seed}/{index}/{day}"),
                customer,
                identity(f"{seed}/{index}/recipient/{day}") if new_recipient else recipient,
                Decimal(str(round(max(0.01, base * multiplier), 2))),
                "KZT",
                timestamp,
                Channel.MOBILE,
                f"synthetic-{index}-{device}",
            )
            events.append(
                LabeledEvent(
                    tx,
                    timestamp + timedelta(minutes=rng.choice([0, 2, 120])),
                    timestamp + timedelta(days=2),
                    fraud,
                )
            )
    return SyntheticDataset(
        tuple(sorted(events, key=lambda e: (e.available_at, str(e.transaction.transaction_id)))),
        tuple(profiles),
        frozenset(ids[-customers // 4 :]),
        seed,
        days,
    )
