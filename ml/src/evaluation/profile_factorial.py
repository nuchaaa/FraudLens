"""Frozen six-cell offline profile comparison and predeclared sensitivity probes."""

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

from backend.app.feedback.entities import AnalystVerdict
from backend.app.profile.entities import CustomerBehaviorProfile, ProfileObservation
from backend.app.profile.gate import ProfileUpdateGate
from ml.src.evaluation.profile_comparison import (
    ANCHOR,
    FrozenStream,
    StreamEvent,
    _hash_source,
    _id,
    _stats,
    _stream_source,
    _validate_stream,
    build_stream,
)

REPORT_VERSION = "profile-factorial-report-v1"
EXPECTED_SOURCE_SHA256 = "fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e"
STATISTICS = ("mean", "median_mad")
POLICIES = ("static", "naive", "gated")
CELLS = tuple(f"{statistic}_{policy}" for policy in POLICIES for statistic in STATISTICS)


def _variant(source: FrozenStream, events: tuple[StreamEvent, ...]) -> FrozenStream:
    ordered = tuple(sorted(events, key=lambda e: (e.arrival_at, str(e.transaction.transaction_id))))
    return FrozenStream(
        source.baseline, ordered, _hash_source(_stream_source(source.baseline, ordered))
    )


def sensitivity_streams(source: FrozenStream) -> dict[str, FrozenStream]:
    """Apply only the three protocol-declared source perturbations."""
    d_events = [event for event in source.events if event.scenario == "D"]
    first_d, second_d = d_events[:2]
    b = next(event for event in source.events if event.scenario == "B")
    c = next(event for event in source.events if event.scenario == "C")
    return {
        "delayed_feedback": _variant(
            source,
            tuple(
                replace(event, feedback_at=second_d.arrival_at) if event == first_d else event
                for event in source.events
            ),
        ),
        "compromised_confirmation": _variant(
            source,
            tuple(
                replace(
                    event,
                    feedback_at=event.transaction.timestamp + timedelta(hours=2),
                    oracle_verdict=AnalystVerdict.LEGITIMATE,
                )
                if event.scenario == "E"
                else event
                for event in source.events
            ),
        ),
        "out_of_order_arrival": _variant(
            source,
            tuple(
                replace(event, arrival_at=c.arrival_at + timedelta(minutes=2))
                if event == b
                else event
                for event in source.events
            ),
        ),
    }


