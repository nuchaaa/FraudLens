"""Versioned synthetic transaction stories, without asserted risk outcomes."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from backend.app.transaction.entities import Channel, Transaction
from backend.app.transaction.service import transaction_document

VERSION = "demo-scenarios-v1"
ANCHOR = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
_NAMESPACE = UUID("ea839263-4c81-4540-8d9e-8169d520a43a")


def demo_id(label: str) -> UUID:
    return uuid5(_NAMESPACE, f"{VERSION}/{label}")


@dataclass(frozen=True)
class DemoEvent:
    scenario: str
    story: str
    transaction: Transaction


@dataclass(frozen=True)
class DemoPlan:
    customers: tuple[UUID, ...]
    events: tuple[DemoEvent, ...]

    def document(self) -> dict[str, object]:
        return {
            "version": VERSION,
            "synthetic_only": True,
            "production_eligible": False,
            "anchor": ANCHOR.isoformat(),
            "customers": [str(identifier) for identifier in self.customers],
            "events": [
                {
                    "scenario": event.scenario,
                    "story": event.story,
                    "transaction": transaction_document(event.transaction),
                }
                for event in self.events
            ],
            "note": (
                "Stories are authored examples, not verified fraud labels or measured decisions."
            ),
        }

    def sha256(self) -> str:
        payload = json.dumps(self.document(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_plan() -> DemoPlan:
    """Use stable UUIDv5, timestamps and amounts across runs and machines."""
    customers = tuple(
        demo_id(f"customer/{name}") for name in ("normal", "vehicle", "shift", "ladder")
    )
    events: list[DemoEvent] = []

    def add(
        scenario: str,
        customer: UUID,
        label: str,
        amount: str,
        timestamp: datetime,
        recipient_label: str,
        story: str,
    ) -> None:
        events.append(
            DemoEvent(
                scenario,
                story,
                Transaction(
                    demo_id(f"transaction/{label}"),
                    customer,
                    demo_id(f"recipient/{recipient_label}"),
                    Decimal(amount),
                    "KZT",
                    timestamp,
                    Channel.MOBILE,
                    f"synthetic-{scenario.lower()}-device",
                ),
            )
        )

    baseline_amounts = ("20000", "25000", "30000", "35000", "40000")
    for customer_name, customer in zip(("A", "BC", "D", "E"), customers, strict=True):
        for index in range(12):
            add(
                customer_name,
                customer,
                f"{customer_name}/baseline/{index:02d}",
                baseline_amounts[index % len(baseline_amounts)],
                ANCHOR - timedelta(days=24 - 2 * index),
                f"{customer_name}/known",
                "unreviewed normal-looking history",
            )

    add("A", customers[0], "A/current", "25000", ANCHOR, "A/known", "normal-looking transfer")
    add(
        "B",
        customers[1],
        "B/vehicle",
        "8000000",
        ANCHOR,
        "B/vehicle",
        "exceptional vehicle payment",
    )
    add(
        "C",
        customers[1],
        "C/after-vehicle",
        "500000",
        ANCHOR + timedelta(hours=1),
        "C/new",
        "authored suspicious transfer after vehicle payment",
    )
    for index, amount in enumerate(("45000", "60000", "75000", "90000", "110000"), 1):
        add(
            "D",
            customers[2],
            f"D/change/{index}",
            amount,
            ANCHOR + timedelta(days=index),
            "D/known",
            "authored gradual legitimate change, not verified by intake",
        )
    for index, amount in enumerate(("50000", "70000", "100000", "150000", "250000", "500000"), 1):
        add(
            "E",
            customers[3],
            f"E/ladder/{index}",
            amount,
            ANCHOR + timedelta(minutes=5 * index),
            "E/new",
            "authored profile-poisoning attempt, not a verified fraud label",
        )
    return DemoPlan(
        customers,
        tuple(
            sorted(
                events,
                key=lambda event: (event.transaction.timestamp, event.transaction.transaction_id),
            )
        ),
    )
