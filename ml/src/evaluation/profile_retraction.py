"""Offline append-only research projection for late events and revoked feedback."""

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.profile.gate import ProfileUpdateGate
from backend.app.transaction.entities import Channel, Transaction

SOURCE_VERSION = "profile-retraction-stream-v1"
REPORT_VERSION = "profile-retraction-report-v1"
ANCHOR = datetime(2026, 11, 1, 9, tzinfo=UTC)
NAMESPACE = UUID("46ee39dd-a329-480b-a633-22ec6d59d14c")
EXPECTED_SOURCE_SHA256 = "a47cf3b27e4556da4fa71554f6057570a7135c7ad56be71b01219ee1064a74dc"


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE, f"{SOURCE_VERSION}/{name}")


@dataclass(frozen=True)
class ResearchEvent:
    transaction: Transaction
    arrival_at: datetime
    feedback_at: datetime
    revoked_at: datetime | None
    oracle_verdict: AnalystVerdict
    scenario: str


@dataclass(frozen=True)
class ProcessStep:
    step_id: UUID
    kind: str
    customer_id: UUID
    processed_at: datetime
    transaction_id: UUID | None = None
    request_id: UUID | None = None
    knowledge_cutoff: datetime | None = None


@dataclass(frozen=True)
class ResearchFixture:
    baseline: dict[UUID, tuple[ProfileObservation, ...]]
    events: tuple[ResearchEvent, ...]
    steps: tuple[ProcessStep, ...]
    source_sha256: str


def _source(fixture: ResearchFixture) -> dict[str, object]:
    return {
        "version": SOURCE_VERSION,
        "anchor": ANCHOR.isoformat(),
        "baseline": [
            {
                "customer_id": str(owner),
                "observations": [
                    {
                        "transaction_id": str(item.transaction_id),
                        "recipient_id": str(item.recipient_id),
                        "amount": str(item.amount),
                        "event_at": item.timestamp.isoformat(),
                    }
                    for item in observations
                ],
            }
            for owner, observations in sorted(
                fixture.baseline.items(), key=lambda pair: str(pair[0])
            )
        ],
        "events": [
            {
                "transaction_id": str(event.transaction.transaction_id),
                "customer_id": str(event.transaction.customer_id),
                "recipient_id": str(event.transaction.recipient_id),
                "amount": str(event.transaction.amount),
                "currency": event.transaction.currency,
                "event_at": event.transaction.timestamp.isoformat(),
                "arrival_at": event.arrival_at.isoformat(),
                "feedback_at": event.feedback_at.isoformat(),
                "revoked_at": event.revoked_at.isoformat() if event.revoked_at else None,
                "oracle_verdict": event.oracle_verdict.value,
                "scenario": event.scenario,
            }
            for event in fixture.events
        ],
        "steps": [
            {
                "step_id": str(step.step_id),
                "kind": step.kind,
                "customer_id": str(step.customer_id),
                "processed_at": step.processed_at.isoformat(),
                "transaction_id": str(step.transaction_id) if step.transaction_id else None,
                "request_id": str(step.request_id) if step.request_id else None,
                "knowledge_cutoff": step.knowledge_cutoff.isoformat()
                if step.knowledge_cutoff
                else None,
            }
            for step in fixture.steps
        ],
    }