def run_cells(source: FrozenStream) -> dict[str, object]:
    """Hold admissions fixed within each policy while varying the statistic."""
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
    actions: list[dict[str, str]] = []
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
            actions.append(
                {
                    "transaction_id": str(tx.transaction_id),
                    "scenario": event.scenario,
                    "action": decision.action.value,
                    "reason": decision.reason,
                }
            )
            pending.remove(event)

    def observations(policy: str, owner: UUID) -> tuple[ProfileObservation, ...]:
        if policy == "static":
            return static[owner]
        if policy == "naive":
            return tuple(naive[owner])
        return gated[owner].observations

    for event in source.events:
        release_feedback(event.arrival_at)
        tx = event.transaction
        for policy in POLICIES:
            prior = observations(policy, tx.customer_id)
            if any(item.transaction_id == tx.transaction_id for item in prior):
                raise ValueError("candidate entered its own profile snapshot")
            summary = _stats(prior, tx.timestamp)
            for statistic in STATISTICS:
                reference = summary["mean" if statistic == "mean" else "median"]
                ratio = tx.amount / Decimal(reference) if isinstance(reference, str) else None
                rows.append(
                    {
                        "transaction_id": str(tx.transaction_id),
                        "customer_id": str(tx.customer_id),
                        "scenario": event.scenario,
                        "cell": f"{statistic}_{policy}",
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
                        if ratio is not None
                        else None,
                        "pre_observation_ids": summary["observation_ids"],
                    }
                )
        naive[tx.customer_id].append(
            ProfileObservation(tx.transaction_id, tx.amount, tx.timestamp, tx.recipient_id)
        )
        if event.feedback_at is not None:
            pending.append(event)

    release_feedback(datetime.max.replace(tzinfo=UTC))
    if pending:
        raise ValueError("feedback remained unreleased")
    finish = max(e.arrival_at for e in source.events) + timedelta(days=1)
    final = {
        policy: {
            str(owner): _stats(observations(policy, owner), finish)
            for owner in sorted(static, key=str)
        }
        for policy in POLICIES
    }

    def first(scenario: str, cell: str) -> dict[str, object]:
        return next(row for row in rows if row["scenario"] == scenario and row["cell"] == cell)

    diagnostics: dict[str, dict[str, object]] = {}
    for policy in POLICIES:
        for statistic in STATISTICS:
            cell = f"{statistic}_{policy}"
            ref_key = "mean" if statistic == "mean" else "median"
            d_initial = first("D", cell)
            e_initial = first("E", cell)
            d_final = final[policy][str(_id("customer/D"))]
            e_final = final[policy][str(_id("customer/E"))]
            diagnostics[cell] = {
                "bc_reference_before_B": first("B", cell)["pre_reference"],
                "bc_reference_before_C": first("C", cell)["pre_reference"],
                "bc_C_amount_to_reference": first("C", cell)["amount_to_reference"],
                "d_count_before_first": d_initial["pre_count"],
                "d_count_final": d_final["count"],
                "d_short_median_before_first": d_initial["pre_short_median"],
                "d_short_median_final": d_final["short_median"],
                "d_reference_before_first": d_initial["pre_reference"],
                "d_reference_final": d_final[ref_key],
                "e_count_before_first": e_initial["pre_count"],
                "e_count_final": e_final["count"],
                "e_reference_before_first": e_initial["pre_reference"],
                "e_reference_final": e_final[ref_key],
            }

    return {
        "source_sha256": source.source_sha256,
        "candidate_count": len(source.events),
        "cells": list(CELLS),
        "rows": rows,
        "diagnostics": diagnostics,
        "final_profiles_by_policy": final,
        "gate_actions": actions,
        "gate_action_counts": dict(sorted(Counter(a["action"] for a in actions).items())),
    }


def run_experiment() -> dict[str, object]:
    source = build_stream()
    if source.source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("base source changed; factorial protocol must be versioned again")
    base = run_cells(source)
    sensitivity: dict[str, dict[str, object]] = {}
    for name, variant in sensitivity_streams(source).items():
        if name == "out_of_order_arrival":
            try:
                run_cells(variant)
            except ValueError as error:
                if "out-of-order customer event" not in str(error):
                    raise
                sensitivity[name] = {
                    "source_sha256": variant.source_sha256,
                    "status": "UNSUPPORTED_REQUIRES_REPLAY",
                    "reason": str(error),
                    "result": None,
                }
            else:
                raise AssertionError("out-of-order arrival unexpectedly accepted")
        else:
            measured = run_cells(variant)
            measured_rows = cast(list[dict[str, object]], measured["rows"])
            sensitivity[name] = {
                "source_sha256": variant.source_sha256,
                "status": "COMPUTED_SYNTHETIC_ONLY",
                "result": {
                    "diagnostics": measured["diagnostics"],
                    "gate_actions": measured["gate_actions"],
                    "gate_action_counts": measured["gate_action_counts"],
                    "d_second_pre_count_gated": next(
                        row["pre_count"]
                        for row in measured_rows
                        if row["scenario"] == "D"
                        and row["cell"] == "median_mad_gated"
                        and row["transaction_id"] == str(_id("candidate/D/01"))
                    ),
                },
            }
    return {
        "report_version": REPORT_VERSION,
        "source_sha256": source.source_sha256,
        "synthetic_only": True,
        "labels_verified": False,
        "production_eligible": False,
        "calibrated": False,
        "model_artifact": None,
        "gate_policy": {"exceptional_ratio": "10", "minimum_history": 5},
        "base": base,
        "sensitivity": sensitivity,
        "limitations": (
            "One authored stream with assumed oracle feedback, not analyst evidence. "
            "Statistic does not change gate admissions. Compromised confirmations bypass "
            "the trust assumption for ordinary amounts. Out-of-order arrival requires "
            "explicit historical replay. No accuracy, uncertainty, calibration or field validity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline six-cell profiling factorial")
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
