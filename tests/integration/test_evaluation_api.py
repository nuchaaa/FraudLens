import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.adapters.database.history import PostgresAuditRepository, PostgresOutboxRepository
from backend.adapters.database.idempotency import PostgresIdempotencyRepository
from backend.adapters.database.uow import PostgresUnitOfWork, create_unit_of_work
from backend.adapters.evaluation import ExperimentalEvaluationEngine
from backend.app.evaluation.service import EvaluationService
from backend.app.profile.entities import Customer
from backend.app.risk.service import Strategy
from backend.app.shared.security import Principal, Role
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres
PATH = "/api/v1/experimental"
TOKENS = {"admin": "a" * 43, "service": "b" * 43, "analyst": "c" * 43, "outsider": "d" * 43}


def headers(role="service", key="evaluate-1"):
    return {"Authorization": f"Bearer {TOKENS[role]}", "Idempotency-Key": key}


@pytest.fixture
def setup(db_engine, transaction):
    tx = replace(transaction, customer_id=uuid4(), transaction_id=uuid4())
    entries = [
        {
            "principal_id": str(uuid4()),
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "roles": [role if role != "outsider" else "analyst"],
            "customer_ids": [str(tx.customer_id)] if role != "outsider" else [],
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        for role, token in TOKENS.items()
    ]
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(tx.customer_id, tx.timestamp, "UTC"))
        uow.transactions.add(tx)
        uow.commit()
    config = Settings(
        environment="test",
        database_url=None,
        api_principals=json.dumps(entries),
        experimental_enabled=True,
        _env_file=None,
    )
    return tx, entries, config


@pytest.fixture
def api(db_engine, setup):
    tx, entries, config = setup
    with TestClient(
        create_app(config, uow_factory=partial(create_unit_of_work, db_engine)),
        raise_server_exceptions=False,
    ) as client:
        yield client, tx, entries


def request(tx):
    return {
        "transaction_id": str(tx.transaction_id),
        "profile_version": None,
        "strategy": "rules_only",
    }


def evaluate(client, tx, key="evaluate-1"):
    response = client.post(PATH + "/evaluations", json=request(tx), headers=headers(key=key))
    assert response.status_code == 201, response.text
    return response


def case(client, evaluation):
    response = client.post(
        PATH + "/cases",
        json={"evaluation_id": evaluation.json()["evaluation_id"]},
        headers=headers("analyst", "case-1"),
    )
    assert response.status_code == 201, response.text
    return response


def change(client, identifier, version, action, key, **extra):
    return client.post(
        PATH + f"/cases/{identifier}/review",
        json={"expected_version": version, "action": action, **extra},
        headers=headers("analyst", key),
    )


def test_durable_absent_provenance_replay_and_scope(api, db_engine):
    client, tx, entries = api
    first = evaluate(client, tx)
    doc = first.json()
    assert doc["risk"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert doc["risk"]["score"] is doc["risk"]["prediction"] is doc["model_manifest_json"] is None
    assert doc["risk"]["profile_version"] is None
    assert doc["explanation"]["model"] is None
    assert doc["context_artifact"]["sha256"] == doc["context_sha256"]
    assert doc["actor_id"] == entries[1]["principal_id"]
    replay = evaluate(client, tx)
    assert replay.content == first.content and replay.headers["idempotency-replayed"] == "true"
    fetched = client.get(first.headers["location"], headers=headers("analyst"))
    assert fetched.content == first.content
    assert fetched.headers["cache-control"] == "no-store"
    assert client.get(first.headers["location"], headers=headers("outsider")).status_code == 404
    assert client.get(first.headers["location"]).status_code == 401
    assert (
        client.post(PATH + "/evaluations", json=request(tx), headers=headers("analyst")).status_code
        == 403
    )
    assert (
        client.post(
            PATH + "/evaluations", json=request(tx), headers=headers("outsider")
        ).status_code
        == 404
    )
    changed = {**request(tx), "profile_version": 1}
    assert client.post(PATH + "/evaluations", json=changed, headers=headers()).status_code == 409
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM experimental_evaluations WHERE transaction_id=:id"),
                {"id": tx.transaction_id},
            ).scalar_one()
            == 1
        )
        row = connection.execute(
            text(
                """SELECT a.actor_id, a.correlation_id=o.correlation_id FROM audit_events a JOIN
outbox_events o ON a.entity_id=o.aggregate_id WHERE a.entity_id=:id"""
            ),
            {"id": UUID(doc["evaluation_id"])},
        ).one()
        assert str(row[0]) == entries[1]["principal_id"] and row[1]
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.transactions.get(tx.transaction_id) == tx
        assert uow.profiles.get(tx.customer_id, tx.currency) is None


