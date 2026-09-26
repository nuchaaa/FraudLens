"""Explicit PostgreSQL grants for a dedicated FraudLens schema/database.

Run only as the migration owner, after Alembic, with separately created login roles.
No role or password is created here; deployment owns credential lifecycle.
"""

import argparse
import re
from collections.abc import Set
from typing import Literal

from sqlalchemy import Connection, inspect, text

from backend.adapters.database.base import create_database_engine
from backend.config import Settings

_NAME = re.compile(r"[a-z][a-z0-9_]{0,62}\Z")

# Review this inventory whenever a migration introduces a table. An unknown table
# fails closed rather than silently granting it to a runtime principal.
_TABLES = frozenset(
    {
        "customers",
        "transactions",
        "profiles",
        "profile_revisions",
        "profile_observations",
        "model_versions",
        "rule_versions",
        "profile_snapshots",
        "risk_assessments",
        "fraud_cases",
        "case_transitions",
        "analyst_decisions",
        "audit_events",
        "outbox_events",
        "outbox_delivery",
        "consumer_receipts",
        "idempotency_records",
        "experimental_evaluations",
        "evaluation_cases",
        "evaluation_case_transitions",
        "evaluation_feedback",
        "profile_learning_decisions",
        "profile_learning_evidence",
        "human_accounts",
        "human_sessions",
        "human_consumed_refresh",
        "human_login_throttle",
    }
)
_ALL_TABLES = _TABLES | {"alembic_version"}

_API_READ = _TABLES - {"outbox_delivery", "consumer_receipts"}
_API_INSERT = {
    "customers",
    "transactions",
    "profiles",
    "profile_revisions",
    "profile_observations",
    "audit_events",
    "outbox_events",
    "outbox_delivery",  # Invoker-rights trigger on outbox_events.
    "idempotency_records",
    "experimental_evaluations",
    "evaluation_cases",
    "evaluation_case_transitions",
    "evaluation_feedback",
    "profile_learning_decisions",
    "profile_learning_evidence",
    "human_sessions",
    "human_consumed_refresh",
    "human_login_throttle",
}
_API_UPDATE = {"profiles", "evaluation_cases", "human_sessions", "human_login_throttle"}
type RuntimeKind = Literal["api", "worker", "operator"]
type GrantSets = tuple[Set[str], Set[str], Set[str], Set[str]]


def _identifier(name: str) -> str:
    if not _NAME.fullmatch(name):
        raise ValueError("database identifiers must be lowercase ASCII names")
    return f'"{name}"'


def _verify_column_grants(
    connection: Connection, schema: str, role: str, kind: RuntimeKind, allowed: GrantSets
) -> None:
    """Table ACL checks alone do not reveal column-level grants."""
    for privilege, index in (("SELECT", 0), ("INSERT", 1), ("UPDATE", 2), ("REFERENCES", None)):
        for table in _ALL_TABLES:
            if index is not None and table in allowed[index]:
                continue
            if kind == "operator" and table == "human_sessions" and privilege == "UPDATE":
                for column in inspect(connection).get_columns(table, schema=schema):
                    name = column["name"]
                    actual = connection.scalar(
                        text("SELECT has_column_privilege(:role, :table, :column, 'UPDATE')"),
                        {"role": role, "table": f"{schema}.{table}", "column": name},
                    )
                    if actual is not (name == "revoked_at"):
                        raise ValueError("operator session update permissions are unsafe")
            elif connection.scalar(
                text("SELECT has_any_column_privilege(:role, :table, :privilege)"),
                {"role": role, "table": f"{schema}.{table}", "privilege": privilege},
            ):
                raise ValueError("runtime role has an unexpected column privilege")


