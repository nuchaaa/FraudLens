"""Point-in-time preservation and explicit offline correction replay."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from ml.src.evaluation.profile_retraction import (
    ANCHOR,
    EXPECTED_SOURCE_SHA256,
    REPORT_VERSION,
    ResearchFixture,
    _sha256,
    _source,
    build_fixture,
    run_experiment,
)


def _rehash(fixture: ResearchFixture) -> ResearchFixture:
    return replace(fixture, source_sha256=_sha256(_source(fixture)))


def test_source_and_report_replay_exactly_without_tampering() -> None:
    fixture = build_fixture()
    assert fixture.source_sha256 == EXPECTED_SOURCE_SHA256
    report = run_experiment()
    assert report == run_experiment()
    assert report["report_version"] == REPORT_VERSION
    assert report["source_sha256"] == EXPECTED_SOURCE_SHA256
    assert report["synthetic_only"] is True
    assert report["labels_verified"] is report["production_eligible"] is False
    root = Path(__file__).resolve().parents[2]
    source_text = (root / "ml/experiments/phase17-profile-retraction-v1/source.json").read_text()
    report_text = (root / "ml/experiments/phase17-profile-retraction-v1/report.json").read_text()
    assert source_text == json.dumps(_source(fixture), indent=2, sort_keys=True) + "\n"
    assert report_text == json.dumps(report, indent=2, sort_keys=True) + "\n"
    with pytest.raises(ValueError, match="source hash mismatch"):
        run_experiment(replace(fixture, source_sha256="0" * 64))


def test_late_arrival_keeps_original_views_and_replays_in_event_order() -> None:
    fixture = build_fixture()
    report = cast(dict[str, Any], run_experiment(fixture))
    late_events = {
        event.scenario: event for event in fixture.events if event.scenario.startswith("L")
    }
    l1_id = str(late_events["L1"].transaction.transaction_id)
    l2_id = str(late_events["L2"].transaction.transaction_id)
    late_owner = str(late_events["L1"].transaction.customer_id)
    originals = [
        view
        for view in report["views"]
        if view["kind"] == "ORIGINAL" and view["customer_id"] == late_owner
    ]
    assert len(originals) == 2
    assert originals[0]["trigger_transaction_id"] == l2_id
    assert originals[0]["status"] == "ACCEPT"
    assert originals[0]["profile"]["count"] == 6
    assert l1_id not in originals[0]["known_arrival_ids"]
    assert originals[1]["trigger_transaction_id"] == l1_id
    assert originals[1]["status"] == "REQUIRES_HISTORICAL_REPLAY"
    assert originals[1]["profile"] == originals[0]["profile"]
    corrected = next(
        view
        for view in report["views"]
        if view["kind"] == "CORRECTED_OFFLINE" and view["customer_id"] == late_owner
    )
    assert corrected["supersedes_view_id"] == originals[1]["view_id"]
    assert [item["transaction_id"] for item in corrected["replay_actions"]] == [l1_id, l2_id]
    assert [item["action"] for item in corrected["replay_actions"]] == ["ACCEPT", "ACCEPT"]
    assert corrected["profile"]["count"] == 7
    assert corrected["profile"]["admitted_transaction_ids"][-2:] == [l1_id, l2_id]
    assert originals[0]["profile"]["count"] == originals[1]["profile"]["count"] == 6


def test_revocation_removes_confirmation_only_in_corrected_view() -> None:
    fixture = build_fixture()
    report = cast(dict[str, Any], run_experiment(fixture))
    event = next(item for item in fixture.events if item.scenario == "R1")
    tx_id = str(event.transaction.transaction_id)
    owner = str(event.transaction.customer_id)
    original = next(
        view
        for view in report["views"]
        if view["kind"] == "ORIGINAL" and view["customer_id"] == owner
    )
    corrected = next(
        view
        for view in report["views"]
        if view["kind"] == "CORRECTED_OFFLINE" and view["customer_id"] == owner
    )
    assert original["status"] == "ACCEPT"
    assert original["profile"]["count"] == 6
    assert tx_id in original["profile"]["admitted_transaction_ids"]
    assert event.revoked_at is not None
    assert original["processed_at"] < event.revoked_at.isoformat()
    assert corrected["supersedes_view_id"] == original["view_id"]
    assert corrected["excluded_events"] == [
        {"transaction_id": tx_id, "reason": "CONFIRMATION_REVOKED"}
    ]
    assert corrected["profile"]["count"] == 5
    assert tx_id not in corrected["profile"]["admitted_transaction_ids"]
    assert report["current_view_ids"][owner] == corrected["view_id"]


def test_duplicate_correction_is_idempotent_and_changed_body_conflicts() -> None:
    fixture = build_fixture()
    report = cast(dict[str, Any], run_experiment(fixture))
    assert len(report["views"]) == 5
    assert [item["status"] for item in report["correction_attempts"]] == [
        "CREATED",
        "CREATED",
        "REPLAYED",
        "REPLAYED",
    ]
    assert (
        report["correction_attempts"][1]["view_id"] == report["correction_attempts"][2]["view_id"]
    )
    changed = list(fixture.steps)
    changed[-1] = replace(changed[-1], knowledge_cutoff=ANCHOR + timedelta(minutes=191))
    with pytest.raises(ValueError, match="changed scope or cutoff"):
        run_experiment(_rehash(replace(fixture, steps=tuple(changed))))


def test_strict_availability_order_and_customer_isolation() -> None:
    fixture = build_fixture()
    r1 = next(item for item in fixture.events if item.scenario == "R1")
    beta_apply = fixture.steps[0]
    changed_events = tuple(
        replace(event, feedback_at=beta_apply.processed_at) if event == r1 else event
        for event in fixture.events
    )
    with pytest.raises(ValueError, match="unavailable facts"):
        run_experiment(_rehash(replace(fixture, events=changed_events)))

    # A revocation recorded exactly at the correction cutoff is not yet known.
    equal_cutoff = tuple(
        replace(event, revoked_at=ANCHOR + timedelta(minutes=190)) if event == r1 else event
        for event in fixture.events
    )
    equal_report = cast(
        dict[str, Any], run_experiment(_rehash(replace(fixture, events=equal_cutoff)))
    )
    equal_corrected = next(
        view
        for view in equal_report["views"]
        if view["customer_id"] == str(r1.transaction.customer_id)
        and view["kind"] == "CORRECTED_OFFLINE"
    )
    assert equal_corrected["profile"]["count"] == 6

    without_revocation = tuple(
        replace(event, revoked_at=None) if event == r1 else event for event in fixture.events
    )
    variant = cast(
        dict[str, Any], run_experiment(_rehash(replace(fixture, events=without_revocation)))
    )
    base = cast(dict[str, Any], run_experiment(fixture))
    late_owner = str(next(e for e in fixture.events if e.scenario == "L1").transaction.customer_id)
    variant_late = [v for v in variant["views"] if v["customer_id"] == late_owner]
    base_late = [v for v in base["views"] if v["customer_id"] == late_owner]
    assert len(variant_late) == len(base_late) == 3
    for changed, original in zip(variant_late, base_late, strict=True):
        assert changed["view_id"] == original["view_id"]
        assert changed["profile"] == original["profile"]
        assert changed.get("status") == original.get("status")
        assert changed["source_sha256"] != original["source_sha256"]
    revoked_owner = str(r1.transaction.customer_id)
    corrected = next(
        v
        for v in variant["views"]
        if v["customer_id"] == revoked_owner and v["kind"] == "CORRECTED_OFFLINE"
    )
    assert corrected["profile"]["count"] == 6

    unordered = _rehash(replace(fixture, steps=tuple(reversed(fixture.steps))))
    with pytest.raises(ValueError, match="processing steps out of order"):
        run_experiment(unordered)