def test_review_lifecycle_actor_history_replay_no_learning(api, db_engine):
    client, tx, entries = api
    evaluation = evaluate(client, tx)
    opened = case(client, evaluation)
    identifier = opened.json()["case_id"]
    assert (
        client.post(
            PATH + "/cases",
            json={"evaluation_id": evaluation.json()["evaluation_id"]},
            headers=headers("service", "bad-case"),
        ).status_code
        == 403
    )
    assert (
        client.post(
            PATH + "/cases",
            json={"evaluation_id": evaluation.json()["evaluation_id"]},
            headers=headers("analyst", "another-key"),
        ).status_code
        == 409
    )
    assert change(client, identifier, 0, "close", "bad-close").status_code == 409
    started = change(client, identifier, 0, "start_review", "start")
    assert started.status_code == 200, started.text
    assert started.json()["state"] == "UNDER_REVIEW"
    assert (
        change(
            client, identifier, 0, "feedback", "stale", verdict="LEGITIMATE", comment="checked"
        ).status_code
        == 409
    )
    pending = change(
        client,
        identifier,
        1,
        "feedback",
        "needs",
        verdict="NEEDS_INVESTIGATION",
        comment="Awaiting independent evidence",
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["version"] == 2 and pending.json()["state"] == "UNDER_REVIEW"
    terminal = change(
        client,
        identifier,
        2,
        "feedback",
        "verdict",
        verdict="LEGITIMATE",
        comment="Reviewed synthetic evidence",
    )
    assert terminal.status_code == 200, terminal.text
    assert terminal.json()["version"] == 4 and terminal.json()["state"] == "LEGITIMATE"
    closed = change(client, identifier, 4, "close", "close")
    assert closed.status_code == 200 and closed.json()["state"] == "CLOSED"
    assert (
        change(
            client,
            identifier,
            2,
            "feedback",
            "verdict",
            verdict="LEGITIMATE",
            comment="Reviewed synthetic evidence",
        ).content
        == terminal.content
    )
    assert (
        change(
            client,
            identifier,
            5,
            "feedback",
            "correction",
            verdict="CONFIRMED_FRAUD",
            comment="try overwrite",
        ).status_code
        == 409
    )
    doc = client.get(opened.headers["location"], headers=headers("analyst")).json()
    assert len(doc["history"]) == 3 and len(doc["feedback"]) == 2
    assert all(f["actor_id"] == entries[2]["principal_id"] for f in doc["feedback"])
    assert doc["operational_action_executed"] is doc["admission_workflow_verified"] is False
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(tx.customer_id, tx.currency) is None
        assert uow.transactions.get(tx.transaction_id) == tx


@pytest.mark.parametrize("method", ["audit", "outbox", "idempotency"])
def test_atomic_evaluation_rollback(api, db_engine, monkeypatch, method):
    client, tx, _ = api
    cls = {
        "audit": PostgresAuditRepository,
        "outbox": PostgresOutboxRepository,
        "idempotency": PostgresIdempotencyRepository,
    }[method]

    def fail(*args, **kwargs):
        raise RuntimeError("injected after preceding writes")

    with monkeypatch.context() as patch:
        patch.setattr(cls, "add", fail)
        response = client.post(PATH + "/evaluations", json=request(tx), headers=headers())
        assert response.status_code == 500
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM experimental_evaluations WHERE transaction_id=:id"),
                {"id": tx.transaction_id},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM idempotency_records WHERE transaction_id=:id"),
                {"id": tx.transaction_id},
            ).scalar_one()
            == 0
        )
    assert evaluate(client, tx).status_code == 201


def test_concurrent_evaluation_replays_once(setup, db_engine):
    tx, entries, _ = setup
    principal = Principal(
        UUID(entries[1]["principal_id"]), frozenset({Role.SERVICE}), frozenset({tx.customer_id})
    )
    service = EvaluationService(
        partial(create_unit_of_work, db_engine), ExperimentalEvaluationEngine()
    )

    def run(_):
        return service.submit(
            principal,
            "concurrent",
            tx.transaction_id,
            profile_version=None,
            strategy=Strategy.RULES_ONLY,
            manifest_sha256=None,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    assert sum(not result.replayed for result in results) == 1
    assert len({r.response_json for r in results}) == 1


def test_concurrent_reviewer_version_conflict(api):
    client, tx, _ = api
    created = case(client, evaluate(client, tx)).json()
    identifier = created["case_id"]
    assert change(client, identifier, 0, "start_review", "start").status_code == 200

    def run(verdict):
        return change(
            client, identifier, 1, "feedback", verdict, verdict=verdict, comment="Concurrent review"
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["LEGITIMATE", "CONFIRMED_FRAUD"]))
    assert sorted(r.status_code for r in results) == [200, 409]
    doc = client.get(PATH + f"/cases/{identifier}", headers=headers("analyst")).json()
    assert len(doc["feedback"]) == 1