def verify_runtime_role(connection: Connection, kind: RuntimeKind) -> None:
    """Fail startup if a runtime login has owner powers or unexpected grants."""
    schema = connection.scalar(text("SELECT current_schema()"))
    role = connection.scalar(text("SELECT current_user"))
    database = connection.scalar(text("SELECT current_database()"))
    if not isinstance(schema, str) or schema == "public" or not isinstance(role, str):
        raise ValueError("runtime requires a dedicated schema")
    if not isinstance(database, str):
        raise ValueError("runtime database is unavailable")
    if set(inspect(connection).get_table_names(schema=schema)) != _ALL_TABLES:
        raise ValueError("runtime schema differs from the reviewed grant plan")
    owners = connection.execute(
        text(
            "SELECT pg_get_userbyid(d.datdba), "
            "(SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=:schema) "
            "FROM pg_database d WHERE d.datname=current_database()"
        ),
        {"schema": schema},
    ).one()
    if role in owners:
        raise ValueError("runtime login cannot own the database or schema")
    attributes = connection.execute(
        text(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, "
            "EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid) "
            "FROM pg_roles r WHERE rolname=:role"
        ),
        {"role": role},
    ).one()
    if any(attributes):
        raise ValueError("runtime login has elevated attributes or role membership")
    for privilege, expected in (("CONNECT", True), ("CREATE", False), ("TEMP", False)):
        actual = connection.scalar(
            text("SELECT has_database_privilege(:role, :database, :privilege)"),
            {"role": role, "database": database, "privilege": privilege},
        )
        if actual is not expected:
            raise ValueError("runtime database privilege mismatch")
    if connection.scalar(
        text("SELECT has_schema_privilege(:role, :schema, 'CREATE')"),
        {"role": role, "schema": schema},
    ):
        raise ValueError("runtime login can create schema objects")
    if not connection.scalar(
        text("SELECT has_schema_privilege(:role, :schema, 'USAGE')"),
        {"role": role, "schema": schema},
    ):
        raise ValueError("runtime login cannot use the dedicated schema")
    writable = connection.scalar(
        text(
            "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
            "AND nspname <> 'information_schema' "
            "AND has_schema_privilege(:role, nspname, 'CREATE'))"
        ),
        {"role": role},
    )
    if writable:
        raise ValueError("runtime login can create objects in another schema")
    privilege_sets = {
        "api": (_API_READ, _API_INSERT, _API_UPDATE, {"human_consumed_refresh"}),
        "worker": (
            {"outbox_events", "outbox_delivery"},
            {"consumer_receipts"},
            {"outbox_events", "outbox_delivery"},
            set(),
        ),
        "operator": (
            {"human_accounts", "human_sessions"},
            {"human_accounts", "audit_events"},
            {"human_accounts"},
            set(),
        ),
    }[kind]
    for index, privilege in enumerate(("SELECT", "INSERT", "UPDATE", "DELETE")):
        for table in _ALL_TABLES:
            actual = connection.scalar(
                text("SELECT has_table_privilege(:role, :table, :privilege)"),
                {"role": role, "table": f"{schema}.{table}", "privilege": privilege},
            )
            if actual is not (table in privilege_sets[index]):
                raise ValueError("runtime table privilege mismatch")
    for privilege in ("TRUNCATE", "TRIGGER", "REFERENCES", "MAINTAIN"):
        for table in _ALL_TABLES:
            if connection.scalar(
                text("SELECT has_table_privilege(:role, :table, :privilege)"),
                {"role": role, "table": f"{schema}.{table}", "privilege": privilege},
            ):
                raise ValueError("runtime login has unsafe table privilege")
    _verify_column_grants(connection, schema, role, kind, privilege_sets)


