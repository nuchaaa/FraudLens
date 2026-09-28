import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.adapters.security import CredentialRegistry
from backend.app.demo.scenarios import build_plan
from backend.app.shared.security import Forbidden, Principal, Role
from backend.app.transaction.entities import TransactionStatus
from backend.app.transaction.service import (
    TransactionService,
    canonical_request_digest,
    validate_idempotency_key,
)
from backend.config import Settings
from backend.main import create_app

TOKEN = "a" * 43  # Synthetic fixture, never a deployed credential.


def credential(**overrides):
    return {
        "principal_id": str(uuid4()),
        "token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
        "roles": ["service"],
        "customer_ids": [str(uuid4())],
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        **overrides,
    }


def test_registry_authenticates_scopes_and_enforces_expiry():
    entry = credential()
    registry = CredentialRegistry(json.dumps([entry]))
    principal = registry.authenticate(TOKEN)
    assert str(principal.principal_id) == entry["principal_id"]
    assert principal.roles == {Role.SERVICE}
    assert {str(value) for value in principal.customer_ids} == set(entry["customer_ids"])
    assert registry.authenticate(TOKEN, now=datetime.fromisoformat(entry["expires_at"])) is None
    assert registry.authenticate("b" * 43) is None
    assert registry.authenticate("short") is None
    assert CredentialRegistry(None).authenticate(TOKEN) is None


@pytest.mark.parametrize(
    "entry",
    [
        {"roles": []},
        {"roles": ["root"]},
        {"token_sha256": "raw-secret"},
        {"expires_at": "2026-10-01T12:00:00"},
        {"extra": "secret"},
    ],
)
def test_registry_rejects_bad_configuration_without_echoing_secrets(entry):
    with pytest.raises(ValueError, match=r"^invalid API principal configuration$"):
        CredentialRegistry(json.dumps([credential(**entry)]))


def test_registry_rejects_duplicate_principals_and_tokens():
    entry = credential()
    for second in (
        credential(),
        credential(principal_id=entry["principal_id"], token_sha256="b" * 64),
    ):
        with pytest.raises(ValueError, match="unique"):
            CredentialRegistry(json.dumps([entry, second]))


def test_settings_hide_credential_configuration():
    settings = Settings(api_principals="secret-registry", _env_file=None)
    assert "secret-registry" not in repr(settings)


def test_missing_credentials_fail_closed_and_missing_storage_is_503():
    settings = Settings(
        environment="test",
        database_url=None,
        api_principals=json.dumps([credential()]),
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        path = f"/api/v1/transactions/{uuid4()}"
        for headers in ({}, {"Authorization": "Basic aaa"}, {"Authorization": "Bearer bad"}):
            response = client.get(path, headers=headers)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
            assert response.headers["cache-control"] == "no-store"
        response = client.get(path, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 503
        assert client.get("/health/live").status_code == 200


def test_demo_evidence_is_opt_in_authenticated_scoped_and_read_only():
    event = build_plan().events[0]
    scoped = credential(customer_ids=[str(event.transaction.customer_id)])
    path = f"/api/v1/experimental/demo/evidence/{event.transaction.transaction_id}"
    settings = Settings(
        environment="test",
        database_url=None,
        api_principals=json.dumps([scoped]),
        experimental_enabled=True,
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get(path).status_code == 401
        response = client.get(path, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["synthetic_only"] is True
        assert response.json()["real_world_verified"] is False
        assert response.json()["verdict_provided"] is False
        assert (
            client.get(
                f"/api/v1/experimental/demo/evidence/{uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ).status_code
            == 404
        )

    unscoped = credential()
    with TestClient(
        create_app(
            settings.model_copy(
                update={"api_principals": __import__("pydantic").SecretStr(json.dumps([unscoped]))}
            )
        )
    ) as client:
        assert client.get(path, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 404

    with TestClient(
        create_app(settings.model_copy(update={"experimental_enabled": False}))
    ) as client:
        assert client.get(path, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 503


def test_controlled_scenarios_are_admin_only_opt_in_and_database_free():
    path = "/api/v1/experimental/demo/controlled-scenarios"
    settings = Settings(
        environment="test",
        database_url=None,
        api_principals=json.dumps([credential(roles=["admin"])]),
        experimental_enabled=True,
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get(path).status_code == 401
        response = client.get(path, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        report = response.json()
        assert report["version"] == "controlled-results-v2"
        assert report["synthetic_only"] is True
        assert report["production_eligible"] is False
        assert all(report["checks"].values())
        assert report["outcomes"][-1]["risk_v2_policy_sha256"]
    from pydantic import SecretStr

    analyst = settings.model_copy(update={"api_principals": SecretStr(json.dumps([credential()]))})
    with TestClient(create_app(analyst)) as client:
        assert client.get(path, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 403
    disabled = settings.model_copy(update={"experimental_enabled": False})
    with TestClient(create_app(disabled)) as client:
        assert client.get(path, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 503


@pytest.mark.parametrize("key", ["", " edge", "trailing ", "two words", "a" * 201, "é", "a\nb"])
def test_keys_are_bounded_printable_ascii(key):
    with pytest.raises(ValueError):
        validate_idempotency_key(key)


def test_canonical_digest_normalizes_money_and_instant(transaction):
    equivalent = replace(
        transaction,
        amount=Decimal("30000.000"),
        timestamp=transaction.timestamp.astimezone(timezone(timedelta(hours=5))),
    )
    assert canonical_request_digest(transaction) == canonical_request_digest(equivalent)
    for field, value in (
        ("amount", Decimal("30000.01")),
        ("transaction_id", uuid4()),
        ("customer_id", uuid4()),
        ("device_id", "another-device"),
    ):
        assert canonical_request_digest(transaction) != canonical_request_digest(
            replace(transaction, **{field: value})
        )


def test_service_checks_authorization_before_opening_database(transaction):
    def forbidden_factory():
        pytest.fail("unauthorized requests must not open a unit of work")

    service = TransactionService(forbidden_factory)
    principal = Principal(uuid4(), frozenset({Role.ANALYST}), frozenset({transaction.customer_id}))
    with pytest.raises(Forbidden):
        service.submit(principal, "key", transaction)
    with pytest.raises(Forbidden):
        service.enroll_customer(principal, uuid4(), "UTC")
    admin = Principal(uuid4(), frozenset({Role.ADMIN}))
    with pytest.raises(ValueError, match="RECEIVED"):
        service.submit(admin, "key", replace(transaction, status=TransactionStatus.EVALUATED))


def test_streamed_body_limit_before_parsing():
    settings = Settings(environment="test", database_url=None, api_principals=None, _env_file=None)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/transactions", content=iter([b"a" * 8192, b"b" * 8193]))
        assert response.status_code == 413
        assert response.headers["cache-control"] == "no-store"
