import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import partial
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from backend.adapters.database.history import PostgresAuditRepository, PostgresOutboxRepository
from backend.adapters.database.idempotency import PostgresIdempotencyRepository
from backend.adapters.database.transactions import PostgresTransactionRepository
from backend.adapters.database.uow import PostgresUnitOfWork, create_unit_of_work
from backend.app.profile.entities import Customer
from backend.app.shared.errors import PersistenceConflict
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres
PATH = "/api/v1/transactions"
TOKENS = {"admin": "a" * 43, "service": "b" * 43, "analyst": "c" * 43, "outsider": "d" * 43}


def headers(role="service", key="request-1"):
    return {"Authorization": f"Bearer {TOKENS[role]}", "Idempotency-Key": key}


def body(customer_id):
    return {
        "transaction_id": str(uuid4()),
        "customer_id": str(customer_id),
        "recipient_id": str(uuid4()),
        "amount": "30000.00",
        "currency": "KZT",
        "timestamp": "2026-09-19T12:00:00+05:00",
        "channel": "MOBILE",
        "device_id": "synthetic-device-1",
    }


@pytest.fixture
def api(db_engine):
    customer_id = uuid4()
    entries = [
        {
            "principal_id": str(uuid4()),
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "roles": [role if role != "outsider" else "service"],
            "customer_ids": [str(customer_id)] if role != "outsider" else [],
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        for role, token in TOKENS.items()
    ]
    with PostgresUnitOfWork(db_engine) as uow:
        uow.customers.add(Customer(customer_id, datetime.now(UTC)))
        uow.commit()
    settings = Settings(
        environment="test",
        database_url=None,
        api_principals=json.dumps(entries),
        _env_file=None,
    )
    app = create_app(settings, uow_factory=partial(create_unit_of_work, db_engine))
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, body(customer_id), entries


def counts(db_engine, transaction_id):
    with db_engine.connect() as connection:
        return tuple(
            connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE {column}=:id"), {"id": transaction_id}
            ).scalar_one()
            for table, column in (
                ("transactions", "transaction_id"),
                ("audit_events", "entity_id"),
                ("outbox_events", "aggregate_id"),
                ("idempotency_records", "transaction_id"),
            )
        )


def test_submit_retrieve_and_exact_durable_replay(api, db_engine):
    client, payload, entries = api
    first = client.post(PATH, json=payload, headers=headers())
    assert first.status_code == 201, first.text
    assert first.headers["idempotency-replayed"] == "false"
    assert first.json()["status"] == "RECEIVED"
    assert first.json()["amount"] == "30000.00"
    assert first.json()["timestamp"] == "2026-09-19T07:00:00+00:00"
    assert "risk_score" not in first.json()
    equivalent = {**payload, "amount": "30000", "timestamp": "2026-09-19T07:00:00Z"}
    replay = client.post(PATH, json=equivalent, headers=headers())
    assert replay.status_code == 201 and replay.content == first.content
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.headers["location"] == first.headers["location"]
    retrieved = client.get(first.headers["location"], headers=headers("analyst"))
    assert retrieved.status_code == 200
    assert retrieved.json() == {**first.json(), "timestamp": "2026-09-19T07:00:00Z"}
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)
    with PostgresUnitOfWork(db_engine) as uow:
        record = uow.idempotency.get(UUID(entries[1]["principal_id"]), "request-1")
        assert record.response_json == first.text
        assert uow.profiles.get(UUID(payload["customer_id"]), "KZT") is None
    with db_engine.connect() as connection:
        row = connection.execute(
            text("""SELECT a.actor_id, a.correlation_id = o.correlation_id
            FROM audit_events a JOIN outbox_events o ON a.entity_id=o.aggregate_id
            WHERE a.entity_id=:id"""),
            {"id": payload["transaction_id"]},
        ).one()
        assert str(row[0]) == entries[1]["principal_id"] and row[1]
        assert (
            connection.execute(
                text("SELECT count(*) FROM risk_assessments WHERE transaction_id=:id"),
                {"id": payload["transaction_id"]},
            ).scalar_one()
            == 0
        )
    # A new app instance must replay PostgreSQL's stored response, not process memory.
    settings = Settings(
        environment="test", database_url=None, api_principals=json.dumps(entries), _env_file=None
    )
    with TestClient(
        create_app(settings, uow_factory=partial(create_unit_of_work, db_engine))
    ) as fresh:
        assert fresh.post(PATH, json=payload, headers=headers()).content == first.content


