"""Chronological offline profile-strategy comparison and leakage guards."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from ml.src.evaluation.profile_comparison import (
    REPORT_VERSION,
    _hash_source,
    _stream_source,
    build_stream,
    run_experiment,
)


def test_same_frozen_stream_replays_without_candidate_or_future_feedback_leakage() -> None:
    stream = build_stream()
    report = run_experiment(stream)
    assert report == run_experiment(build_stream())
    assert report["report_version"] == REPORT_VERSION
    assert report["source_sha256"] == stream.source_sha256
    assert report["synthetic_only"] is True
    assert report["labels_verified"] is report["calibrated"] is False
    assert report["candidate_count"] == 21
    rows = report["rows"]
    assert len(rows) == 21 * 4
    for row in rows:
        assert row["transaction_id"] not in row["pre_observation_ids"]
        assert row["event_at"] <= row["arrival_at"]

    diagnostics = report["diagnostics"]
    assert (
        diagnostics["mean_static"]["bc_reference_before_B"]
        == diagnostics["mean_static"]["bc_reference_before_C"]
    )
    assert (
        diagnostics["naive_adaptive"]["bc_reference_before_C"]
        != diagnostics["naive_adaptive"]["bc_reference_before_B"]
    )
    assert (
        diagnostics["gated_adaptive"]["bc_reference_before_B"]
        == diagnostics["gated_adaptive"]["bc_reference_before_C"]
    )
    assert (
        diagnostics["gated_adaptive"]["d_short_median_final"]
        > diagnostics["gated_adaptive"]["d_short_median_before_first"]
    )
    assert (
        diagnostics["gated_adaptive"]["e_count_final"]
        == diagnostics["gated_adaptive"]["e_count_before_first"]
    )
    assert (
        diagnostics["naive_adaptive"]["e_count_final"]
        == diagnostics["naive_adaptive"]["e_count_before_first"] + 6
    )
    assert report["gate_action_counts"] == {
        "ACCEPT": 13,
        "QUARANTINE": 1,
        "REJECT_FROM_PROFILE": 1,
    }


def test_feedback_exactly_at_next_arrival_cannot_change_that_decision() -> None:
    stream = build_stream()
    d_events = [event for event in stream.events if event.scenario == "D"]
    first, second = d_events[:2]
    delayed = tuple(
        replace(event, feedback_at=second.arrival_at) if event == first else event
        for event in stream.events
    )
    amended = replace(
        stream,
        events=delayed,
        source_sha256=_hash_source(_stream_source(stream.baseline, delayed)),
    )
    original_rows = run_experiment(stream)["rows"]
    amended_rows = run_experiment(amended)["rows"]

    def candidate_row(rows: list[dict[str, object]], tx_id: str) -> dict[str, object]:
        return next(
            row
            for row in rows
            if row["transaction_id"] == tx_id and row["strategy"] == "gated_adaptive"
        )

    first_id = str(first.transaction.transaction_id)
    second_id = str(second.transaction.transaction_id)
    assert (
        candidate_row(original_rows, first_id)["pre_count"]
        == candidate_row(amended_rows, first_id)["pre_count"]
    )
    assert (
        candidate_row(original_rows, second_id)["pre_count"]
        == candidate_row(amended_rows, second_id)["pre_count"] + 1
    )


def test_tampered_hash_future_baseline_and_out_of_order_event_fail() -> None:
    stream = build_stream()
    with pytest.raises(ValueError, match="hash mismatch"):
        run_experiment(replace(stream, source_sha256="0" * 64))
    owner = next(iter(stream.baseline))
    contaminated = dict(stream.baseline)
    contaminated[owner] = (
        *contaminated[owner][:-1],
        replace(
            contaminated[owner][-1], timestamp=stream.events[-1].arrival_at + timedelta(days=1)
        ),
    )
    changed = replace(
        stream,
        baseline=contaminated,
        source_sha256=_hash_source(_stream_source(contaminated, stream.events)),
    )
    with pytest.raises(ValueError, match="baseline cannot"):
        run_experiment(changed)
    reversed_events = tuple(reversed(stream.events))
    changed = replace(
        stream,
        events=reversed_events,
        source_sha256=_hash_source(_stream_source(stream.baseline, reversed_events)),
    )
    with pytest.raises(ValueError, match="ordered by arrival"):
        run_experiment(changed)


def test_committed_report_replays_exactly() -> None:
    root = Path(__file__).resolve().parents[2]
    saved = (root / "ml/experiments/phase17-profile-comparison-v1/report.json").read_text()
    assert saved == json.dumps(run_experiment(), indent=2, sort_keys=True) + "\n"
