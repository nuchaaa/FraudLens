"""Human sessions are tested against disposable PostgreSQL, never SQLite."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from threading import Barrier, Event, Lock, current_thread, main_thread
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.adapters.database.history import PostgresAuditRepository
from backend.adapters.database.identity import PostgresIdentityRepository
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.passwords import Argon2Passwords
from backend.app.identity.service import AuthenticationDenied, IdentityService
from backend.app.shared.security import Role
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres
PASSWORD = "A long local password for tests"
ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def browser(db_engine):
    settings = Settings(
        environment="test",
        human_auth_enabled=True,
        human_origin=ORIGIN,
        human_local_insecure=True,
        _env_file=None,
    )
    app = create_app(settings, uow_factory=partial(create_unit_of_work, db_engine))
    with TestClient(app, base_url=ORIGIN) as client:
        identity = app.state.services.identity
        assert identity is not None
        yield client, identity


def _login(client: TestClient, login: str = "analyst-one"):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"login": login, "password": PASSWORD},
    )


def test_password_recovery_during_login_rejects_old_password(db_engine, monkeypatch):
    identity = IdentityService(partial(create_unit_of_work, db_engine), Argon2Passwords())
    account_id = identity.provision(
        "recovery-race", PASSWORD, Role.ADMIN, frozenset(), operator_id=uuid4()
    )
    reached_lock, continue_login = Event(), Event()
    original = PostgresIdentityRepository.lock_account

    def pause_login(self, identifier):
        if current_thread() is not main_thread():
            reached_lock.set()
            assert continue_login.wait(timeout=5)
        original(self, identifier)

    monkeypatch.setattr(PostgresIdentityRepository, "lock_account", pause_login)
    with ThreadPoolExecutor(max_workers=1) as pool:
        attempt = pool.submit(identity.login, "recovery-race", PASSWORD)
        assert reached_lock.wait(timeout=5)
        identity.change(account_id, operator_id=uuid4(), password="A different recovery password")
        continue_login.set()
        with pytest.raises(AuthenticationDenied):
            attempt.result(timeout=5)
    assert identity.login("recovery-race", "A different recovery password")


def test_login_scope_csrf_rotation_reuse_and_logout(browser, db_engine):
    client, identity = browser
    customer = uuid4()
    account_id = identity.provision(
        "analyst-one", PASSWORD, Role.ANALYST, frozenset({customer}), operator_id=uuid4()
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"login": "analyst-one", "password": PASSWORD}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers={"Origin": "null"},
            json={"login": "analyst-one", "password": PASSWORD},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"login": "missing-user", "password": PASSWORD},
        ).json()
        == client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"login": "analyst-one", "password": "wrong password"},
        ).json()
    )
    response = _login(client)
    assert response.status_code == 200
    document = response.json()
    assert document["account_id"] == str(account_id)
    assert document["role"] == "analyst"
    assert document["customer_ids"] == [str(customer)]
    assert "password" not in response.text and "access" not in response.text
    assert all(
        "httponly" in item.lower() and "samesite=strict" in item.lower()
        for item in response.headers.get_list("set-cookie")
    )
    old_access = client.cookies.get("fl_access")
    old_refresh = client.cookies.get("fl_refresh")
    old_csrf = client.cookies.get("fl_csrf")
    assert client.get("/api/v1/auth/session").status_code == 200
    assert client.get("/api/v1/console/summary").status_code == 200
    assert (
        client.get("/api/v1/console/summary", headers={"Authorization": "Bearer bad"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/experimental/evaluations", json={}, headers={"Origin": ORIGIN}
        ).status_code
        == 403
    )
    refreshed = client.post(
        "/api/v1/auth/refresh", headers={"Origin": ORIGIN, "X-CSRF-Token": document["csrf"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    assert client.cookies.get("fl_access") != old_access
    assert client.cookies.get("fl_refresh") != old_refresh
    assert identity.session(old_access, old_csrf) is None
    # A stolen consumed token, with its matching old CSRF, invalidates the newest generation.
    with pytest.raises(AuthenticationDenied):
        identity.refresh(old_refresh, old_csrf, old_csrf)
    assert client.get("/api/v1/auth/session").status_code == 401
    with db_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM human_consumed_refresh")).scalar_one()
            >= 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM audit_events WHERE action LIKE 'HUMAN_%'")
            ).scalar_one()
            >= 3
        )


def test_policy_change_revokes_sessions_and_authorization_precedes_business_replay(browser):
    client, identity = browser
    account_id = identity.provision(
        "analyst-two", PASSWORD, Role.ANALYST, frozenset({uuid4()}), operator_id=uuid4()
    )
    assert _login(client, "analyst-two").status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 200
    identity.change(account_id, operator_id=uuid4(), active=False)
    assert client.get("/api/v1/auth/session").status_code == 401
    assert client.get("/api/v1/console/summary").status_code == 401
    assert _login(client, "analyst-two").status_code == 401


def test_parallel_refresh_reuses_old_digest_and_revokes_family(browser):
    client, identity = browser
    identity.provision("analyst-three", PASSWORD, Role.ANALYST, frozenset(), operator_id=uuid4())
    response = _login(client, "analyst-three")
    assert response.status_code == 200
    refresh = client.cookies.get("fl_refresh")
    csrf = response.json()["csrf"]

    def attempt():
        try:
            return identity.refresh(refresh, csrf, csrf)
        except AuthenticationDenied:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(item is not None for item in results) == 1
    latest = next(item for item in results if item is not None)
    assert identity.session(latest.access, latest.csrf) is None


def test_refresh_race_after_both_initial_reads_revokes_family(browser, monkeypatch):
    client, identity = browser
    identity.provision("analyst-four", PASSWORD, Role.ANALYST, frozenset(), operator_id=uuid4())
    assert _login(client, "analyst-four").status_code == 200
    refresh = client.cookies.get("fl_refresh")
    csrf = client.cookies.get("fl_csrf")
    barrier = Barrier(2)
    lock = Lock()
    count = 0
    original = PostgresIdentityRepository.refresh

    def synchronized(self, digest):
        nonlocal count
        result = original(self, digest)
        if result[0] is not None:
            with lock:
                count += 1
                first_reads = count <= 2
            if first_reads:
                barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(PostgresIdentityRepository, "refresh", synchronized)

    def attempt():
        try:
            return identity.refresh(refresh, csrf, csrf)
        except AuthenticationDenied:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(item is not None for item in results) == 1
    latest = next(item for item in results if item is not None)
    assert identity.session(latest.access, latest.csrf) is None


def test_session_bootstrap_logout_and_shared_login_throttle(browser, db_engine):
    client, identity = browser
    identity.provision("analyst-five", PASSWORD, Role.ANALYST, frozenset(), operator_id=uuid4())
    for _ in range(10):
        denied = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"login": "analyst-five", "password": "A different long password"},
        )
        assert denied.status_code == 401
    assert _login(client, "analyst-five").status_code == 401
    restarted = IdentityService(partial(create_unit_of_work, db_engine), Argon2Passwords())
    with pytest.raises(AuthenticationDenied):
        restarted.login("analyst-five", PASSWORD)
    with db_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM human_login_throttle")).scalar_one()
            <= 257
        )
    identity.provision("analyst-six", PASSWORD, Role.ANALYST, frozenset(), operator_id=uuid4())
    assert _login(client, "analyst-six").status_code == 200
    csrf = client.cookies.get("fl_csrf")
    client.cookies.delete("fl_access")
    pending = client.get("/api/v1/auth/session")
    assert pending.json() == {"refresh_required": True, "csrf": csrf}
    renewed = client.post("/api/v1/auth/refresh", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
    assert renewed.status_code == 200
    assert client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN}).status_code == 401
    result = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": renewed.json()["csrf"]},
    )
    assert result.status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 401


def test_human_policy_scope_csrf_and_authorization_before_replay(browser):
    client, identity = browser
    account_id = identity.provision(
        "local-admin", PASSWORD, Role.ADMIN, frozenset(), operator_id=uuid4()
    )
    initial = _login(client, "local-admin")
    assert initial.status_code == 200
    customer = uuid4()
    body = {"customer_id": str(customer), "timezone": "UTC"}
    path = "/api/v1/customers"
    assert client.post(path, json=body, headers={"Origin": ORIGIN}).status_code == 403
    assert (
        client.post(
            path,
            json=body,
            headers={"Origin": "http://evil.invalid", "X-CSRF-Token": initial.json()["csrf"]},
        ).status_code
        == 403
    )
    headers = {
        "Origin": ORIGIN,
        "X-CSRF-Token": initial.json()["csrf"],
        "Idempotency-Key": "human-customer-1",
    }
    assert client.post(path, json=body, headers=headers).status_code == 201
    transaction = {
        "transaction_id": str(uuid4()),
        "customer_id": str(customer),
        "recipient_id": str(uuid4()),
        "amount": "25000.00",
        "currency": "KZT",
        "timestamp": datetime.now(UTC).isoformat(),
        "channel": "MOBILE",
        "device_id": "synthetic-device",
    }
    submission = {**headers, "Idempotency-Key": "human-transaction-1"}
    assert (
        client.post("/api/v1/transactions", json=transaction, headers=submission).status_code == 201
    )
    identity.change(
        account_id,
        operator_id=uuid4(),
        role=Role.ANALYST,
        customer_ids=frozenset({customer}),
    )
    assert (
        client.post("/api/v1/transactions", json=transaction, headers=submission).status_code == 401
    )
    next_session = _login(client, "local-admin")
    assert next_session.status_code == 200
    submission["X-CSRF-Token"] = next_session.json()["csrf"]
    assert (
        client.post("/api/v1/transactions", json=transaction, headers=submission).status_code == 403
    )
    assert client.get(f"/api/v1/customers/{uuid4()}/profiles/KZT").status_code == 404
    assert client.get(f"/api/v1/customers/{customer}/profiles/KZT").status_code == 200


def test_secure_cookie_configuration_and_trusted_host(db_engine):
    origin = "https://fraudlens.example"
    settings = Settings(
        environment="production",
        human_auth_enabled=True,
        human_origin=origin,
        _env_file=None,
    )
    app = create_app(settings, uow_factory=partial(create_unit_of_work, db_engine))
    with TestClient(app, base_url=origin) as client:
        identity = app.state.services.identity
        assert identity is not None
        identity.provision("secure-admin", PASSWORD, Role.ADMIN, frozenset(), operator_id=uuid4())
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": origin},
            json={"login": "secure-admin", "password": PASSWORD},
        )
        assert response.status_code == 200
        cookies = response.headers.get_list("set-cookie")
        assert all(
            "__Host-fl_" in item and "Secure" in item and "HttpOnly" in item for item in cookies
        )
        assert client.get("/api/v1/auth/session").status_code == 200
        assert (
            client.get("/api/v1/auth/session", headers={"Host": "attacker.invalid"}).status_code
            == 400
        )


def test_production_rejects_insecure_cookie_mode():
    settings = Settings(
        environment="production",
        human_auth_enabled=True,
        human_origin="https://fraudlens.example",
        human_local_insecure=True,
        _env_file=None,
    )
    with pytest.raises(ValueError, match="HTTPS"):
        create_app(settings)


def test_account_changes_roll_back_with_audit_and_service_ids_cannot_collide(
    browser, db_engine, monkeypatch
):
    _, identity = browser
    account_id = identity.provision(
        "analyst-seven", PASSWORD, Role.ANALYST, frozenset(), operator_id=uuid4()
    )
    with db_engine.connect() as connection:
        (encoded,) = connection.execute(
            text("SELECT password_hash FROM human_accounts WHERE account_id=:id"),
            {"id": account_id},
        ).one()
        assert encoded.startswith("$argon2id$") and PASSWORD not in encoded
        assert PASSWORD not in "".join(connection.scalars(text("SELECT detail FROM audit_events")))
    collision = IdentityService(
        partial(create_unit_of_work, db_engine),
        Argon2Passwords(),
        service_principal_ids=frozenset({account_id}),
    )
    with pytest.raises(ValueError, match="overlap"):
        collision.ensure_no_collisions()

    def broken_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(PostgresAuditRepository, "add", broken_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        identity.change(account_id, operator_id=uuid4(), active=False)
    with db_engine.connect() as connection:
        active, version = connection.execute(
            text("SELECT active,authorization_version FROM human_accounts WHERE account_id=:id"),
            {"id": account_id},
        ).one()
        assert active is True and version == 1


def test_operator_cli_provisions_and_recovers_without_password_arguments(db_engine):
    actor = uuid4()
    env = {
        **os.environ,
        "FRAUDLENS_DATABASE_URL": db_engine.url.render_as_string(hide_password=False),
        "FRAUDLENS_API_PRINCIPALS": "[]",
    }
    base = [sys.executable, "-m", "backend.adapters.identity"]
    provision = [
        *base,
        "provision",
        "--operator-id",
        str(actor),
        "--login",
        "cli-analyst",
        "--role",
        "analyst",
        "--customer-id",
        str(uuid4()),
    ]
    assert PASSWORD not in repr(provision)
    created = subprocess.run(
        provision,
        input=f"{PASSWORD}\n{PASSWORD}\n",
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    assert PASSWORD not in created.stdout + created.stderr
    account_id = created.stdout.strip().rsplit(" ", 1)[-1]
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM human_accounts WHERE account_id=:id"),
                {"id": account_id},
            ).scalar_one()
            == 1
        )
    changed = "Another long recovery password"
    recovered = subprocess.run(
        [*base, "recover", "--operator-id", str(actor), "--account-id", account_id],
        input=f"{changed}\n{changed}\n",
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    assert changed not in recovered.stdout + recovered.stderr
    subprocess.run(
        [*base, "disable", "--operator-id", str(actor), "--account-id", account_id],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    with db_engine.connect() as connection:
        active, version = connection.execute(
            text("SELECT active, authorization_version FROM human_accounts WHERE account_id=:id"),
            {"id": account_id},
        ).one()
        assert active is False and version == 3
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE actor_id=:actor "
                    "AND action LIKE 'HUMAN_ACCOUNT_%'"
                ),
                {"actor": actor},
            ).scalar_one()
            == 3
        )
