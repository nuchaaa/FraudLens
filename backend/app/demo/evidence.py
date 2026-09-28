"""Clearly fictional review context for the deterministic local demonstration."""

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from backend.app.demo.scenarios import DemoEvent, DemoPlan

VERSION = "demo-review-evidence-v1"


class SupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class EvidenceArtifact:
    kind: str
    reference: str
    summary: str


@dataclass(frozen=True)
class DemoReviewEvidence:
    transaction_id: UUID
    customer_id: UUID
    scenario: str
    sender_display_name: str
    counterparty_display_name: str
    counterparty_type: str
    payment_purpose: str
    location_display: str
    payment_reference: str
    support_status: SupportStatus
    artifacts: tuple[EvidenceArtifact, ...]

    def document(self) -> dict[str, object]:
        return {
            "version": VERSION,
            "transaction_id": str(self.transaction_id),
            "customer_id": str(self.customer_id),
            "scenario": self.scenario,
            "synthetic_only": True,
            "real_world_verified": False,
            "production_eligible": False,
            "verdict_provided": False,
            "sender_display_name": self.sender_display_name,
            "counterparty_display_name": self.counterparty_display_name,
            "counterparty_type": self.counterparty_type,
            "payment_purpose": self.payment_purpose,
            "location": {
                "display": self.location_display,
                "source": "authored fictional demo packet",
                "verified_real_world_location": False,
            },
            "payment_reference": self.payment_reference,
            "support_status": self.support_status.value,
            "artifacts": [
                {
                    "kind": artifact.kind,
                    "reference": artifact.reference,
                    "summary": artifact.summary,
                }
                for artifact in self.artifacts
            ],
            "limitations": (
                "This packet is authored role-play evidence. It is not bank data, registry "
                "verification, a fraud label, or permission to update a customer profile."
            ),
        }


@dataclass(frozen=True)
class DemoEvidencePackage:
    entries: tuple[DemoReviewEvidence, ...]

    def document(self) -> dict[str, object]:
        return {
            "version": VERSION,
            "synthetic_only": True,
            "real_world_verified": False,
            "production_eligible": False,
            "entries": [entry.document() for entry in self.entries],
            "note": (
                "Reviewers choose their own verdicts. No entry is a verified label or "
                "learning authorization."
            ),
        }

    def sha256(self) -> str:
        payload = json.dumps(self.document(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def find(self, transaction_id: UUID) -> DemoReviewEvidence | None:
        return next(
            (entry for entry in self.entries if entry.transaction_id == transaction_id), None
        )


def _supported(
    event: DemoEvent,
    *,
    sender: str,
    counterparty: str,
    kind: str,
    purpose: str,
    location: str,
    artifacts: tuple[tuple[str, str], ...],
) -> DemoReviewEvidence:
    short_id = str(event.transaction.transaction_id).split("-", 1)[0]
    return DemoReviewEvidence(
        event.transaction.transaction_id,
        event.transaction.customer_id,
        event.scenario,
        sender,
        counterparty,
        kind,
        purpose,
        location,
        f"DEMO-{event.scenario}-{short_id.upper()}",
        SupportStatus.SUPPORTED,
        tuple(
            EvidenceArtifact(artifact_kind, f"FICTIONAL-{short_id.upper()}-{index}", summary)
            for index, (artifact_kind, summary) in enumerate(artifacts, 1)
        ),
    )


def _unavailable(
    event: DemoEvent, *, sender: str, counterparty: str, purpose: str
) -> DemoReviewEvidence:
    short_id = str(event.transaction.transaction_id).split("-", 1)[0]
    return DemoReviewEvidence(
        event.transaction.transaction_id,
        event.transaction.customer_id,
        event.scenario,
        sender,
        counterparty,
        "PERSON",
        purpose,
        "Unavailable — no transaction-linked location supplied",
        f"DEMO-{event.scenario}-{short_id.upper()}",
        SupportStatus.UNAVAILABLE,
        (),
    )


def build_evidence_package(plan: DemoPlan) -> DemoEvidencePackage:
    """Attach review context without altering transaction facts or supplying verdicts."""
    entries: list[DemoReviewEvidence] = []
    for event in plan.events:
        if event.story == "unreviewed normal-looking history" or event.scenario == "A":
            owner = "Demo Customer " + ("B" if event.scenario == "BC" else event.scenario)
            entries.append(
                _supported(
                    event,
                    sender=f"{owner} (fictional)",
                    counterparty=f"Known Recipient {owner[-1]} (fictional)",
                    kind="PERSON",
                    purpose="Recurring household transfer in the fictional scenario",
                    location="Demo District, Almaty — fictional customer-declared device location",
                    artifacts=(
                        (
                            "CUSTOMER_CONFIRMATION",
                            "Authored confirmation of the recurring transfer.",
                        ),
                        (
                            "RECIPIENT_ACKNOWLEDGEMENT",
                            "Authored acknowledgement matching the amount.",
                        ),
                    ),
                )
            )
        elif event.scenario == "B":
            entries.append(
                _supported(
                    event,
                    sender="Demo Customer B (fictional)",
                    counterparty="Qadam Auto Demo LLP (fictional and unregistered)",
                    kind="MERCHANT",
                    purpose="Vehicle purchase in the fictional scenario",
                    location="Demo Showroom, Almaty — fictional location with no real address",
                    artifacts=(
                        ("PURCHASE_AGREEMENT", "Authored vehicle agreement matching the payment."),
                        ("INVOICE", "Authored invoice for KZT 8,000,000."),
                    ),
                )
            )
        elif event.scenario == "C":
            entries.append(
                _unavailable(
                    event,
                    sender="Demo Customer B (fictional)",
                    counterparty="New Recipient C (fictional, identity unverified)",
                    purpose=(
                        "Customer-entered transfer description; no supporting document supplied"
                    ),
                )
            )
        elif event.scenario == "D":
            entries.append(
                _supported(
                    event,
                    sender="Demo Customer D (fictional)",
                    counterparty="Samal Learning Demo LLP (fictional and unregistered)",
                    kind="MERCHANT",
                    purpose="Increasing course instalment in the fictional scenario",
                    location="Online service — fictional Kazakhstan demo merchant",
                    artifacts=(
                        (
                            "SERVICE_AGREEMENT",
                            "Authored agreement describing increasing instalments.",
                        ),
                        ("INVOICE", "Authored invoice matching this transaction amount."),
                    ),
                )
            )
        else:
            entries.append(
                _unavailable(
                    event,
                    sender="Demo Customer E (fictional)",
                    counterparty="New Recipient E (fictional, identity unverified)",
                    purpose="Transfer description unavailable; no supporting document supplied",
                )
            )
    return DemoEvidencePackage(tuple(entries))
