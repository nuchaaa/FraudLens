"""Synthetic fixture and read-only guide use disposable PostgreSQL evidence."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.models import (
    AuditRow,
    CustomerRow,
    EvaluationRow,
    OutboxRow,
    ProfileRow,
    TransactionRow,
)
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.demo.__main__ import apply_plan, apply_stage, check_stage, require_disposable
from backend.adapters.demo.progress import evidence_report
from backend.adapters.demo.walkthrough import render_walkthrough
from backend.app.demo.scenarios import DemoPlan, build_plan
from backend.config import Settings
from backend.main import create_app


def test_seed_replay_and_no_automatic_learning_or_evaluation(isolated_db_engine) -> None:
    db_engine = isolated_db_engine
    plan = build_plan()
    transaction_ids = [event.transaction.transaction_id for event in plan.events]
    assert apply_plan(db_engine, plan) == (62, 0)
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(CustomerRow)
                .where(CustomerRow.customer_id.in_(plan.customers))
            )
            == 4
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(TransactionRow)
                .where(TransactionRow.transaction_id.in_(transaction_ids))
            )
            == 62
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditRow)
                .where(AuditRow.entity_id.in_(transaction_ids))
            )
            == 62
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxRow)
                .where(OutboxRow.aggregate_id.in_(transaction_ids))
            )
            == 62
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProfileRow)
                .where(ProfileRow.customer_id.in_(plan.customers))
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(EvaluationRow)
                .where(EvaluationRow.transaction_id.in_(transaction_ids))
            )
            == 0
        )
    assert apply_plan(db_engine, plan) == (0, 62)
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditRow)
                .where(AuditRow.entity_id.in_(transaction_ids))
            )
            == 62
        )


def test_seeder_rejects_non_disposable_or_tcp_database(db_engine) -> None:
    unsafe_database = create_database_engine(
        db_engine.url.set(database="fraudlens").render_as_string(hide_password=False)
    )
    tcp_database = create_database_engine(
        db_engine.url.update_query_dict({"host": "127.0.0.1"}).render_as_string(hide_password=False)
    )
    try:
        with pytest.raises(ValueError, match="local Unix-socket"):
            require_disposable(unsafe_database)
        with pytest.raises(ValueError, match="local Unix-socket"):
            require_disposable(tcp_database)
    finally:
        unsafe_database.dispose()
        tcp_database.dispose()


def test_seeder_rejects_production_mode_even_with_test_database(db_engine, monkeypatch) -> None:
    monkeypatch.setenv("FRAUDLENS_ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="local Unix-socket"):
        require_disposable(db_engine)


def test_staged_fixture_waits_for_real_review_evidence(isolated_db_engine) -> None:
    plan = build_plan()
    assert check_stage(isolated_db_engine, plan, "BASELINE")["state"] == "READY"
    assert check_stage(isolated_db_engine, plan, "B") == {
        "stage": "B",
        "state": "BLOCKED",
        "reason": "stage requires matching earlier customer baseline facts",
        "read_only": True,
    }
    with pytest.raises(ValueError, match="baseline"):
        apply_stage(isolated_db_engine, plan, "B")
    assert apply_stage(isolated_db_engine, plan, "BASELINE") == (48, 0)
    assert check_stage(isolated_db_engine, plan, "BASELINE")["state"] == "REPLAYABLE"
    assert check_stage(isolated_db_engine, plan, "A")["state"] == "READY"
    assert apply_stage(isolated_db_engine, plan, "BASELINE") == (0, 48)
    assert apply_stage(isolated_db_engine, plan, "A") == (1, 0)
    assert apply_stage(isolated_db_engine, plan, "A") == (0, 1)
    for stage in ("B", "C", "D1", "E1"):
        assert check_stage(isolated_db_engine, plan, stage)["state"] == "BLOCKED"
        with pytest.raises(ValueError, match="verified prior KZT profile"):
            apply_stage(isolated_db_engine, plan, stage)
    with Session(isolated_db_engine) as session:
        assert session.scalar(select(func.count()).select_from(TransactionRow)) == 49
        assert session.scalar(select(func.count()).select_from(ProfileRow)) == 0
        assert session.scalar(select(func.count()).select_from(EvaluationRow)) == 0


def test_stage_preflight_reports_conflicting_fixture_facts(isolated_db_engine) -> None:
    plan = build_plan()
    first = plan.events[0]
    changed = replace(first, transaction=replace(first.transaction, amount=Decimal("1")))
    alternate = DemoPlan(plan.customers, (changed, *plan.events[1:]))
    assert apply_stage(isolated_db_engine, alternate, "BASELINE") == (48, 0)
    assert check_stage(isolated_db_engine, plan, "BASELINE") == {
        "stage": "BASELINE",
        "state": "CONFLICT",
        "reason": "demo stage conflicts with stored transaction facts",
        "read_only": True,
    }
    with pytest.raises(ValueError, match="conflicts"):
        apply_stage(isolated_db_engine, plan, "BASELINE")


def test_progress_reports_only_recorded_authorized_evidence(isolated_db_engine) -> None:
    db_engine = isolated_db_engine
    plan = build_plan()
    before = evidence_report(db_engine, plan)
    assert before == evidence_report(db_engine, plan)
    unseeded_guide = render_walkthrough(plan, before)
    assert "run --check-stage B; apply only if READY" in unseeded_guide
    assert "run --check-stage D1; apply only if READY" in unseeded_guide
    assert sum(apply_plan(db_engine, plan)) == 62
    seeded = evidence_report(db_engine, plan)
    assert seeded["fixture_fact_counts"] == {"MATCH": 62}
    assert all(profile["current_version"] is None for profile in seeded["profiles"])
    assert all(not event["evaluations"] for event in seeded["events"])
    guide = render_walkthrough(plan, seeded)
    assert guide.count("Recorded evaluations: none") == 14
    assert (
        "Capture an experimental evaluation with an explicit pre-decision profile version" in guide
    )
    assert "does not certify B/C baseline preservation or D adaptation" in guide
    with pytest.raises(ValueError, match="manifest"):
        render_walkthrough(plan, seeded | {"manifest_sha256": "0" * 64})

    token = "e" * 43
    principal_id = uuid4()
    credentials = json.dumps(
        [
            {
                "principal_id": str(principal_id),
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                "roles": ["admin"],
                "customer_ids": [],
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        ]
    )
    settings = Settings(
        environment="test", api_principals=credentials, experimental_enabled=True, _env_file=None
    )
    candidate = next(event for event in plan.events if event.scenario == "B")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "demo-eval-b"}
    with TestClient(
        create_app(settings, uow_factory=partial(create_unit_of_work, db_engine)),
        raise_server_exceptions=False,
    ) as client:
        result = client.post(
            "/api/v1/experimental/evaluations",
            json={
                "transaction_id": str(candidate.transaction.transaction_id),
                "profile_version": None,
                "strategy": "rules_only",
                "manifest_sha256": None,
            },
            headers=headers,
        )
        assert result.status_code == 201, result.text
        opened = client.post(
            "/api/v1/experimental/cases",
            json={"evaluation_id": result.json()["evaluation_id"]},
            headers=headers | {"Idempotency-Key": "demo-case-b"},
        )
        assert opened.status_code == 201, opened.text
        case_id = opened.json()["case_id"]
    observed = evidence_report(db_engine, plan)
    b = next(
        event
        for event in observed["events"]
        if event["transaction_id"] == str(candidate.transaction.transaction_id)
    )
    assert len(b["evaluations"]) == 1
    assert b["evaluations"][0]["captured_profile_version"] is None
    recorded_case = b["evaluations"][0]["cases"][0]
    assert recorded_case["case_id"] == case_id
    assert recorded_case["state"] == "OPEN"
    assert recorded_case["feedback"] == []
    assert recorded_case["learning"] == []
    assert b["evaluations"][0]["risk_status"] == "INSUFFICIENT_EVIDENCE"
    assert all(profile["current_version"] is None for profile in observed["profiles"])
    assert evidence_report(db_engine, plan) == observed
    reviewed_guide = render_walkthrough(plan, observed)
    assert "INSUFFICIENT_EVIDENCE (profile vNone)" in reviewed_guide
    assert "Await an authenticated analyst's independent review" in reviewed_guide
    incompatible_event = replace(
        candidate, transaction=replace(candidate.transaction, amount=Decimal("9000000"))
    )
    incompatible_plan = DemoPlan(
        plan.customers,
        tuple(incompatible_event if event is candidate else event for event in plan.events),
    )
    conflict = evidence_report(db_engine, incompatible_plan)
    mismatched = next(
        event
        for event in conflict["events"]
        if event["transaction_id"] == str(candidate.transaction.transaction_id)
    )
    assert mismatched["fixture_fact"] == "CONFLICT"
    assert mismatched["evaluations"] == []
    assert "STOP: fixture UUID has different stored facts" in render_walkthrough(
        incompatible_plan, conflict
    )
