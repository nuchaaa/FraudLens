"""Real login-role proof on a newly created disposable PostgreSQL database."""

import os
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.delivery import PostgresDeliveryQueue, PostgresRecordingConsumer
from backend.adapters.database.grants import apply_runtime_grants, verify_runtime_role
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.passwords import Argon2Passwords
from backend.app.identity.service import IdentityService
from backend.app.shared.security import Principal, Role
from backend.app.transaction.entities import Channel, Transaction
from backend.app.transaction.service import TransactionService
from backend.config import Settings
from backend.main import create_app

pytestmark = pytest.mark.postgres


def _denied(engine: Engine, statement: str) -> None:
    with engine.connect() as connection, pytest.raises(DBAPIError):
        connection.exec_driver_sql(statement)


def test_dedicated_login_roles_can_work_but_cannot_cross_boundaries(monkeypatch):
    source = os.getenv("TEST_DATABASE_URL")
    if not source:
        pytest.skip("TEST_DATABASE_URL not set; disposable PostgreSQL required")
    url = make_url(source)
    if not (url.database or "").endswith("_test"):
        pytest.fail("role test requires a disposable *_test database")

    suffix = uuid4().hex[:12]
    database = f"fl_roles_{suffix}_test"
    migrator, api, worker, operator = (
        f"fl_{kind}_{suffix}" for kind in ("mig", "api", "wrk", "op")
    )
    passwords = {name: secrets.token_urlsafe(24) for name in (migrator, api, worker, operator)}
    admin = create_database_engine(source).execution_options(isolation_level="AUTOCOMMIT")
    created: list[str] = []
    try:
        with admin.connect() as connection:
            for role, password in passwords.items():
                connection.exec_driver_sql(f"CREATE ROLE {role} LOGIN PASSWORD '{password}'")
                created.append(role)
            connection.exec_driver_sql(f"CREATE DATABASE {database} OWNER {migrator}")

        def engine_for(role: str) -> Engine:
            scoped = url.set(username=role, password=passwords[role], database=database)
            scoped = scoped.update_query_dict({"options": "-csearch_path=fraudlens"})
            return create_database_engine(scoped.render_as_string(hide_password=False))

        migrator_engine = engine_for(migrator)
        api_engine = engine_for(api)
        worker_engine = engine_for(worker)
        operator_engine = engine_for(operator)
        try:
            with migrator_engine.begin() as connection:
                connection.exec_driver_sql("CREATE SCHEMA fraudlens")
            monkeypatch.setenv(
                "FRAUDLENS_DATABASE_URL",
                migrator_engine.url.render_as_string(hide_password=False),
            )
            command.upgrade(
                Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head"
            )
            with migrator_engine.begin() as connection:
                apply_runtime_grants(
                    connection,
                    schema="fraudlens",
                    api_role=api,
                    worker_role=worker,
                    operator_role=operator,
                )
            with migrator_engine.begin() as connection:
                connection.exec_driver_sql("GRANT UPDATE (amount) ON transactions TO PUBLIC")
            with (
                api_engine.connect() as connection,
                pytest.raises(ValueError, match="column privilege"),
            ):
                verify_runtime_role(connection, "api")
            with migrator_engine.begin() as connection:
                connection.exec_driver_sql("REVOKE UPDATE (amount) ON transactions FROM PUBLIC")
                connection.exec_driver_sql("GRANT SELECT ON alembic_version TO PUBLIC")
            with (
                api_engine.connect() as connection,
                pytest.raises(ValueError, match="table privilege"),
            ):
                verify_runtime_role(connection, "api")
            with migrator_engine.begin() as connection:
                connection.exec_driver_sql("REVOKE SELECT ON alembic_version FROM PUBLIC")

            with api_engine.connect() as connection:
                verify_runtime_role(connection, "api")
                assert connection.scalar(text("SELECT current_user")) == api
                assert connection.scalar(text("SELECT count(*) FROM customers")) == 0
                assert (
                    connection.scalar(
                        text(
                            "SELECT has_database_privilege("
                            "current_user, current_database(), 'TEMP')"
                        )
                    )
                    is False
                )
            _denied(api_engine, "CREATE TABLE fraudlens.escape(id integer)")
            _denied(api_engine, "CREATE TABLE public.escape(id integer)")
            _denied(api_engine, "CREATE TEMP TABLE escape(id integer)")
            _denied(api_engine, "ALTER TABLE fraudlens.transactions DISABLE TRIGGER ALL")
            _denied(api_engine, "DELETE FROM transactions")
            _denied(api_engine, "UPDATE profile_revisions SET version=100")
            _denied(api_engine, "INSERT INTO human_accounts(account_id) VALUES (gen_random_uuid())")
            _denied(api_engine, "UPDATE outbox_delivery SET attempts=100")
            _denied(worker_engine, "SELECT * FROM human_accounts")
            _denied(
                worker_engine, "INSERT INTO transactions(transaction_id) VALUES (gen_random_uuid())"
            )
            _denied(operator_engine, "SELECT * FROM transactions")
            _denied(operator_engine, "UPDATE human_sessions SET access_sha256='x'")
            with worker_engine.connect() as connection:
                verify_runtime_role(connection, "worker")
            with operator_engine.connect() as connection:
                verify_runtime_role(connection, "operator")
            with migrator_engine.connect() as connection, pytest.raises(ValueError):
                verify_runtime_role(connection, "api")

            identity_operator = IdentityService(
                partial(create_unit_of_work, operator_engine), Argon2Passwords()
            )
            account_id = identity_operator.provision(
                "role-admin",
                "Test only long passphrase",
                Role.ADMIN,
                frozenset(),
                operator_id=uuid4(),
            )
            origin = "https://fraudlens.example.test"
            app = create_app(
                Settings(
                    environment="production",
                    database_url=api_engine.url.render_as_string(hide_password=False),
                    human_auth_enabled=True,
                    human_origin=origin,
                    _env_file=None,
                )
            )
            with TestClient(app, base_url=origin) as client:
                assert client.get("/health/live").status_code == 200
                assert client.get("/docs").status_code == 404
                assert (
                    client.get("/health/live", headers={"Host": "evil.example"}).status_code == 400
                )
                response = client.post(
                    "/api/v1/auth/login",
                    headers={"Origin": origin, "X-Forwarded-Host": "evil.example"},
                    json={"login": "role-admin", "password": "Test only long passphrase"},
                )
                assert response.status_code == 200
                assert all(
                    "secure" in cookie.lower() and "httponly" in cookie.lower()
                    for cookie in response.headers.get_list("set-cookie")
                )
            identity_api = IdentityService(
                partial(create_unit_of_work, api_engine), Argon2Passwords()
            )
            issued = identity_api.login("role-admin", "Test only long passphrase")
            assert identity_api.session(issued.access, issued.csrf) is not None
            identity_operator.change(account_id, operator_id=uuid4(), active=False)
            assert identity_api.session(issued.access, issued.csrf) is None

            transactions = TransactionService(partial(create_unit_of_work, api_engine))
            principal = Principal(uuid4(), frozenset({Role.ADMIN}))
            customer = uuid4()
            transactions.enroll_customer(principal, customer, "Asia/Almaty")
            tx = Transaction(
                uuid4(),
                customer,
                uuid4(),
                Decimal("30000.00"),
                "KZT",
                datetime.now(UTC),
                Channel.MOBILE,
                "role-test-device",
            )
            assert transactions.submit(principal, "role-test", tx).status_code == 201
            queue = PostgresDeliveryQueue(worker_engine)
            claim = queue.claim()
            assert claim is not None
            PostgresRecordingConsumer(worker_engine).publish(claim.event)
            assert queue.acknowledge(claim) is True
        finally:
            for engine in (migrator_engine, api_engine, worker_engine, operator_engine):
                engine.dispose()
    finally:
        with admin.connect() as connection:
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")
            for role in reversed(created):
                connection.exec_driver_sql(f"DROP ROLE {role}")
        admin.dispose()
