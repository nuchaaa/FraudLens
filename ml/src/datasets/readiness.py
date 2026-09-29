"""Read-only manifest suitability audit; no transaction rows or models are loaded."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "behavioral-readiness-manifest-v1"
REPORT_VERSION = "behavioral-readiness-report-v1"
MAX_MANIFEST_BYTES = 1_048_576
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
GOVERNANCE = ("license", "research_permission", "privacy_handling", "retention_plan")
CAPABILITIES = (
    "stable_customer_id",
    "stable_recipient_id",
    "currency",
    "amount",
    "stable_device_id",
    "absolute_event_at",
    "arrival_at",
    "decision_at",
    "label_value",
    "label_available_at",
    "feedback_provenance",
    "revocation_available_at",
    "trusted_admission_provenance",
    "admission_available_at",
)


def _check(
    requirement: str, status: str, code: str, evidence: str | None = None
) -> dict[str, str | None]:
    return {"requirement": requirement, "status": status, "code": code, "evidence": evidence}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _declared(requirement: str, value: object, *, field_required: bool) -> dict[str, str | None]:
    if value is None:
        return _check(requirement, "UNKNOWN", "DECLARATION_MISSING")
    if not isinstance(value, dict):
        return _check(requirement, "FAIL", "DECLARATION_INVALID")
    state = value.get("state")
    evidence = value.get("evidence")
    evidence_ref = evidence if _nonempty(evidence) else None
    if state == "ABSENT":
        return _check(requirement, "FAIL", "DECLARED_ABSENT", evidence_ref)
    if state == "UNKNOWN" or state is None:
        return _check(requirement, "UNKNOWN", "NOT_ESTABLISHED", evidence_ref)
    if state != "DOCUMENTED":
        return _check(requirement, "FAIL", "DECLARATION_INVALID_STATE", evidence_ref)
    if evidence_ref is None:
        return _check(requirement, "FAIL", "EVIDENCE_REFERENCE_MISSING")
    if field_required and not _nonempty(value.get("field")):
        return _check(requirement, "FAIL", "SOURCE_FIELD_MISSING", evidence_ref)
    return _check(requirement, "PASS", "DECLARED_WITH_REFERENCE", evidence_ref)


def _utc_instant(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        instant = datetime.fromisoformat(value)
    except ValueError:
        return None
    if instant.utcoffset() != timedelta(0):
        return None
    return instant


def _split_check(value: object) -> dict[str, str | None]:
    requirement = "split_plan"
    basic = _declared(requirement, value, field_required=False)
    if basic["status"] != "PASS":
        return basic
    assert isinstance(value, dict)
    bounds = tuple(
        _utc_instant(value.get(field))
        for field in ("train_end_utc", "validation_end_utc", "test_end_utc")
    )
    if any(bound is None for bound in bounds):
        return _check(requirement, "FAIL", "SPLIT_BOUNDARY_INVALID", basic["evidence"])
    train, validation, test = bounds
    assert train is not None and validation is not None and test is not None
    if not train < validation < test:
        return _check(requirement, "FAIL", "SPLIT_BOUNDARY_ORDER", basic["evidence"])
    count = value.get("held_out_customer_count")
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 1
        or value.get("customer_disjoint") is not True
    ):
        return _check(requirement, "FAIL", "HELD_OUT_CUSTOMERS_UNPROVEN", basic["evidence"])
    return _check(requirement, "PASS", "DECLARED_SPLIT_PLAN", basic["evidence"])


def audit_manifest(manifest: object, *, manifest_sha256: str) -> dict[str, object]:
    """Evaluate declarations only; PASS never authenticates referenced evidence."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")
    checks: list[dict[str, str | None]] = []

    version = manifest.get("manifest_version")
    checks.append(
        _check(
            "manifest_version",
            "PASS" if version == MANIFEST_VERSION else "UNKNOWN" if version is None else "FAIL",
            "SUPPORTED_VERSION"
            if version == MANIFEST_VERSION
            else "MISSING"
            if version is None
            else "UNSUPPORTED_VERSION",
        )
    )
    dataset = manifest.get("dataset")
    dataset = dataset if isinstance(dataset, dict) else {}
    for field in ("id", "version", "source_uri"):
        value = dataset.get(field)
        valid = _nonempty(value) or (field == "version" and type(value) is int and value > 0)
        checks.append(
            _check(
                f"dataset.{field}",
                "PASS" if valid else "UNKNOWN" if value is None else "FAIL",
                "DECLARED" if valid else "MISSING" if value is None else "INVALID",
            )
        )
    digest = dataset.get("source_sha256")
    valid_digest = isinstance(digest, str) and SHA256_PATTERN.fullmatch(digest) is not None
    checks.append(
        _check(
            "dataset.source_sha256",
            "PASS" if valid_digest else "UNKNOWN" if digest is None else "FAIL",
            "HASH_SYNTAX_VALID"
            if valid_digest
            else "MISSING"
            if digest is None
            else "HASH_INVALID",
        )
    )
    source_type = dataset.get("source_type")
    valid_type = source_type in ("synthetic", "public", "restricted")
    checks.append(
        _check(
            "dataset.source_type",
            "PASS" if valid_type else "UNKNOWN" if source_type is None else "FAIL",
            "DECLARED" if valid_type else "MISSING" if source_type is None else "INVALID",
        )
    )

    governance = manifest.get("governance")
    governance = governance if isinstance(governance, dict) else {}
    checks.extend(
        _declared(f"governance.{name}", governance.get(name), field_required=False)
        for name in GOVERNANCE
    )
    capabilities = manifest.get("capabilities")
    capabilities = capabilities if isinstance(capabilities, dict) else {}
    checks.extend(
        _declared(f"capability.{name}", capabilities.get(name), field_required=True)
        for name in CAPABILITIES
    )

    resolution = manifest.get("time_resolution_seconds")
    valid_resolution = type(resolution) is int and 1 <= resolution <= 60
    checks.append(
        _check(
            "time_resolution_seconds",
            "PASS" if valid_resolution else "UNKNOWN" if resolution is None else "FAIL",
            "MINUTE_OR_BETTER"
            if valid_resolution
            else "MISSING"
            if resolution is None
            else "COARSE_OR_INVALID",
        )
    )
    checks.append(_split_check(manifest.get("split_plan")))
    failures = [item for item in checks if item["status"] == "FAIL"]
    unknowns = [item for item in checks if item["status"] == "UNKNOWN"]
    return {
        "manifest_sha256": manifest_sha256,
        "dataset_id": dataset.get("id") if _nonempty(dataset.get("id")) else None,
        "status": "BLOCKED" if failures or unknowns else "READY_FOR_ROW_AUDIT",
        "behavioral_validation_eligible": False,
        "production_eligible": False,
        "checks": checks,
        "failures": failures,
        "unknowns": unknowns,
        "scope": "manifest declarations only; rows, legal authority and evidence are unverified",
    }


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    """Read at most 1 MiB and reject ambiguous/nonfinite JSON."""
    with path.open("rb") as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds 1 MiB")
    document: object = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_unique_keys, parse_constant=_invalid_constant
    )
    if not isinstance(document, dict):
        raise ValueError("manifest root must be an object")
    return document, hashlib.sha256(raw).hexdigest()


def audit_files(paths: list[Path]) -> dict[str, object]:
    if not paths:
        raise ValueError("at least one manifest is required")
    ordered = sorted(paths, key=lambda path: path.name)
    if len({path.name for path in ordered}) != len(ordered):
        raise ValueError("manifest basenames must be unique")
    audits: list[dict[str, object]] = []
    for path in ordered:
        manifest, digest = read_manifest(path)
        audits.append(
            {"manifest_name": path.name, **audit_manifest(manifest, manifest_sha256=digest)}
        )
    return {
        "report_version": REPORT_VERSION,
        "manifest_version": MANIFEST_VERSION,
        "audits": audits,
        "all_ready_for_row_audit": all(item["status"] == "READY_FOR_ROW_AUDIT" for item in audits),
        "behavioral_validation_eligible": False,
        "production_eligible": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only behavioral dataset manifest audit")
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, help="new JSON report; never overwrite")
    args = parser.parse_args()
    document = json.dumps(audit_files(args.manifest), indent=2, sort_keys=True) + "\n"
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