def apply_runtime_grants(
    connection: Connection,
    *,
    schema: str,
    api_role: str,
    worker_role: str,
    operator_role: str,
) -> None:
    """Apply a reviewed privilege matrix inside the migration-owner transaction.

    The database must be dedicated: this revokes PUBLIC CONNECT/TEMP and schema
    access. The migrator owns the database/schema/objects and is never a runtime login.
    """
    schema_sql = _identifier(schema)
    roles = (api_role, worker_role, operator_role)
    role_sql = tuple(_identifier(role) for role in roles)
    if schema == "public" or len(set(roles)) != 3:
        raise ValueError("use a dedicated non-public schema and three distinct runtime roles")
    database = connection.scalar(text("SELECT current_database()"))
    owner = connection.scalar(text("SELECT current_user"))
    assert isinstance(database, str) and isinstance(owner, str)
    database_sql = _identifier(database)
    existing = set(inspect(connection).get_table_names(schema=schema))
    if existing != _ALL_TABLES:
        raise ValueError("schema table inventory differs from the reviewed grant plan")
    schema_owner = connection.scalar(
        text("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=:name"),
        {"name": schema},
    )
    db_owner = connection.scalar(
        text("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()")
    )
    if schema_owner != owner or db_owner != owner:
        raise ValueError("grant plan must run as the dedicated database/schema owner")
    role_rows = connection.execute(
        text(
            "SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
            "FROM pg_roles WHERE rolname=ANY(:names)"
        ),
        {"names": list(roles)},
    ).all()
    if len(role_rows) != 3 or any(
        not row.rolcanlogin or any(row[2:]) or row.rolname == owner for row in role_rows
    ):
        raise ValueError("runtime roles must exist and have no elevated role attributes")
    # Membership can permit SET ROLE even when inheritance is disabled.
    for role in roles:
        if connection.scalar(
            text(
                "SELECT EXISTS(SELECT 1 FROM pg_auth_members m "
                "JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=:role)"
            ),
            {"role": role},
        ):
            raise ValueError("runtime login roles must not belong to other roles")

    execute = connection.exec_driver_sql
    execute(f"REVOKE ALL ON DATABASE {database_sql} FROM PUBLIC")
    execute(f"REVOKE ALL ON DATABASE {database_sql} FROM {', '.join(role_sql)}")
    execute(f"REVOKE ALL ON SCHEMA {schema_sql} FROM PUBLIC")
    execute(f"REVOKE ALL ON SCHEMA {schema_sql} FROM {', '.join(role_sql)}")
    execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    execute(f"REVOKE CREATE ON SCHEMA public FROM {', '.join(role_sql)}")
    execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema_sql} FROM PUBLIC")
    execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema_sql} FROM {', '.join(role_sql)}")
    for role in role_sql:
        execute(f"GRANT CONNECT ON DATABASE {database_sql} TO {role}")
        execute(f"GRANT USAGE ON SCHEMA {schema_sql} TO {role}")

    def grant(privilege: str, tables: set[str] | frozenset[str], role: str) -> None:
        qualified = ", ".join(f"{schema_sql}.{_identifier(table)}" for table in sorted(tables))
        execute(f"GRANT {privilege} ON {qualified} TO {role}")

    grant("SELECT", _API_READ, role_sql[0])
    grant("INSERT", _API_INSERT, role_sql[0])
    grant("UPDATE", _API_UPDATE, role_sql[0])
    grant("DELETE", {"human_consumed_refresh"}, role_sql[0])
    grant("SELECT", {"outbox_events", "outbox_delivery"}, role_sql[1])
    grant("UPDATE", {"outbox_events", "outbox_delivery"}, role_sql[1])
    grant("INSERT", {"consumer_receipts"}, role_sql[1])
    grant("SELECT", {"human_accounts", "human_sessions"}, role_sql[2])
    grant("INSERT", {"human_accounts", "audit_events"}, role_sql[2])
    grant("UPDATE", {"human_accounts"}, role_sql[2])
    execute(f"GRANT UPDATE (revoked_at) ON {schema_sql}.human_sessions TO {role_sql[2]}")

    expected: tuple[GrantSets, GrantSets, GrantSets] = (
        (_API_READ, _API_INSERT, _API_UPDATE, {"human_consumed_refresh"}),
        (
            {"outbox_events", "outbox_delivery"},
            {"consumer_receipts"},
            {"outbox_events", "outbox_delivery"},
            set(),
        ),
        (
            {"human_accounts", "human_sessions"},
            {"human_accounts", "audit_events"},
            {"human_accounts"},
            set(),
        ),
    )
    kinds: tuple[RuntimeKind, RuntimeKind, RuntimeKind] = ("api", "worker", "operator")
    for role, kind, allowed in zip(roles, kinds, expected, strict=True):
        for privilege in (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "TRUNCATE",
            "TRIGGER",
            "REFERENCES",
            "MAINTAIN",
        ):
            for table in _ALL_TABLES:
                actual = connection.scalar(
                    text("SELECT has_table_privilege(:role, :table, :privilege)"),
                    {"role": role, "table": f"{schema}.{table}", "privilege": privilege},
                )
                permitted = (
                    table in allowed[("SELECT", "INSERT", "UPDATE", "DELETE").index(privilege)]
                    if privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
                    else False
                )
                if actual is not permitted:
                    raise ValueError("runtime role has an unexpected effective table privilege")
        for target, privilege, allowed_access in (
            (schema, "CREATE", False),
            (schema, "USAGE", True),
        ):
            if (
                connection.scalar(
                    text("SELECT has_schema_privilege(:role, :target, :privilege)"),
                    {"role": role, "target": target, "privilege": privilege},
                )
                is not allowed_access
            ):
                raise ValueError("runtime role has an unexpected schema privilege")
        for privilege, allowed_access in (("CREATE", False), ("TEMP", False), ("CONNECT", True)):
            if (
                connection.scalar(
                    text("SELECT has_database_privilege(:role, :database, :privilege)"),
                    {"role": role, "database": database, "privilege": privilege},
                )
                is not allowed_access
            ):
                raise ValueError("runtime role has an unexpected database privilege")
        writable_schemas = connection.execute(
            text(
                "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
                "AND nspname <> 'information_schema' "
                "AND has_schema_privilege(:role, nspname, 'CREATE')"
            ),
            {"role": role},
        ).all()
        if writable_schemas:
            raise ValueError("runtime role has CREATE on a schema")
        _verify_column_grants(connection, schema, role, kind, allowed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply grants to a dedicated migrated database")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--api-role", required=True)
    parser.add_argument("--worker-role", required=True)
    parser.add_argument("--operator-role", required=True)
    args = parser.parse_args()
    settings = Settings()
    if settings.database_url is None:
        parser.error("FRAUDLENS_DATABASE_URL for the migration owner is required")
    engine = create_database_engine(settings.database_url.get_secret_value())
    try:
        with engine.begin() as connection:
            apply_runtime_grants(
                connection,
                schema=args.schema,
                api_role=args.api_role,
                worker_role=args.worker_role,
                operator_role=args.operator_role,
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
