"""Fictional point-in-time row acceptance, not predictive validation."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ml.src.datasets.row_acceptance import PROTOCOL_SHA256, audit_source, read_source

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ml/experiments/phase17-fictional-row-acceptance-v1/source.json"
REPORT = ROOT / "ml/experiments/phase17-fictional-row-acceptance-v1/report.json"
PROTOCOL = ROOT / "docs/research/phase17-prospective-behavioral-validation-v1.md"


def _source() -> tuple[dict[str, Any], str]:
    return read_source(SOURCE)


def _audit(source: dict[str, Any]) -> dict[str, Any]:
    return audit_source(source, source_sha256="f" * 64)


def _row(report: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [item for item in report["rows"] if item["transaction_id"] == name]


def _view(report: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(item for item in report["views"] if item["view_type"] == kind)


def _excluded(view: dict[str, Any], name: str, stage: str) -> str:
    return next(
        item["code"]
        for item in view["excluded"]
        if item["transaction_id"] == name and item["stage"] == stage
    )


def test_frozen_original_and_later_corrected_views_are_distinct() -> None:
    source, digest = _source()
    report = audit_source(source, source_sha256=digest)
    assert report == audit_source(source, source_sha256=digest)
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert report["protocol_sha256"] == PROTOCOL_SHA256
    assert report["status"] == "BLOCKED"  # deliberate bad rows, not a validation pass
    assert report["behavioral_validation_eligible"] is False
    assert report["production_eligible"] is False
    assert REPORT.read_text() == json.dumps(report, indent=2, sort_keys=True) + "\n"

    original = _view(report, "ORIGINAL_DECISION")
    corrected = _view(report, "CORRECTED_LATER_KNOWLEDGE")
    assert original["raw_ids"] == ["H1", "H3", "H4"]
    assert original["trusted_ids"] == ["H1", "H4"]
    assert _excluded(original, "H2", "raw") == "LATE_ARRIVAL"
    assert _excluded(original, "H3", "trusted") == "FEEDBACK_NOT_YET_AVAILABLE"
    assert _excluded(original, "C", "raw") == "CANDIDATE_SELF"
    assert _excluded(original, "same", "raw") == "EVENT_NOT_STRICTLY_PRIOR"
    assert _excluded(original, "lower", "raw") == "LOWER_BOUNDARY_EXCLUDED"
    assert corrected["raw_ids"] == ["H1", "H2", "H3", "H4"]
    assert corrected["trusted_ids"] == ["H1", "H2", "H3"]
    assert _excluded(corrected, "H4", "trusted") == "REVOKED_BY_CUTOFF"
    assert corrected["original_view_id"] == original["view_id"]
    assert corrected["view_id"] != original["view_id"]
    assert original["trusted_ids"] == ["H1", "H4"]  # correction did not rewrite it


def test_invalid_rows_and_create_only_cli_leave_source_unchanged(tmp_path: Path) -> None:
    source_digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    source, digest = _source()
    report = audit_source(source, source_sha256=digest)
    assert len(_row(report, "dup")) == 2
    assert all(item["codes"] == ["CONFLICTING_TRANSACTION_ID"] for item in _row(report, "dup"))
    assert _row(report, "naive")[0]["codes"] == ["TIMESTAMP_NOT_UTC"]
    assert _row(report, "late-decision")[0]["codes"] == ["ARRIVAL_AFTER_DECISION"]
    assert _row(report, "B-test")[0]["codes"] == []  # held-out customer only in test

    output = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "ml.src.datasets.row_acceptance",
        "--source",
        str(SOURCE),
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    assert (
        json.loads(completed.stdout)["report_sha256"]
        == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert output.read_text() == REPORT.read_text()
    again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert again.returncode != 0
    assert output.read_text() == REPORT.read_text()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_digest


def test_identity_cohort_overlap_and_missing_lineage_block_without_guessing() -> None:
    source, _ = _source()
    overlap = copy.deepcopy(source)
    overlap["identities"].append(
        {
            "source_customer_id": "fictional-A-new",
            "canonical_customer_id": "fictional-A",
            "cohort": "held_out",
        }
    )
    report = _audit(overlap)
    assert "IDENTITY_COHORT_CONFLICT" in report["source_failures"]
    assert "IDENTITY_COHORT_CONFLICT" in _row(report, "C")[0]["codes"]
    assert report["views"][0]["code"] == "CANDIDATE_UNAVAILABLE"

    reused_alias = copy.deepcopy(source)
    reused_alias["identities"].append(
        {
            "source_customer_id": "fictional-A",
            "canonical_customer_id": "fictional-Z",
            "cohort": "held_out",
        }
    )
    reused_report = _audit(reused_alias)
    assert "IDENTITY_ALIAS_CONFLICT" in reused_report["source_failures"]
    assert "IDENTITY_COHORT_CONFLICT" in _row(reused_report, "C")[0]["codes"]

    early_holdout = copy.deepcopy(source)
    tx = next(item for item in early_holdout["transactions"] if item["transaction_id"] == "B-test")
    tx["event_at"] = "2026-01-02T08:00:00Z"
    tx["arrival_at"] = "2026-01-02T08:01:00Z"
    tx["decision_at"] = "2026-01-02T08:02:00Z"
    assert _row(_audit(early_holdout), "B-test")[0]["codes"] == ["HELDOUT_IN_FIT_PERIOD"]

    unknown = copy.deepcopy(source)
    unknown["identities"] = [
        item for item in unknown["identities"] if item["source_customer_id"] != "fictional-A"
    ]
    assert "IDENTITY_LINEAGE_UNKNOWN" in _row(_audit(unknown), "C")[0]["codes"]


def test_strict_availability_boundaries_and_provenance_unknowns() -> None:
    source, _ = _source()
    exact_feedback = copy.deepcopy(source)
    f1 = next(item for item in exact_feedback["feedback"] if item["id"] == "f1")
    a1 = next(item for item in exact_feedback["admissions"] if item["id"] == "a1")
    f1["available_at"] = "2026-01-05T12:01:00Z"
    a1["available_at"] = "2026-01-05T12:01:01Z"
    original = _view(_audit(exact_feedback), "ORIGINAL_DECISION")
    assert _excluded(original, "H1", "trusted") == "FEEDBACK_NOT_YET_AVAILABLE"

    exact_revocation = copy.deepcopy(source)
    exact_revocation["revocations"][0]["available_at"] = "2026-01-05T12:01:00Z"
    original = _view(_audit(exact_revocation), "ORIGINAL_DECISION")
    assert "H4" in original["trusted_ids"]
    later = _view(_audit(exact_revocation), "CORRECTED_LATER_KNOWLEDGE")
    assert _excluded(later, "H4", "trusted") == "REVOKED_BY_CUTOFF"

    missing_link = copy.deepcopy(source)
    a1 = next(item for item in missing_link["admissions"] if item["id"] == "a1")
    a1["feedback_id"] = "not-present"
    original = _view(_audit(missing_link), "ORIGINAL_DECISION")
    assert original["status"] == "UNKNOWN"
    assert _excluded(original, "H1", "trusted") == "ADMISSION_PROVENANCE_UNKNOWN"
    assert "H1" not in original["trusted_ids"]

    impossible_revoke = copy.deepcopy(source)
    impossible_revoke["revocations"][0]["available_at"] = "2026-01-04T11:30:00Z"
    original = _view(_audit(impossible_revoke), "ORIGINAL_DECISION")
    assert original["status"] == "UNKNOWN"
    assert _excluded(original, "H4", "trusted") == "REVOCATION_PROVENANCE_UNKNOWN"


def test_later_source_rows_do_not_rename_original_known_context() -> None:
    source, digest = _source()
    initial = _view(audit_source(source, source_sha256=digest), "ORIGINAL_DECISION")
    extended = copy.deepcopy(source)
    later = copy.deepcopy(
        next(row for row in source["transactions"] if row["transaction_id"] == "B-test")
    )
    later.update(
        transaction_id="A-later",
        customer_id="fictional-A",
        event_at="2026-01-09T08:00:00Z",
        arrival_at="2026-01-09T08:01:00Z",
        decision_at="2026-01-09T08:02:00Z",
    )
    extended["transactions"].append(later)
    changed_source = _view(_audit(extended), "ORIGINAL_DECISION")
    assert changed_source["raw_ids"] == initial["raw_ids"]
    assert changed_source["trusted_ids"] == initial["trusted_ids"]
    assert changed_source["view_id"] == initial["view_id"]


def test_customer_currency_and_admission_clock_isolation() -> None:
    source, _ = _source()
    held_out_view = copy.deepcopy(source)
    held_out_view["views"].append({"candidate_id": "B-test"})
    b = next(
        item
        for item in _audit(held_out_view)["views"]
        if item.get("candidate_id") == "B-test" and item.get("view_type") == "ORIGINAL_DECISION"
    )
    assert b["raw_ids"] == b["trusted_ids"] == []

    other_currency = copy.deepcopy(source)
    h1 = next(row for row in other_currency["transactions"] if row["transaction_id"] == "H1")
    h1["currency"] = "USD"
    a = _view(_audit(other_currency), "ORIGINAL_DECISION")
    assert "H1" not in a["raw_ids"]
    assert "H1" not in a["trusted_ids"]

    same_instant = copy.deepcopy(source)
    a1 = next(item for item in same_instant["admissions"] if item["id"] == "a1")
    a1["available_at"] = "2026-01-05T12:01:00Z"
    a = _view(_audit(same_instant), "ORIGINAL_DECISION")
    assert _excluded(a, "H1", "trusted") == "ADMISSION_NOT_YET_AVAILABLE"


def test_coarse_precision_bad_splits_and_corrections_fail_closed() -> None:
    source, _ = _source()
    coarse = copy.deepcopy(source)
    coarse["time_resolution_seconds"] = 3600
    report = _audit(coarse)
    assert report["source_failures"] == ["COARSE_TIME_RESOLUTION"]
    assert all(item["status"] == "BLOCKED" for item in report["rows"])
    assert report["views"][0]["code"] == "CANDIDATE_UNAVAILABLE"

    reversed_split = copy.deepcopy(source)
    reversed_split["split_plan"]["validation_end_utc"] = "2026-01-01T00:00:00Z"
    assert "SPLIT_BOUNDARY_ORDER" in _audit(reversed_split)["source_failures"]

    invalid_correction = copy.deepcopy(source)
    invalid_correction["views"][0]["corrected_at"] = "2026-01-05T12:01:00Z"
    views = _audit(invalid_correction)["views"]
    assert views[0]["view_type"] == "ORIGINAL_DECISION"
    assert views[1]["code"] == "CORRECTION_TIME_INVALID"

    wrong_protocol = copy.deepcopy(source)
    wrong_protocol["protocol_sha256"] = "0" * 64
    assert "PROTOCOL_HASH_MISMATCH" in _audit(wrong_protocol)["source_failures"]


def test_nonfictional_duplicate_key_nonfinite_and_oversize_sources_rejected(tmp_path: Path) -> None:
    source, _ = _source()
    source["synthetic_only"] = False
    with pytest.raises(ValueError, match="synthetic_only"):
        _audit(source)
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"synthetic_only":true,"synthetic_only":true}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read_source(invalid)
    invalid.write_text('{"synthetic_only":true,"value":NaN}')
    with pytest.raises(ValueError, match="invalid JSON constant"):
        read_source(invalid)
    invalid.write_bytes(b" " * 1_048_577)
    with pytest.raises(ValueError, match="exceeds 1 MiB"):
        read_source(invalid)
