"""Read-only, fictional row acceptance rehearsal; never loads real behavioral data."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path
from typing import Any

SOURCE_VERSION = "fictional-row-source-v1"
REPORT_VERSION = "fictional-row-acceptance-v1"
PROTOCOL_SHA256 = "501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2"
MAX_SOURCE_BYTES = 1_048_576
WINDOW = timedelta(days=180)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def read_source(path: Path) -> tuple[dict[str, Any], str]:
    """Read only a bounded, explicitly fictional JSON document."""
    with path.open("rb") as handle:
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("fictional source exceeds 1 MiB")
    source = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_unique_keys, parse_constant=_nonfinite
    )
    if not isinstance(source, dict) or source.get("synthetic_only") is not True:
        raise ValueError("source must be a synthetic_only object")
    return source, hashlib.sha256(raw).hexdigest()


def _instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() == timedelta(0) else None


def _items(source: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = source.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be an array of objects")
    return value


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _identity_map(
    identities: list[dict[str, Any]],
) -> tuple[dict[str, tuple[str, str]], set[str], list[str]]:
    aliases: dict[str, tuple[str, str]] = {}
    canonical_cohorts: dict[str, set[str]] = {}
    failures: list[str] = []
    alias_conflicts: set[str] = set()
    for item in identities:
        alias = item.get("source_customer_id")
        canonical = item.get("canonical_customer_id")
        cohort = item.get("cohort")
        if not all(_text(value) for value in (alias, canonical)) or cohort not in (
            "development",
            "held_out",
        ):
            failures.append("IDENTITY_DECLARATION_INVALID")
            continue
        assert isinstance(alias, str) and isinstance(canonical, str)
        if alias in aliases and aliases[alias] != (canonical, cohort):
            failures.append("IDENTITY_ALIAS_CONFLICT")
            alias_conflicts.update((aliases[alias][0], canonical))
        aliases[alias] = (canonical, cohort)
        canonical_cohorts.setdefault(canonical, set()).add(cohort)
    cohort_conflicts = {name for name, cohorts in canonical_cohorts.items() if len(cohorts) > 1}
    if cohort_conflicts:
        failures.append("IDENTITY_COHORT_CONFLICT")
    conflicts = alias_conflicts | cohort_conflicts
    return aliases, conflicts, sorted(set(failures))


def _split_plan(source: dict[str, Any]) -> tuple[tuple[datetime, ...] | None, list[str]]:
    failures: list[str] = []
    if source.get("source_version") != SOURCE_VERSION:
        failures.append("SOURCE_VERSION_UNSUPPORTED")
    if source.get("protocol_sha256") != PROTOCOL_SHA256:
        failures.append("PROTOCOL_HASH_MISMATCH")
    resolution = source.get("time_resolution_seconds")
    if type(resolution) is not int or not 1 <= resolution <= 60:
        failures.append("COARSE_TIME_RESOLUTION")
    split = source.get("split_plan")
    if not isinstance(split, dict):
        return None, sorted(set([*failures, "SPLIT_PLAN_UNKNOWN"]))
    names = ("start_utc", "train_end_utc", "validation_end_utc", "test_end_utc")
    times = tuple(_instant(split.get(name)) for name in names)
    if any(value is None for value in times):
        failures.append("SPLIT_TIME_NOT_UTC")
        return None, sorted(set(failures))
    assert all(value is not None for value in times)
    valid_times = tuple(value for value in times if value is not None)
    if not all(a < b for a, b in pairwise(valid_times)):
        failures.append("SPLIT_BOUNDARY_ORDER")
    return valid_times, sorted(set(failures))


def _transaction_checks(
    rows: list[dict[str, Any]],
    aliases: dict[str, tuple[str, str]],
    conflicts: set[str],
    split: tuple[datetime, ...] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get("transaction_id")
        if isinstance(key, str):
            by_id.setdefault(key, []).append(row)
    duplicate_codes: dict[str, str] = {}
    for key, duplicates in by_id.items():
        if len(duplicates) > 1:
            duplicate_codes[key] = (
                "DUPLICATE_TRANSACTION_ID"
                if all(row == duplicates[0] for row in duplicates)
                else "CONFLICTING_TRANSACTION_ID"
            )
    results: list[dict[str, Any]] = []
    valid: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        key = row.get("transaction_id")
        codes: set[str] = set()
        if not _text(key):
            codes.add("TRANSACTION_ID_UNKNOWN")
        elif isinstance(key, str) and key in duplicate_codes:
            codes.add(duplicate_codes[key])
        alias = row.get("customer_id")
        identity = aliases.get(alias) if isinstance(alias, str) else None
        if identity is None:
            codes.add("IDENTITY_LINEAGE_UNKNOWN")
        elif identity[0] in conflicts:
            codes.add("IDENTITY_COHORT_CONFLICT")
        if not all(_text(row.get(name)) for name in ("recipient_id", "device_id", "currency")):
            codes.add("TRANSACTION_FACT_UNKNOWN")
        amount = row.get("amount")
        try:
            numeric = Decimal(amount) if isinstance(amount, str) else Decimal("NaN")
        except InvalidOperation:
            numeric = Decimal("NaN")
        if not numeric.is_finite() or numeric <= 0:
            codes.add("AMOUNT_INVALID")
        moments = {
            name: _instant(row.get(name)) for name in ("event_at", "arrival_at", "decision_at")
        }
        if any(value is None for value in moments.values()):
            codes.add("TIMESTAMP_NOT_UTC")
        else:
            event = moments["event_at"]
            arrival = moments["arrival_at"]
            decision = moments["decision_at"]
            assert event is not None and arrival is not None and decision is not None
            if event > decision:
                codes.add("EVENT_AFTER_DECISION")
            if arrival > decision:
                codes.add("ARRIVAL_AFTER_DECISION")
            if split is None or not split[0] <= decision < split[3]:
                codes.add("OUTSIDE_DECLARED_SPLIT")
            elif identity is not None:
                period = (
                    "train"
                    if decision < split[1]
                    else "validation"
                    if decision < split[2]
                    else "test"
                )
                if identity[1] == "held_out" and period != "test":
                    codes.add("HELDOUT_IN_FIT_PERIOD")
        result = {
            "source_index": index,
            "transaction_id": key if isinstance(key, str) else None,
            "status": "BLOCKED" if codes else "ACCEPTED_FOR_CONTEXT_REHEARSAL",
            "codes": sorted(codes),
        }
        results.append(result)
        if not codes and isinstance(key, str):
            valid[key] = row
    return results, valid


def _records_by_id(items: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.get("id")
        if not _text(key) or key in indexed:
            raise ValueError(f"{name} IDs must be unique and nonempty")
        assert isinstance(key, str)
        indexed[key] = item
    return indexed


def _trust_code(
    row_id: str,
    cutoff: datetime,
    feedback: dict[str, dict[str, Any]],
    admissions: dict[str, dict[str, Any]],
    revocations: dict[str, dict[str, Any]],
) -> str | None:
    matching = [item for item in admissions.values() if item.get("transaction_id") == row_id]
    if not matching:
        return "NOT_ADMITTED"
    if len(matching) != 1:
        return "ADMISSION_PROVENANCE_UNKNOWN"
    admission = matching[0]
    feedback_id = admission.get("feedback_id")
    linked = feedback.get(feedback_id) if isinstance(feedback_id, str) else None
    feedback_at = _instant(linked.get("available_at")) if linked else None
    admission_at = _instant(admission.get("available_at"))
    if (
        linked is None
        or linked.get("transaction_id") != row_id
        or linked.get("outcome") != "LEGITIMATE"
        or linked.get("oracle_assumed") is not True
        or admission.get("oracle_assumed") is not True
        or feedback_at is None
        or admission_at is None
        or admission_at <= feedback_at
    ):
        return "ADMISSION_PROVENANCE_UNKNOWN"
    if feedback_at >= cutoff:
        return "FEEDBACK_NOT_YET_AVAILABLE"
    if admission_at >= cutoff:
        return "ADMISSION_NOT_YET_AVAILABLE"
    for item in revocations.values():
        if item.get("admission_id") != admission["id"]:
            continue
        revoked_at = _instant(item.get("available_at"))
        if (
            revoked_at is None
            or item.get("oracle_assumed") is not True
            or revoked_at <= admission_at
        ):
            return "REVOCATION_PROVENANCE_UNKNOWN"
        if revoked_at < cutoff:
            return "REVOKED_BY_CUTOFF"
    return None


def _view(
    candidate_id: str,
    cutoff: datetime,
    *,
    original_id: str | None,
    valid: dict[str, dict[str, Any]],
    aliases: dict[str, tuple[str, str]],
    feedback: dict[str, dict[str, Any]],
    admissions: dict[str, dict[str, Any]],
    revocations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate = valid[candidate_id]
    event = _instant(candidate["event_at"])
    assert event is not None
    raw: list[str] = []
    trusted: list[str] = []
    excluded: list[dict[str, str]] = []
    canonical = aliases[candidate["customer_id"]][0]
    for row_id, row in sorted(valid.items()):
        if aliases[row["customer_id"]][0] != canonical or row["currency"] != candidate["currency"]:
            continue
        earlier = _instant(row["event_at"])
        arrival = _instant(row["arrival_at"])
        assert earlier is not None and arrival is not None
        code: str | None = None
        if row_id == candidate_id:
            code = "CANDIDATE_SELF"
        elif earlier == event - WINDOW:
            code = "LOWER_BOUNDARY_EXCLUDED"
        elif earlier >= event:
            code = "EVENT_NOT_STRICTLY_PRIOR"
        elif earlier < event - WINDOW:
            code = "OUTSIDE_HISTORY_WINDOW"
        elif arrival >= cutoff:
            code = "LATE_ARRIVAL"
        if code is not None:
            excluded.append({"transaction_id": row_id, "stage": "raw", "code": code})
            continue
        raw.append(row_id)
        trust_code = _trust_code(row_id, cutoff, feedback, admissions, revocations)
        if trust_code is None:
            trusted.append(row_id)
        else:
            excluded.append({"transaction_id": row_id, "stage": "trusted", "code": trust_code})
    context_identity = {
        "candidate": candidate,
        "cutoff": cutoff.isoformat(),
        "original_view_id": original_id,
        "raw_ids": raw,
        "trusted_ids": trusted,
    }
    view_id = hashlib.sha256(json.dumps(context_identity, sort_keys=True).encode()).hexdigest()
    return {
        "view_id": view_id,
        "candidate_id": candidate_id,
        "knowledge_cutoff": cutoff.isoformat(),
        "view_type": "CORRECTED_LATER_KNOWLEDGE" if original_id else "ORIGINAL_DECISION",
        "original_view_id": original_id,
        "raw_ids": raw,
        "trusted_ids": trusted,
        "excluded": excluded,
        "status": "UNKNOWN"
        if any(item["code"].endswith("PROVENANCE_UNKNOWN") for item in excluded)
        else "RECONSTRUCTED_FICTIONAL_CONTEXT",
    }


def audit_source(source: dict[str, Any], *, source_sha256: str) -> dict[str, Any]:
    """Return deterministic, non-predictive row and point-in-time view checks."""
    if source.get("synthetic_only") is not True:
        raise ValueError("only synthetic_only sources are accepted")
    rows = _items(source, "transactions")
    identities = _items(source, "identities")
    feedback = _records_by_id(_items(source, "feedback"), "feedback")
    admissions = _records_by_id(_items(source, "admissions"), "admission")
    revocations = _records_by_id(_items(source, "revocations"), "revocation")
    aliases, conflicts, identity_failures = _identity_map(identities)
    split, split_failures = _split_plan(source)
    source_failures = sorted(set([*split_failures, *identity_failures]))
    row_results, valid = _transaction_checks(rows, aliases, conflicts, split)
    if split_failures:
        for result in row_results:
            result["codes"] = sorted(set([*result["codes"], *split_failures]))
            result["status"] = "BLOCKED"
        valid = {}
    views: list[dict[str, Any]] = []
    for request in _items(source, "views"):
        candidate_id = request.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id not in valid:
            views.append(
                {"candidate_id": candidate_id, "status": "BLOCKED", "code": "CANDIDATE_UNAVAILABLE"}
            )
            continue
        decision = _instant(valid[candidate_id]["decision_at"])
        assert decision is not None
        original = _view(
            candidate_id,
            decision,
            original_id=None,
            valid=valid,
            aliases=aliases,
            feedback=feedback,
            admissions=admissions,
            revocations=revocations,
        )
        views.append(original)
        corrected_value = request.get("corrected_at")
        if corrected_value is not None:
            corrected = _instant(corrected_value)
            if corrected is None or corrected <= decision:
                views.append(
                    {
                        "candidate_id": candidate_id,
                        "status": "BLOCKED",
                        "code": "CORRECTION_TIME_INVALID",
                    }
                )
            else:
                views.append(
                    _view(
                        candidate_id,
                        corrected,
                        original_id=original["view_id"],
                        valid=valid,
                        aliases=aliases,
                        feedback=feedback,
                        admissions=admissions,
                        revocations=revocations,
                    )
                )
    return {
        "report_version": REPORT_VERSION,
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": source_sha256,
        "synthetic_only": True,
        "behavioral_validation_eligible": False,
        "production_eligible": False,
        "status": "BLOCKED"
        if source_failures
        or any(item["status"] in ("BLOCKED", "UNKNOWN") for item in row_results + views)
        else "FICTIONAL_ROWS_CHECKED",
        "source_failures": source_failures,
        "rows": row_results,
        "views": views,
        "scope": (
            "fictional row mechanics only; legal authority, source truth and reviewer identity "
            "unverified"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    source, digest = read_source(arguments.source)
    result = audit_source(source, source_sha256=digest)
    rendered = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with arguments.output.open("xb") as handle:
        handle.write(rendered)
    print(
        json.dumps(
            {"report_sha256": hashlib.sha256(rendered).hexdigest(), "status": result["status"]}
        )
    )


if __name__ == "__main__":
    main()