def test_changed_body_and_duplicate_id_are_explicit_conflicts(api, db_engine):
    client, payload, _ = api
    assert client.post(PATH, json=payload, headers=headers()).status_code == 201
    changed = client.post(PATH, json={**payload, "amount": "30001.00"}, headers=headers())
    assert changed.status_code == 409 and "different request" in changed.text
    duplicate = client.post(PATH, json=payload, headers=headers(key="other-key"))
    assert duplicate.status_code == 409 and "transaction ID" in duplicate.text
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)


def test_idempotency_is_principal_scoped(api, db_engine):
    client, payload, _ = api
    assert client.post(PATH, json=payload, headers=headers()).status_code == 201
    other = {**payload, "transaction_id": str(uuid4())}
    assert client.post(PATH, json=other, headers=headers("admin")).status_code == 201
    assert counts(db_engine, other["transaction_id"]) == (1, 1, 1, 1)


def test_authentication_roles_scope_and_no_existence_leak(api, db_engine):
    client, payload, _ = api
    assert client.post(PATH, json=payload).status_code == 401
    for role in ("analyst", "outsider"):
        assert client.post(PATH, json=payload, headers=headers(role)).status_code == 403
    assert counts(db_engine, payload["transaction_id"]) == (0, 0, 0, 0)
    assert client.post(PATH, json=payload, headers=headers()).status_code == 201
    for transaction_id in (payload["transaction_id"], str(uuid4())):
        response = client.get(f"{PATH}/{transaction_id}", headers=headers("outsider"))
        assert response.status_code == 404 and response.json() == {
            "detail": "transaction not found"
        }
    # An existing idempotency record never bypasses the current scope policy.
    assert client.post(PATH, json=payload, headers=headers("outsider")).status_code == 403


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", "0"),
        ("amount", "-1"),
        ("amount", "NaN"),
        ("amount", "Infinity"),
        ("amount", "1.001"),
        ("amount", "10000000000000000.00"),
        ("amount", 30000),
        ("timestamp", "2026-09-19T12:00:00"),
        ("timestamp", 123456789),
        ("timestamp", "0001-01-01T00:00:00+05:00"),
        ("currency", "kzt"),
        ("channel", "UNKNOWN"),
        ("device_id", "   "),
        ("device_id", "x" * 201),
        ("device_id", "device\u0000"),
        ("transaction_id", "invalid"),
        ("status", "EVALUATED"),
        ("principal_id", "spoofed"),
        ("customer_id", None),
    ],
)
def test_invalid_input_does_not_write_or_echo_body(api, db_engine, field, value):
    client, payload, _ = api
    response = client.post(PATH, json={**payload, field: value}, headers=headers())
    assert response.status_code == 422, response.text
    assert "synthetic-device-1" not in response.text
    assert counts(db_engine, payload["transaction_id"]) == (0, 0, 0, 0)


@pytest.mark.parametrize("key", [None, "", "a" * 201, "has space"])
def test_key_required_and_validated(api, key):
    client, payload, _ = api
    request_headers = headers(key=key) if key is not None else headers()
    if key is None:
        del request_headers["Idempotency-Key"]
    assert client.post(PATH, json=payload, headers=request_headers).status_code == 422


def test_unpaired_unicode_surrogate_is_invalid_input(api, db_engine):
    client, payload, _ = api
    response = client.post(
        PATH,
        content=json.dumps({**payload, "device_id": "device\ud800"}),
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert counts(db_engine, payload["transaction_id"]) == (0, 0, 0, 0)


def test_unknown_customer_and_enrollment_authorization(api, db_engine):
    client, payload, _ = api
    payload["customer_id"] = str(uuid4())
    assert client.post(PATH, json=payload, headers=headers("admin")).status_code == 404
    enrollment = {"customer_id": payload["customer_id"], "timezone": "Asia/Almaty"}
    assert client.post("/api/v1/customers", json=enrollment, headers=headers()).status_code == 403
    assert (
        client.post(
            "/api/v1/customers",
            json={**enrollment, "timezone": "Unknown/Place"},
            headers=headers("admin"),
        ).status_code
        == 422
    )
    assert (
        client.post("/api/v1/customers", json=enrollment, headers=headers("admin")).status_code
        == 201
    )
    assert (
        client.post("/api/v1/customers", json=enrollment, headers=headers("admin")).status_code
        == 409
    )
    assert client.post(PATH, json=payload, headers=headers("admin")).status_code == 201
    with PostgresUnitOfWork(db_engine) as uow:
        assert uow.profiles.get(UUID(payload["customer_id"]), "KZT") is None


@pytest.mark.parametrize(
    "target,method",
    [
        (PostgresAuditRepository, "add"),
        (PostgresOutboxRepository, "add"),
        (PostgresIdempotencyRepository, "add"),
        (PostgresUnitOfWork, "commit"),
    ],
)
def test_partial_write_failure_rolls_back_and_retry_succeeds(
    api, db_engine, monkeypatch, target, method
):
    client, payload, _ = api

    def fail(*args, **kwargs):
        raise RuntimeError("injected failure with sensitive internal detail")

    with monkeypatch.context() as patch:
        patch.setattr(target, method, fail)
        response = client.post(PATH, json=payload, headers=headers())
        assert response.status_code == 500
        assert response.headers["cache-control"] == "no-store"
        assert "sensitive" not in response.text
    assert counts(db_engine, payload["transaction_id"]) == (0, 0, 0, 0)
    assert client.post(PATH, json=payload, headers=headers()).status_code == 201
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)


