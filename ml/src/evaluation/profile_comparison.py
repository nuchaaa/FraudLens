"""Offline comparison of four amount-profile strategies on one authored stream.

This module has no database, trained-model or analyst-identity dependency.
"""

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import (
    CustomerBehaviorProfile,
    ProfileObservation,
    amount_statistics,
)
from backend.app.profile.gate import ProfileUpdateGate
from backend.app.transaction.entities import Channel, Transaction

STREAM_VERSION = "profile-comparison-stream-v1"
REPORT_VERSION = "profile-comparison-report-v1"
ANCHOR = datetime(2026, 10, 1, 9, tzinfo=UTC)
NAMESPACE = UUID("079cb4df-7dc2-444c-b119-167db0cf1295")
STRATEGIES = ("mean_static", "median_mad_static", "naive_adaptive", "gated_adaptive")
BASE_AMOUNTS = ("22000", "31000", "28000", "35000", "26000", "33000", "29000")


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE, f"{STREAM_VERSION}/{name}")


@dataclass(frozen=True)
class StreamEvent:
    transaction: Transaction
    scenario: str
    authored_outcome: str
    arrival_at: datetime
    feedback_at: datetime | None
    oracle_verdict: AnalystVerdict | None


@dataclass(frozen=True)
class FrozenStream:
    baseline: dict[UUID, tuple[ProfileObservation, ...]]
    events: tuple[StreamEvent, ...]
    source_sha256: str


def _stream_source(
    baseline: dict[UUID, tuple[ProfileObservation, ...]], events: tuple[StreamEvent, ...]
) -> dict[str, object]:
    return {
        "version": STREAM_VERSION,
        "anchor": ANCHOR.isoformat(),
        "baseline": [
            {
                "customer_id": str(owner),
                "observations": [
                    {
                        "transaction_id": str(item.transaction_id),
                        "amount": str(item.amount),
                        "timestamp": item.timestamp.isoformat(),
                        "recipient_id": str(item.recipient_id),
                    }
                    for item in observations
                ],
            }
            for owner, observations in sorted(baseline.items(), key=lambda pair: str(pair[0]))
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
                "feedback_at": event.feedback_at.isoformat() if event.feedback_at else None,
                "oracle_verdict": event.oracle_verdict.value if event.oracle_verdict else None,
                "scenario": event.scenario,
                "authored_outcome": event.authored_outcome,
            }
            for event in events
        ],
    }