def _sha256(document: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_fixture() -> ResearchFixture:
    """Fixed source only; no simulation result is computed here."""
    baseline: dict[UUID, tuple[ProfileObservation, ...]] = {}
    for name in ("late", "revoked"):
        owner = _id(f"customer/{name}")
        baseline[owner] = tuple(
            ProfileObservation(
                _id(f"baseline/{name}/{index}"),
                Decimal(amount),
                ANCHOR - timedelta(days=10 - index),
                _id(f"recipient/{name}/known"),
            )
            for index, amount in enumerate(("25000", "28000", "30000", "27000", "29000"))
        )

    def event(
        name: str,
        customer: str,
        amount: str,
        event_minutes: int,
        arrival_minutes: int,
        feedback_minutes: int,
        revoked_minutes: int | None = None,
    ) -> ResearchEvent:
        owner = _id(f"customer/{customer}")
        return ResearchEvent(
            Transaction(
                _id(f"event/{name}"),
                owner,
                _id(f"recipient/{customer}/known"),
                Decimal(amount),
                "KZT",
                ANCHOR + timedelta(minutes=event_minutes),
                Channel.MOBILE,
                f"synthetic-{customer}",
            ),
            ANCHOR + timedelta(minutes=arrival_minutes),
            ANCHOR + timedelta(minutes=feedback_minutes),
            ANCHOR + timedelta(minutes=revoked_minutes) if revoked_minutes else None,
            AnalystVerdict.LEGITIMATE,
            name,
        )

    events = (
        event("L1", "late", "31000", 60, 240, 250),
        event("L2", "late", "32000", 120, 121, 130),
        event("R1", "revoked", "26000", 60, 61, 70, 180),
    )

    def apply(name: str, minute: int) -> ProcessStep:
        owner_name = "revoked" if name == "R1" else "late"
        return ProcessStep(
            _id(f"step/apply/{name}"),
            "APPLY",
            _id(f"customer/{owner_name}"),
            ANCHOR + timedelta(minutes=minute),
            transaction_id=_id(f"event/{name}"),
        )

    def correct(name: str, customer: str, minute: int, cutoff: int) -> ProcessStep:
        return ProcessStep(
            _id(f"step/correct/{name}"),
            "CORRECT",
            _id(f"customer/{customer}"),
            ANCHOR + timedelta(minutes=minute),
            request_id=_id(f"correction/{customer}"),
            knowledge_cutoff=ANCHOR + timedelta(minutes=cutoff),
        )

    steps = (
        apply("R1", 80),
        apply("L2", 140),
        correct("R1", "revoked", 190, 190),
        apply("L1", 260),
        correct("L1", "late", 300, 300),
        correct("L1-duplicate", "late", 301, 300),
        correct("R1-duplicate", "revoked", 302, 190),
    )
    fixture = ResearchFixture(baseline, events, steps, "")
    return ResearchFixture(baseline, events, steps, _sha256(_source(fixture)))


def _validate(fixture: ResearchFixture) -> None:
    if fixture.source_sha256 != _sha256(_source(fixture)):
        raise ValueError("source hash mismatch")
    if len({event.transaction.transaction_id for event in fixture.events}) != len(fixture.events):
        raise ValueError("duplicate transaction")
    if len({step.step_id for step in fixture.steps}) != len(fixture.steps):
        raise ValueError("duplicate process step")
    if fixture.steps != tuple(sorted(fixture.steps, key=lambda step: step.processed_at)):
        raise ValueError("processing steps out of order")
    for event in fixture.events:
        tx = event.transaction
        if tx.customer_id not in fixture.baseline or not (
            tx.timestamp <= event.arrival_at < event.feedback_at
        ):
            raise ValueError("invalid event, arrival or feedback chronology")
        if event.revoked_at is not None and event.revoked_at <= event.feedback_at:
            raise ValueError("revocation must follow feedback")
        if any(obs.timestamp >= tx.timestamp for obs in fixture.baseline[tx.customer_id]):
            raise ValueError("baseline includes candidate or future observation")
    for step in fixture.steps:
        if step.customer_id not in fixture.baseline:
            raise ValueError("unknown customer")
        if step.kind == "APPLY":
            if step.transaction_id is None or step.request_id or step.knowledge_cutoff:
                raise ValueError("invalid apply step")
        elif step.kind == "CORRECT":
            if (
                step.request_id is None
                or step.knowledge_cutoff is None
                or step.transaction_id is not None
                or step.knowledge_cutoff > step.processed_at
            ):
                raise ValueError("invalid correction step")
        else:
            raise ValueError("unknown processing step")


def _profile(owner: UUID, observations: tuple[ProfileObservation, ...]) -> CustomerBehaviorProfile:
    return CustomerBehaviorProfile(
        owner,
        "KZT",
        ANCHOR - timedelta(days=1),
        observations,
        admission_workflow_verified=True,
        admission_policy_version="simulated-oracle-only-v1",
        learning_decision_id=_id(f"oracle/{owner}"),
    )


def _snapshot(profile: CustomerBehaviorProfile) -> dict[str, object]:
    stats = profile.long_term
    return {
        "admitted_transaction_ids": [str(obs.transaction_id) for obs in profile.observations],
        "count": len(profile.observations),
        "median": str(stats.median) if stats else None,
        "version": profile.version,
    }


def run_experiment(fixture: ResearchFixture | None = None) -> dict[str, object]:
    source = fixture or build_fixture()
    _validate(source)
    if fixture is None and source.source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("canonical source changed; version the protocol again")
    event_by_id = {event.transaction.transaction_id: event for event in source.events}
    profiles = {owner: _profile(owner, items) for owner, items in source.baseline.items()}
    views: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    current: dict[UUID, UUID] = {}
    requests: dict[UUID, tuple[UUID, datetime, UUID]] = {}
    applied: set[UUID] = set()
    gate = ProfileUpdateGate()

    for step in source.steps:
        owner = step.customer_id
        if step.kind == "APPLY":
            assert step.transaction_id is not None
            event = event_by_id.get(step.transaction_id)
            if event is None or event.transaction.customer_id != owner:
                raise ValueError("apply step customer/transaction mismatch")
            if step.transaction_id in applied:
                raise ValueError("duplicate original apply")
            if not (event.arrival_at < step.processed_at and event.feedback_at < step.processed_at):
                raise ValueError("apply cannot use unavailable facts")
            if event.revoked_at is not None and event.revoked_at < step.processed_at:
                raise ValueError("apply cannot use revoked feedback")
            applied.add(step.transaction_id)
            previous = profiles[owner]
            try:
                decision, advanced = gate.apply(event.transaction, previous, event.oracle_verdict)
                status, reason = decision.action.value, decision.reason
            except ValueError as error:
                if "historical transactions require a profile replay" not in str(error):
                    raise
                advanced = previous
                status, reason = "REQUIRES_HISTORICAL_REPLAY", str(error)
            profiles[owner] = advanced
            view_id = _id(f"view/{step.step_id}")
            views.append(
                {
                    "view_id": str(view_id),
                    "kind": "ORIGINAL",
                    "source_sha256": source.source_sha256,
                    "customer_id": str(owner),
                    "processed_at": step.processed_at.isoformat(),
                    "knowledge_cutoff": step.processed_at.isoformat(),
                    "supersedes_view_id": str(current[owner]) if owner in current else None,
                    "trigger_transaction_id": str(step.transaction_id),
                    "status": status,
                    "reason": reason,
                    "known_arrival_ids": [
                        str(item.transaction.transaction_id)
                        for item in sorted(
                            source.events,
                            key=lambda known: (
                                known.arrival_at,
                                str(known.transaction.transaction_id),
                            ),
                        )
                        if item.transaction.customer_id == owner
                        and item.arrival_at < step.processed_at
                    ],
                    "known_feedback_ids": [
                        str(item.transaction.transaction_id)
                        for item in sorted(
                            source.events,
                            key=lambda known: (
                                known.feedback_at,
                                str(known.transaction.transaction_id),
                            ),
                        )
                        if item.transaction.customer_id == owner
                        and item.feedback_at < step.processed_at
                        and (item.revoked_at is None or item.revoked_at >= step.processed_at)
                    ],
                    "profile": _snapshot(advanced),
                }
            )
            current[owner] = view_id
            continue

        assert step.kind == "CORRECT" and step.request_id and step.knowledge_cutoff
        prior_request = requests.get(step.request_id)
        if prior_request is not None:
            if prior_request[:2] != (owner, step.knowledge_cutoff):
                raise ValueError("correction request ID reused with changed scope or cutoff")
            attempts.append(
                {
                    "step_id": str(step.step_id),
                    "request_id": str(step.request_id),
                    "processed_at": step.processed_at.isoformat(),
                    "status": "REPLAYED",
                    "view_id": str(prior_request[2]),
                }
            )
            continue

        cutoff = step.knowledge_cutoff
        replay = _profile(owner, source.baseline[owner])
        eligible: list[ResearchEvent] = []
        excluded: list[dict[str, str]] = []
        for event in source.events:
            if event.transaction.customer_id != owner:
                continue
            tx_id = str(event.transaction.transaction_id)
            if event.arrival_at >= cutoff:
                reason = "ARRIVAL_UNAVAILABLE"
            elif event.feedback_at >= cutoff:
                reason = "FEEDBACK_UNAVAILABLE"
            elif event.revoked_at is not None and event.revoked_at < cutoff:
                reason = "CONFIRMATION_REVOKED"
            else:
                eligible.append(event)
                continue
            excluded.append({"transaction_id": tx_id, "reason": reason})
        actions: list[dict[str, str]] = []
        for event in sorted(
            eligible, key=lambda e: (e.transaction.timestamp, str(e.transaction.transaction_id))
        ):
            decision, replay = gate.apply(event.transaction, replay, event.oracle_verdict)
            actions.append(
                {
                    "transaction_id": str(event.transaction.transaction_id),
                    "action": decision.action.value,
                    "reason": decision.reason,
                }
            )
        view_id = _id(f"view/{step.request_id}/{owner}/{cutoff.isoformat()}")
        views.append(
            {
                "view_id": str(view_id),
                "kind": "CORRECTED_OFFLINE",
                "source_sha256": source.source_sha256,
                "customer_id": str(owner),
                "request_id": str(step.request_id),
                "processed_at": step.processed_at.isoformat(),
                "knowledge_cutoff": cutoff.isoformat(),
                "supersedes_view_id": str(current[owner]) if owner in current else None,
                "eligible_event_ids": [str(e.transaction.transaction_id) for e in eligible],
                "excluded_events": excluded,
                "replay_actions": actions,
                "profile": _snapshot(replay),
            }
        )
        requests[step.request_id] = (owner, cutoff, view_id)
        current[owner] = view_id
        attempts.append(
            {
                "step_id": str(step.step_id),
                "request_id": str(step.request_id),
                "processed_at": step.processed_at.isoformat(),
                "status": "CREATED",
                "view_id": str(view_id),
            }
        )

    return {
        "report_version": REPORT_VERSION,
        "source_version": SOURCE_VERSION,
        "source_sha256": source.source_sha256,
        "synthetic_only": True,
        "labels_verified": False,
        "production_eligible": False,
        "views": views,
        "correction_attempts": attempts,
        "current_view_ids": {str(owner): str(view_id) for owner, view_id in current.items()},
        "limitations": [
            "Only authored event, arrival, feedback, revocation and processing clocks are known.",
            "Revoked confirmation means unknown legitimacy, not confirmed fraud.",
            "Offline corrected projections do not rewrite or repair live profile history.",
            "No verified identity, external proof, authorization or bank-action reversal exists.",
            "Unobserved events and actual historical availability cannot be reconstructed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline append-only profile correction fixture")
    parser.add_argument("--output", type=Path, help="new JSON file; never overwrite")
    args = parser.parse_args()
    document = json.dumps(run_experiment(), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(document, end="")
    else:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(document)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "sha256": hashlib.sha256(document.encode()).hexdigest(),
                }
            )
        )


if __name__ == "__main__":
    main()