@pytest.mark.parametrize("same_body", [True, False])
def test_concurrent_same_key_serializes_outcome(api, db_engine, same_body):
    client, payload, _ = api
    barrier = Barrier(2)

    def submit(changed):
        barrier.wait(timeout=5)
        return client.post(PATH, json=changed, headers=headers())

    other = payload if same_body else {**payload, "amount": "40000.00"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit, item) for item in (payload, other)]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in results) == (
        [201, 201] if same_body else [201, 409]
    )
    if same_body:
        assert results[0].content == results[1].content
        assert {response.headers["idempotency-replayed"] for response in results} == {
            "true",
            "false",
        }
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)


def test_concurrent_duplicate_id_different_keys_hits_database_constraint(
    api, db_engine, monkeypatch
):
    client, payload, _ = api
    barrier = Barrier(2)
    original = PostgresTransactionRepository.add

    def simultaneous_insert(self, transaction):
        # Both have passed the read check. Only PostgreSQL's unique constraint can decide.
        barrier.wait(timeout=5)
        return original(self, transaction)

    monkeypatch.setattr(PostgresTransactionRepository, "add", simultaneous_insert)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, PATH, json=payload, headers=headers(key=key))
            for key in ("first", "second")
        ]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in results) == [201, 409]
    assert "transaction ID" in next(
        response.text for response in results if response.status_code == 409
    )
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)


def test_real_engine_lifespan_configuration(api, db_engine):
    _, payload, entries = api
    settings = Settings(
        environment="test",
        database_url=db_engine.url.render_as_string(hide_password=False),
        api_principals=json.dumps(entries),
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        assert client.post(PATH, json=payload, headers=headers()).status_code == 201


def test_token_rotation_preserves_principal_scope_and_revocation_blocks_replay(api, db_engine):
    client, payload, entries = api
    first = client.post(PATH, json=payload, headers=headers())
    rotated = "e" * 43
    entries[1]["token_sha256"] = hashlib.sha256(rotated.encode()).hexdigest()

    def settings():
        return Settings(
            environment="test",
            database_url=None,
            api_principals=json.dumps(entries),
            _env_file=None,
        )

    factory = partial(create_unit_of_work, db_engine)
    with TestClient(create_app(settings(), uow_factory=factory)) as rotated_client:
        assert rotated_client.post(PATH, json=payload, headers=headers()).status_code == 401
        response = rotated_client.post(
            PATH, json=payload, headers={**headers(), "Authorization": f"Bearer {rotated}"}
        )
        assert response.status_code == 201 and response.content == first.content
        assert response.headers["idempotency-replayed"] == "true"
    entries[1]["customer_ids"] = []
    with TestClient(create_app(settings(), uow_factory=factory)) as revoked_client:
        assert (
            revoked_client.post(
                PATH, json=payload, headers={**headers(), "Authorization": f"Bearer {rotated}"}
            ).status_code
            == 403
        )
    assert counts(db_engine, payload["transaction_id"]) == (1, 1, 1, 1)


@pytest.mark.parametrize(
    "error,status",
    [
        (OperationalError("private SQL", {}, Exception("secret connection string")), 503),
        (PersistenceConflict("private constraint"), 500),
    ],
)
def test_database_errors_are_sanitized_and_leave_no_writes(
    api, db_engine, monkeypatch, error, status
):
    client, payload, _ = api

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(PostgresTransactionRepository, "add", fail)
    response = client.post(PATH, json=payload, headers=headers())
    assert response.status_code == status
    assert "private" not in response.text and "secret" not in response.text
    assert counts(db_engine, payload["transaction_id"]) == (0, 0, 0, 0)
