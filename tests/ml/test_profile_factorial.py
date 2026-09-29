"""Six-cell factorial replay and predeclared availability/failure probes."""

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from ml.src.evaluation.profile_comparison import build_stream
from ml.src.evaluation.profile_factorial import (
    CELLS,
    EXPECTED_SOURCE_SHA256,
    REPORT_VERSION,
    run_cells,
    run_experiment,
    sensitivity_streams,
)


def _row(
    rows: list[dict[str, object]], scenario: str, cell: str, ordinal: int = 0
) -> dict[str, object]:
    return [row for row in rows if row["scenario"] == scenario and row["cell"] == cell][ordinal]


def test_factorial_cells_share_admissions_and_exclude_candidate() -> None:
    stream = build_stream()
    assert stream.source_sha256 == EXPECTED_SOURCE_SHA256
    result = cast(dict[str, Any], run_cells(stream))
    rows = result["rows"]
    assert len(rows) == 21 * 6
    assert result["cells"] == list(CELLS)
    for row in rows:
        assert row["transaction_id"] not in row["pre_observation_ids"]
        assert row["event_at"] <= row["arrival_at"]
    for event in stream.events:
        event_rows = [
            row for row in rows if row["transaction_id"] == str(event.transaction.transaction_id)
        ]
        assert len(event_rows) == 6
        for policy in ("static", "naive", "gated"):
            pair = [row for row in event_rows if str(row["cell"]).endswith(f"_{policy}")]
            assert pair[0]["pre_observation_ids"] == pair[1]["pre_observation_ids"]
            assert pair[0]["pre_mean"] == pair[1]["pre_mean"]
            assert pair[0]["pre_median"] == pair[1]["pre_median"]


def test_predeclared_factorial_contrasts() -> None:
    result = cast(dict[str, Any], run_cells(build_stream()))
    diagnostics = result["diagnostics"]
    assert Decimal(diagnostics["mean_naive"]["bc_reference_before_C"]) > Decimal("400000")
    assert diagnostics["median_mad_naive"]["bc_reference_before_C"] == "29000"
    assert diagnostics["mean_gated"]["bc_reference_before_C"] == "29150"
    assert diagnostics["median_mad_gated"]["bc_reference_before_C"] == "29000"
    assert diagnostics["mean_static"]["d_count_final"] == 20
    assert diagnostics["mean_gated"]["d_count_final"] == 32
    assert diagnostics["mean_gated"]["e_count_final"] == 20
    assert diagnostics["mean_naive"]["e_count_final"] == 26
    assert result["gate_action_counts"] == {
        "ACCEPT": 13,
        "QUARANTINE": 1,
        "REJECT_FROM_PROFILE": 1,
    }


def test_delayed_feedback_exact_boundary_cannot_leak_into_d2() -> None:
    source = build_stream()
    base = cast(dict[str, Any], run_cells(source))
    delayed = cast(dict[str, Any], run_cells(sensitivity_streams(source)["delayed_feedback"]))
    assert _row(base["rows"], "D", "median_mad_gated", 1)["pre_count"] == 21
    assert _row(delayed["rows"], "D", "median_mad_gated", 1)["pre_count"] == 20
    assert (
        _row(base["rows"], "D", "mean_naive", 1)["pre_count"]
        == _row(delayed["rows"], "D", "mean_naive", 1)["pre_count"]
    )
    assert delayed["gate_action_counts"] == base["gate_action_counts"]


def test_compromised_confirmations_and_disordered_arrival_are_explicit() -> None:
    source = build_stream()
    variants = sensitivity_streams(source)
    compromised = cast(dict[str, Any], run_cells(variants["compromised_confirmation"]))
    assert compromised["diagnostics"]["median_mad_gated"]["e_count_final"] == 26
    assert compromised["gate_action_counts"]["ACCEPT"] == 19
    assert all(
        event.authored_outcome == "AUTHORED_UNVERIFIED"
        for event in variants["compromised_confirmation"].events
        if event.scenario == "E"
    )
    with pytest.raises(ValueError, match="out-of-order customer event"):
        run_cells(variants["out_of_order_arrival"])
    report = cast(dict[str, Any], run_experiment())
    assert report["sensitivity"]["out_of_order_arrival"]["status"] == "UNSUPPORTED_REQUIRES_REPLAY"
    assert report["sensitivity"]["out_of_order_arrival"]["result"] is None


def test_hash_guard_and_committed_report_replay() -> None:
    source = build_stream()
    with pytest.raises(ValueError, match="source hash mismatch"):
        run_cells(replace(source, source_sha256="0" * 64))
    # The frozen v1 source cannot be silently modified to include future data.
    modified = replace(source, events=source.events[:-1])
    with pytest.raises(ValueError, match="source hash mismatch"):
        run_cells(modified)
    result = run_experiment()
    assert result == run_experiment()
    assert result["report_version"] == REPORT_VERSION
    assert result["synthetic_only"] is True
    assert result["labels_verified"] is result["calibrated"] is False
    root = Path(__file__).resolve().parents[2]
    saved = (root / "ml/experiments/phase17-profile-factorial-v1/report.json").read_text()
    assert saved == json.dumps(result, indent=2, sort_keys=True) + "\n"