def _hash_source(document: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_stream() -> FrozenStream:
    """Freeze source facts and availability clocks before calculating results."""
    baseline: dict[UUID, tuple[ProfileObservation, ...]] = {}
    for name in ("A", "BC", "D", "E"):
        owner = _id(f"customer/{name}")
        recipient = _id(f"recipient/{name}/known")
        baseline[owner] = tuple(
            ProfileObservation(
                _id(f"baseline/{name}/{index:02d}"),
                Decimal(BASE_AMOUNTS[index % len(BASE_AMOUNTS)]),
                ANCHOR - timedelta(days=40 - index),
                recipient,
            )
            for index in range(20)
        )

    events: list[StreamEvent] = []

    def add(
        scenario: str,
        customer: str,
        index: int,
        amount: int,
        event_at: datetime,
        *,
        new_recipient: bool,
        arrival_minutes: int,
        feedback_hours: int | None,
        verdict: AnalystVerdict | None,
        authored_outcome: str,
    ) -> None:
        owner = _id(f"customer/{customer}")
        recipient = _id(f"recipient/{customer}/{'new' if new_recipient else 'known'}")
        tx = Transaction(
            _id(f"candidate/{scenario}/{index:02d}"),
            owner,
            recipient,
            Decimal(amount),
            "KZT",
            event_at,
            Channel.MOBILE,
            f"research-device-{customer}",
        )
        events.append(
            StreamEvent(
                tx,
                scenario,
                authored_outcome,
                event_at + timedelta(minutes=arrival_minutes),
                event_at + timedelta(hours=feedback_hours) if feedback_hours is not None else None,
                verdict,
            )
        )

    add(
        "A",
        "A",
        0,
        25_000,
        ANCHOR,
        new_recipient=False,
        arrival_minutes=2,
        feedback_hours=1,
        verdict=AnalystVerdict.LEGITIMATE,
        authored_outcome="AUTHORED_LEGITIMATE",
    )
    add(
        "B",
        "BC",
        0,
        8_000_000,
        ANCHOR + timedelta(days=1),
        new_recipient=True,
        arrival_minutes=5,
        feedback_hours=72,
        verdict=AnalystVerdict.LEGITIMATE,
        authored_outcome="AUTHORED_LEGITIMATE",
    )
    add(
        "C",
        "BC",
        0,
        500_000,
        ANCHOR + timedelta(days=2),
        new_recipient=True,
        arrival_minutes=1,
        feedback_hours=168,
        verdict=AnalystVerdict.CONFIRMED_FRAUD,
        authored_outcome="AUTHORED_FRAUD",
    )
    for index in range(12):
        add(
            "D",
            "D",
            index,
            45_000 + 70_000 * index // 11,
            ANCHOR + timedelta(days=1 + 2 * index),
            new_recipient=False,
            arrival_minutes=3,
            feedback_hours=6,
            verdict=AnalystVerdict.LEGITIMATE,
            authored_outcome="AUTHORED_LEGITIMATE",
        )
    for index in range(6):
        add(
            "E",
            "E",
            index,
            25_000,
            ANCHOR + timedelta(days=1, minutes=10 * index),
            new_recipient=True,
            arrival_minutes=1,
            feedback_hours=None,
            verdict=None,
            authored_outcome="AUTHORED_UNVERIFIED",
        )
    ordered = tuple(
        sorted(events, key=lambda item: (item.arrival_at, str(item.transaction.transaction_id)))
    )
    return FrozenStream(baseline, ordered, _hash_source(_stream_source(baseline, ordered)))


def _stats(observations: tuple[ProfileObservation, ...], at: datetime) -> dict[str, object]:
    # The candidate is never part of its own snapshot, even when an earlier
    # arrival supplied an observation with a later event timestamp.
    visible = tuple(item for item in observations if at - timedelta(days=180) < item.timestamp < at)
    amounts = amount_statistics(visible)
    short = amount_statistics(
        tuple(item for item in visible if at - timedelta(days=30) < item.timestamp)
    )
    return {
        "count": len(visible),
        "mean": str(amounts.mean) if amounts else None,
        "median": str(amounts.median) if amounts else None,
        "mad": str(amounts.mad) if amounts else None,
        "short_median": str(short.median) if short else None,
        "observation_ids": [str(item.transaction_id) for item in visible],
    }


def _validate_stream(stream: FrozenStream) -> None:
    if stream.source_sha256 != _hash_source(_stream_source(stream.baseline, stream.events)):
        raise ValueError("frozen stream source hash mismatch")
    if not stream.events or len({e.transaction.transaction_id for e in stream.events}) != len(
        stream.events
    ):
        raise ValueError("stream needs unique events")
    if stream.events != tuple(
        sorted(
            stream.events, key=lambda item: (item.arrival_at, str(item.transaction.transaction_id))
        )
    ):
        raise ValueError("events must be ordered by arrival")
    last_event: dict[UUID, datetime] = {}
    for event in stream.events:
        tx = event.transaction
        if tx.customer_id not in stream.baseline or tx.timestamp > event.arrival_at:
            raise ValueError("invalid customer or arrival chronology")
        if tx.customer_id in last_event and tx.timestamp <= last_event[tx.customer_id]:
            raise ValueError("out-of-order customer event needs a separate replay protocol")
        last_event[tx.customer_id] = tx.timestamp
        if (event.feedback_at is None) != (event.oracle_verdict is None):
            raise ValueError("feedback availability and verdict must be paired")
        if event.feedback_at is not None and event.feedback_at <= event.arrival_at:
            raise ValueError("feedback must become available after candidate decision")
        if any(item.timestamp >= tx.timestamp for item in stream.baseline[tx.customer_id]):
            raise ValueError("baseline cannot contain candidate or future observations")


def run_experiment(stream: FrozenStream | None = None) -> dict[str, object]:
    """Compare all strategies on the exact same frozen facts and release times."""
    source = stream or build_stream()
    _validate_stream(source)
    static = source.baseline
    naive = {owner: list(items) for owner, items in static.items()}
    gated = {
        owner: CustomerBehaviorProfile(
            owner,
            "KZT",
            ANCHOR - timedelta(days=1),
            items,
            admission_workflow_verified=True,
            admission_policy_version="simulated-oracle-only-v1",
            learning_decision_id=_id(f"oracle/{owner}"),
        )
        for owner, items in static.items()
    }
    gate = ProfileUpdateGate()
    pending: list[StreamEvent] = []
    gate_actions: list[dict[str, str]] = []
    rows: list[dict[str, object]] = []

    def release_feedback(before: datetime) -> None:
        ready = sorted(
            (e for e in pending if e.feedback_at is not None and e.feedback_at < before),
            key=lambda e: (e.feedback_at or ANCHOR, str(e.transaction.transaction_id)),
        )
        for event in ready:
            assert event.oracle_verdict is not None
            tx = event.transaction
            prior = gated[tx.customer_id]
            if tx.timestamp < prior.as_of:
                raise ValueError("late feedback requires an explicit historical correction")
            decision, advanced = gate.apply(tx, prior, event.oracle_verdict)
            gated[tx.customer_id] = advanced
            gate_actions.append(
                {
                    "transaction_id": str(tx.transaction_id),
                    "scenario": event.scenario,
                    "action": decision.action.value,
                    "reason": decision.reason,
                    "feedback_at": event.feedback_at.isoformat() if event.feedback_at else "",
                }
            )
            pending.remove(event)

    for event in source.events:
        release_feedback(event.arrival_at)
        tx = event.transaction
        owner = tx.customer_id
        for strategy in STRATEGIES:
            observations = (
                static[owner]
                if strategy in ("mean_static", "median_mad_static")
                else tuple(naive[owner])
                if strategy == "naive_adaptive"
                else gated[owner].observations
            )
            summary = _stats(observations, tx.timestamp)
            if any(item.transaction_id == tx.transaction_id for item in observations):
                raise ValueError("candidate entered its own profile snapshot")
            reference_key = "mean" if strategy in ("mean_static", "naive_adaptive") else "median"
            reference = summary[reference_key]
            ratio = Decimal(tx.amount) / Decimal(reference) if isinstance(reference, str) else None
            rows.append(
                {
                    "transaction_id": str(tx.transaction_id),
                    "customer_id": str(owner),
                    "scenario": event.scenario,
                    "strategy": strategy,
                    "event_at": tx.timestamp.isoformat(),
                    "arrival_at": event.arrival_at.isoformat(),
                    "feedback_at": event.feedback_at.isoformat() if event.feedback_at else None,
                    "authored_outcome": event.authored_outcome,
                    "amount": str(tx.amount),
                    "pre_count": summary["count"],
                    "pre_mean": summary["mean"],
                    "pre_median": summary["median"],
                    "pre_mad": summary["mad"],
                    "pre_short_median": summary["short_median"],
                    "pre_reference": reference,
                    "amount_to_reference": str(ratio.quantize(Decimal("0.000001")))
                    if ratio
                    else None,
                    "pre_observation_ids": summary["observation_ids"],
                }
            )
        naive[owner].append(
            ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, tx.recipient_id)
        )
        if event.feedback_at is not None:
            pending.append(event)
    release_feedback(datetime.max.replace(tzinfo=UTC))
    if pending:
        raise ValueError("feedback remained unreleased")

    finish = max(e.arrival_at for e in source.events) + timedelta(days=1)
    final = {
        strategy: {
            str(owner): _stats(
                static[owner]
                if strategy in ("mean_static", "median_mad_static")
                else tuple(naive[owner])
                if strategy == "naive_adaptive"
                else gated[owner].observations,
                finish,
            )
            for owner in sorted(static, key=str)
        }
        for strategy in STRATEGIES
    }

    def first(scenario: str, strategy: str) -> dict[str, object]:
        return next(
            row for row in rows if row["scenario"] == scenario and row["strategy"] == strategy
        )

    diagnostics = {
        strategy: {
            "bc_reference_before_B": first("B", strategy)["pre_reference"],
            "bc_reference_before_C": first("C", strategy)["pre_reference"],
            "bc_C_amount_to_reference": first("C", strategy)["amount_to_reference"],
            "d_short_median_before_first": first("D", strategy)["pre_short_median"],
            "d_short_median_final": final[strategy][str(_id("customer/D"))]["short_median"],
            "e_count_before_first": first("E", strategy)["pre_count"],
            "e_count_final": final[strategy][str(_id("customer/E"))]["count"],
            "e_mean_final": final[strategy][str(_id("customer/E"))]["mean"],
        }
        for strategy in STRATEGIES
    }
    return {
        "report_version": REPORT_VERSION,
        "stream_version": STREAM_VERSION,
        "source_sha256": source.source_sha256,
        "synthetic_only": True,
        "labels_verified": False,
        "production_eligible": False,
        "calibrated": False,
        "model_artifact": None,
        "split": "none: offline mechanism comparison, no model selection",
        "strategies": list(STRATEGIES),
        "candidate_count": len(source.events),
        "gate_policy": {
            "exceptional_ratio": str(gate.policy.exceptional_ratio),
            "minimum_history": gate.policy.minimum_history,
        },
        "rows": rows,
        "gate_actions": gate_actions,
        "gate_action_counts": dict(
            sorted(Counter(item["action"] for item in gate_actions).items())
        ),
        "unverified_without_feedback": sum(e.feedback_at is None for e in source.events),
        "final_profiles": final,
        "diagnostics": diagnostics,
        "limitations": (
            "Four authored statistic/update combinations on one deterministic synthetic stream. "
            "Oracle approvals and feedback are assumptions, not analyst evidence. No predictive "
            "accuracy, calibration, field representativeness or correction workflow is established."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline four-strategy profiling comparison")
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
