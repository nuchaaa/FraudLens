"""Manifest-only behavioral readiness audit and explicit unknown handling."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from ml.src.datasets.readiness import (
    CAPABILITIES,
    GOVERNANCE,
    MANIFEST_VERSION,
    REPORT_VERSION,
    audit_files,
    audit_manifest,
    read_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "ml/experiments/phase17-dataset-readiness-v1/manifests"
NAMES = (
    "synthetic-complete.json",
    "synthetic-missing-chronology.json",
    "synthetic-unknown-label-time.json",
    "ulb-known.json",
)


def _manifest(name: str) -> dict[str, Any]:
    document, _ = read_manifest(FIXTURES / name)
    return document


def _check(result: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in result["checks"] if item["requirement"] == name)


def test_frozen_report_replays_and_sources_are_not_modified(tmp_path: Path) -> None:
    paths = [FIXTURES / name for name in NAMES]
    before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = audit_files(list(reversed(paths)))
    assert report == audit_files(paths)
    assert report["report_version"] == REPORT_VERSION
    assert report["manifest_version"] == MANIFEST_VERSION
    assert report["behavioral_validation_eligible"] is False
    saved = (ROOT / "ml/experiments/phase17-dataset-readiness-v1/report.json").read_text()
    assert saved == json.dumps(report, indent=2, sort_keys=True) + "\n"
    assert before == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    output = tmp_path / "new.json"
    command = [
        sys.executable,
        "-m",
        "ml.src.datasets.readiness",
        *[part for path in paths for part in ("--manifest", str(path))],
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(completed.stdout)["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert output.read_text() == saved
    again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert again.returncode != 0
    assert output.read_text() == saved


def test_missing_absent_and_unknown_clocks_have_distinct_codes() -> None:
    report = cast(dict[str, Any], audit_files([FIXTURES / name for name in NAMES]))
    audits = {item["manifest_name"]: item for item in report["audits"]}
    complete = audits["synthetic-complete.json"]
    assert complete["status"] == "READY_FOR_ROW_AUDIT"
    assert complete["failures"] == complete["unknowns"] == []
    assert complete["behavioral_validation_eligible"] is False
    missing = audits["synthetic-missing-chronology.json"]
    assert missing["status"] == "BLOCKED"
    assert _check(missing, "capability.arrival_at")["code"] == "DECLARED_ABSENT"
    assert _check(missing, "capability.decision_at")["code"] == "DECLARED_ABSENT"
    unknown = audits["synthetic-unknown-label-time.json"]
    assert unknown["status"] == "BLOCKED"
    assert _check(unknown, "capability.label_available_at")["status"] == "UNKNOWN"
    assert _check(unknown, "capability.label_available_at")["code"] == "NOT_ESTABLISHED"

    omitted = _manifest("synthetic-complete.json")
    del omitted["capabilities"]["arrival_at"]
    item = _check(
        cast(dict[str, Any], audit_manifest(omitted, manifest_sha256="0" * 64)),
        "capability.arrival_at",
    )
    assert item["status"] == "UNKNOWN"
    assert item["code"] == "DECLARATION_MISSING"


def test_ulb_audit_uses_only_existing_version_hash_and_schema_evidence() -> None:
    ulb = _manifest("ulb-known.json")
    metadata = json.loads((ROOT / "docs/research/ulb-source-metadata.json").read_text())
    source = json.loads((ROOT / "docs/research/ulb-source-manifest.json").read_text())
    assert ulb["dataset"]["id"] == metadata["dataset"]["ref"]
    assert ulb["dataset"]["version"] == metadata["dataset"]["currentVersionNumber"]
    assert ulb["dataset"]["source_sha256"] == source["files"]["creditcard.csv"]["sha256"]
    assert ulb["dataset"]["source_uri"] == source["source_url"]
    result = cast(dict[str, Any], audit_manifest(ulb, manifest_sha256="0" * 64))
    assert result["status"] == "BLOCKED"
    assert result["behavioral_validation_eligible"] is False
    assert _check(result, "governance.license")["status"] == "PASS"
    assert _check(result, "capability.amount")["status"] == "PASS"
    assert _check(result, "capability.label_value")["status"] == "PASS"
    for capability in (
        "stable_customer_id",
        "stable_recipient_id",
        "currency",
        "absolute_event_at",
    ):
        assert _check(result, f"capability.{capability}")["code"] == "DECLARED_ABSENT"
    for capability in ("arrival_at", "label_available_at", "trusted_admission_provenance"):
        assert _check(result, f"capability.{capability}")["status"] == "UNKNOWN"
    assert _check(result, "split_plan")["code"] == "DECLARED_ABSENT"


def test_evidence_hash_resolution_and_split_checks_fail_closed() -> None:
    base = _manifest("synthetic-complete.json")

    def audited(change: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], audit_manifest(change, manifest_sha256="0" * 64))

    no_evidence = copy.deepcopy(base)
    no_evidence["governance"]["research_permission"]["evidence"] = ""
    assert (
        _check(audited(no_evidence), "governance.research_permission")["code"]
        == "EVIDENCE_REFERENCE_MISSING"
    )
    no_field = copy.deepcopy(base)
    del no_field["capabilities"]["stable_customer_id"]["field"]
    assert (
        _check(audited(no_field), "capability.stable_customer_id")["code"] == "SOURCE_FIELD_MISSING"
    )
    bad_hash = copy.deepcopy(base)
    bad_hash["dataset"]["source_sha256"] = "bad"
    assert _check(audited(bad_hash), "dataset.source_sha256")["code"] == "HASH_INVALID"
    coarse = copy.deepcopy(base)
    coarse["time_resolution_seconds"] = 3600
    assert _check(audited(coarse), "time_resolution_seconds")["code"] == "COARSE_OR_INVALID"
    reversed_bounds = copy.deepcopy(base)
    reversed_bounds["split_plan"]["validation_end_utc"] = "2026-01-01T00:00:00+00:00"
    assert _check(audited(reversed_bounds), "split_plan")["code"] == "SPLIT_BOUNDARY_ORDER"
    missing_holdout = copy.deepcopy(base)
    missing_holdout["split_plan"]["customer_disjoint"] = False
    assert _check(audited(missing_holdout), "split_plan")["code"] == "HELD_OUT_CUSTOMERS_UNPROVEN"
    wrong_version = copy.deepcopy(base)
    wrong_version["manifest_version"] = "future-v9"
    assert _check(audited(wrong_version), "manifest_version")["code"] == "UNSUPPORTED_VERSION"
    assert len(CAPABILITIES) == 14 and len(GOVERNANCE) == 4


def test_duplicate_nonfinite_oversized_and_ambiguous_names_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"dataset": {}, "dataset": {}}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read_manifest(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value": NaN}')
    with pytest.raises(ValueError, match="invalid JSON constant"):
        read_manifest(nonfinite)
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * 1_048_577)
    with pytest.raises(ValueError, match="exceeds 1 MiB"):
        read_manifest(oversized)
    with pytest.raises(ValueError, match="basenames must be unique"):
        audit_files([FIXTURES / NAMES[0], FIXTURES / NAMES[0]])
