"""Point-in-time replay without using target labels to construct features."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from backend.app.features.context import ContextSource, FeatureContext
from backend.app.features.engine import extract_features
from ml.src.datasets.synthetic import START, SyntheticDataset, identity


@dataclass(frozen=True)
class PreparedRow:
    transaction_id: str
    customer_id: str
    event_at: datetime
    decision_at: datetime
    label_available_at: datetime
    label: int
    values: tuple[float, ...]
    held_out: bool


def source_json(dataset: SyntheticDataset) -> str:
    value = asdict(dataset)
    value["held_out_customers"] = sorted(str(v) for v in dataset.held_out_customers)
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def source_hash(dataset: SyntheticDataset) -> str:
    return hashlib.sha256(source_json(dataset).encode()).hexdigest()


def prepare(dataset: SyntheticDataset) -> tuple[PreparedRow, ...]:
    events = sorted(
        dataset.events, key=lambda e: (e.available_at, str(e.transaction.transaction_id))
    )
    if len({e.transaction.transaction_id for e in events}) != len(events):
        raise ValueError("duplicate source transaction")
    profiles = {(p.customer_id, p.currency): p for p in dataset.profiles}
    if len(profiles) != len(dataset.profiles):
        raise ValueError("duplicate source profile")
    rows = []
    for event in events:
        tx = event.transaction
        profile = profiles.get((tx.customer_id, tx.currency))
        # START is declared bootstrap availability for this synthetic experiment.
        if profile is not None and profile.as_of > START:
            raise ValueError("bootstrap must be available by experiment start")
        context = FeatureContext(
            identity(f"context/{tx.transaction_id}"),
            tx,
            profile,
            "UTC",
            tuple(
                prior.transaction
                for prior in events
                if prior.available_at < event.available_at
                and prior.transaction.customer_id == tx.customer_id
                and prior.transaction.currency == tx.currency
                and tx.timestamp - timedelta(days=180) < prior.transaction.timestamp < tx.timestamp
            ),
            event.available_at,
            ContextSource.DECLARED_OFFLINE,
        )
        rows.append(
            PreparedRow(
                str(tx.transaction_id),
                str(tx.customer_id),
                tx.timestamp,
                event.available_at,
                event.label_available_at,
                event.label,
                extract_features(context).values,
                tx.customer_id in dataset.held_out_customers,
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class Splits:
    train: tuple[PreparedRow, ...]
    validation: tuple[PreparedRow, ...]
    test: tuple[PreparedRow, ...]
    held_out_test: tuple[PreparedRow, ...]
    train_end: datetime
    validation_end: datetime
    test_end: datetime


def split(rows: tuple[PreparedRow, ...], *, days: int) -> Splits:
    train_end = START + timedelta(days=int(days * 0.6))
    validation_end = START + timedelta(days=int(days * 0.8))
    test_end = START + timedelta(days=days + 3)
    # Both source event and capture must belong to the partition. Labels mature before
    # model/threshold selection; late captures crossing a boundary are excluded.
    train = tuple(
        r
        for r in rows
        if not r.held_out and r.decision_at < train_end and r.label_available_at < train_end
    )
    validation = tuple(
        r
        for r in rows
        if not r.held_out
        and train_end <= r.event_at <= r.decision_at < validation_end
        and r.label_available_at < validation_end
    )
    test = tuple(
        r
        for r in rows
        if not r.held_out
        and validation_end <= r.event_at <= r.decision_at < test_end
        and r.label_available_at < test_end
    )
    held_out = tuple(
        r
        for r in rows
        if r.held_out
        and validation_end <= r.event_at <= r.decision_at < test_end
        and r.label_available_at < test_end
    )
    for name, part in (
        ("train", train),
        ("validation", validation),
        ("test", test),
        ("held_out_test", held_out),
    ):
        if {r.label for r in part} != {0, 1}:
            raise ValueError(f"{name} must contain both classes; no silent metric substitution")
    return Splits(train, validation, test, held_out, train_end, validation_end, test_end)