@pytest.mark.parametrize(
    "table,column",
    [
        ("experimental_evaluations", "evaluation_id"),
        ("evaluation_cases", "case_id"),
        ("evaluation_case_transitions", "case_id"),
        ("evaluation_feedback", "case_id"),
    ],
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
def test_immutable_evaluation_review_history(api, db_engine, table, column, operation):
    client, tx, _ = api
    evaluated = evaluate(client, tx)
    opened = case(client, evaluated).json()
    caseid = opened["case_id"]
    assert change(client, caseid, 0, "start_review", "start").status_code == 200
    assert (
        change(
            client,
            caseid,
            1,
            "feedback",
            "feedback",
            verdict="NEEDS_INVESTIGATION",
            comment="More evidence",
        ).status_code
        == 200
    )
    identifier = (
        evaluated.json()["evaluation_id"] if table == "experimental_evaluations" else caseid
    )
    if operation == "UPDATE":
        query = f"UPDATE {table} SET {column}={column} WHERE {column}=:id"
    elif operation == "DELETE":
        query = f"DELETE FROM {table} WHERE {column}=:id"
    else:
        query = f"TRUNCATE {table} CASCADE"
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(text(query), {"id": UUID(identifier)})


def test_opt_in_and_validation(setup, db_engine):
    tx, _, config = setup
    app = create_app(
        config.model_copy(update={"experimental_enabled": False}),
        uow_factory=partial(create_unit_of_work, db_engine),
    )
    with TestClient(app) as client:
        assert (
            client.post(PATH + "/evaluations", json=request(tx), headers=headers()).status_code
            == 503
        )
    with TestClient(
        create_app(config, uow_factory=partial(create_unit_of_work, db_engine))
    ) as client:
        for updates in (
            {"profile_version": 0},
            {"strategy": "ml_only"},
            {"manifest_sha256": "a" * 64},
            {"score": 0.9},
        ):
            assert (
                client.post(
                    PATH + "/evaluations", json={**request(tx), **updates}, headers=headers()
                ).status_code
                == 422
            )
        for strategy in ("ml_only", "hybrid"):
            response = client.post(
                PATH + "/evaluations",
                json={**request(tx), "strategy": strategy, "manifest_sha256": "a" * 64},
                headers=headers(),
            )
            assert response.status_code == 503


@pytest.mark.parametrize("strategy", ["ml_only", "hybrid"])
def test_native_model_provenance_and_restart_replay(setup, db_engine, native_bundle, strategy):
    tx, entries, config = setup
    bundle, pin, _ = native_bundle
    enabled = config.model_copy(
        update={"experimental_model_bundle": bundle, "experimental_manifest_sha256": pin}
    )
    payload = {**request(tx), "strategy": strategy, "manifest_sha256": pin}
    with TestClient(
        create_app(enabled, uow_factory=partial(create_unit_of_work, db_engine))
    ) as client:
        first = client.post(PATH + "/evaluations", json=payload, headers=headers())
        assert first.status_code == 201, first.text
        doc = first.json()
        manifest = json.loads(doc["model_manifest_json"])
        assert manifest["trained_at"] is None
        assert hashlib.sha256(doc["model_manifest_json"].encode()).hexdigest() == pin
        assert doc["risk"]["prediction"]["model_version"] == manifest["model_version"]
        assert doc["explanation"]["model"]["model_version"] == manifest["model_version"]
        assert doc["explanation"]["model"]["features"] == doc["risk"]["features"]
        assert doc["production_eligible"] is False
        assert (doc["risk"]["status"] == "SCORED") == (strategy == "ml_only")
    # Exact completed response survives process restart with no model configured.
    with TestClient(
        create_app(config, uow_factory=partial(create_unit_of_work, db_engine))
    ) as client:
        replay = client.post(PATH + "/evaluations", json=payload, headers=headers())
        assert replay.status_code == 201 and replay.content == first.content
        assert (
            client.get(first.headers["location"], headers=headers("analyst")).content
            == first.content
        )
        assert (
            client.post(
                PATH + "/evaluations", json=payload, headers=headers(key="new-evaluation")
            ).status_code
            == 503
        )
        changed = {**payload, "manifest_sha256": "a" * 64}
        assert (
            client.post(PATH + "/evaluations", json=changed, headers=headers()).status_code == 409
        )
        # Current authorization is checked even for a completed idempotency key.
    entries[1]["customer_ids"] = []
    revoked = config.model_copy(
        update={"api_principals": __import__("pydantic").SecretStr(json.dumps(entries))}
    )
    with TestClient(
        create_app(revoked, uow_factory=partial(create_unit_of_work, db_engine))
    ) as client:
        assert (
            client.post(PATH + "/evaluations", json=payload, headers=headers()).status_code == 404
        )


@pytest.mark.parametrize("operation", ["case", "feedback"])
def test_review_outbox_failure_rolls_back_every_write(api, db_engine, monkeypatch, operation):
    client, tx, _ = api
    evaluation = evaluate(client, tx)
    if operation == "feedback":
        created = case(client, evaluation).json()
        identifier = created["case_id"]
        assert change(client, identifier, 0, "start_review", "start").status_code == 200

    def fail(*args, **kwargs):
        raise RuntimeError("outbox failed")

    with monkeypatch.context() as patch:
        patch.setattr(PostgresOutboxRepository, "add", fail)
        if operation == "case":
            response = client.post(
                PATH + "/cases",
                json={"evaluation_id": evaluation.json()["evaluation_id"]},
                headers=headers("analyst", "case-fail"),
            )
        else:
            response = change(
                client,
                identifier,
                1,
                "feedback",
                "feedback-fail",
                verdict="LEGITIMATE",
                comment="Reviewed",
            )
        assert response.status_code == 500
    with PostgresUnitOfWork(db_engine) as uow:
        if operation == "case":
            assert uow.reviews.find(UUID(evaluation.json()["evaluation_id"])) is None
        else:
            stored = uow.reviews.get(UUID(identifier))
            assert stored.state.value == "UNDER_REVIEW"
            assert uow.reviews.feedback(UUID(identifier)) == ()


def test_database_requires_terminal_feedback_and_checks_actor(api, db_engine):
    from backend.app.cases.entities import CaseState
    from backend.app.evaluation.contracts import ReviewFeedback
    from backend.app.feedback.entities import AnalystVerdict
    from backend.app.shared.errors import PersistenceConflict

    client, tx, _ = api
    identifier = UUID(case(client, evaluate(client, tx)).json()["case_id"])
    assert change(client, str(identifier), 0, "start_review", "start").status_code == 200
    for wrong_actor in (False, True):
        with pytest.raises(PersistenceConflict), PostgresUnitOfWork(db_engine) as uow:
            stored = uow.reviews.get(identifier, lock=True)
            actor = uuid4()
            now = datetime.now(UTC)
            uow.reviews.save(stored.transition(CaseState.LEGITIMATE, actor, now))
            if wrong_actor:
                uow.reviews.add_feedback(
                    ReviewFeedback(
                        uuid4(),
                        identifier,
                        uuid4(),
                        AnalystVerdict.LEGITIMATE,
                        now,
                        "Invalid actor",
                        1,
                    )
                )
            uow.commit()


def test_capture_late_arrivals_do_not_change_stored_evaluation(api, db_engine):
    client, tx, _ = api
    first = evaluate(client, tx)
    late = replace(tx, transaction_id=uuid4(), timestamp=tx.timestamp - timedelta(minutes=1))
    with PostgresUnitOfWork(db_engine) as uow:
        uow.transactions.add(late)
        uow.commit()
    assert evaluate(client, tx).content == first.content
    second = evaluate(client, tx, key="new-capture")
    assert second.json()["context_sha256"] != first.json()["context_sha256"]
    assert second.json()["risk"]["features"]["values"] != first.json()["risk"]["features"]["values"]
    assert (
        client.get(first.headers["location"], headers=headers("analyst")).content == first.content
    )


def test_evaluation_envelope_database_identity_guard(api, db_engine):
    client, tx, _ = api
    first = evaluate(client, tx)
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO experimental_evaluations
        (evaluation_id,transaction_id,customer_id,currency,actor_id,created_at,response_json)
        SELECT :new_id,transaction_id,customer_id,currency,actor_id,created_at,response_json
        FROM experimental_evaluations WHERE evaluation_id=:id"""),
            {"new_id": uuid4(), "id": UUID(first.json()["evaluation_id"])},
        )
