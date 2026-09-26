# ADR-023: Dedicated PostgreSQL runtime roles

Status: accepted for a locally verified Phase 15 database boundary, 2026-09-26.
This does not approve remote deployment.

## Context

The original local API, outbox worker and operator CLI connected as the migration
owner. The owner can alter tables and disable triggers, making immutable history
guards ineffective against a compromised process. Human login needs to read
account password hashes and write session state, while account provisioning must
remain outside the API. The worker needs queue state but no customer or identity
access. A dedicated PostgreSQL database and schema are necessary: inherited
permissions, PUBLIC grants or writable search-path schemas could defeat a table
grant matrix.

## Decision

Use four distinct **LOGIN** roles with no memberships or elevated attributes:
migrator (database/schema/object owner), API runtime, outbox worker and identity
operator. Their passwords come from deployment secret management, never source.
The migration owner applies `backend.adapters.database.grants` only after Alembic
has reached head. The grant plan requires a non-public schema, exact reviewed table
inventory and three separate runtime roles. It revokes PUBLIC database/schema/table
access, including temporary-table creation; revokes public-schema CREATE; then
grants only the reviewed matrix. Future migrations must rerun this plan. An unknown
table or unexpected effective privilege fails the grant transaction. The runtime
verifier also checks column-level privileges and denies access to Alembic's
version table, which is reserved for migration ownership.

The API can read the data needed by the existing use cases, insert transaction,
evaluation, learning, audit, outbox, idempotency and session evidence, and update
only current profile/case/session/throttle state. It cannot insert or update human
accounts, mutate immutable history, update delivery state, truncate tables, alter
schema or disable triggers. The operator can create/update accounts, revoke
sessions and append audit entries. Its session UPDATE grant covers only
`revoked_at`. The worker can read and update outbox/delivery state and insert
local receipts; it cannot read customer or human-account tables.

Production API startup and production worker/operator CLI commands verify their
effective database grants before operating. A production API without a database or
using owner credentials fails startup. Test dependency-injection factories bypass
this deployment check, but the real production entry point never injects one.
The current localhost Compose file still uses one owner credential and remains a
development-only topology.

Login used to lock `human_accounts` with `SELECT FOR UPDATE`, which PostgreSQL
requires UPDATE privilege to execute. Granting the API that privilege would let a
compromised API connection modify account policy. Login and operator changes now
share a transaction-scoped account advisory lock; login rereads both account
policy and password hash after acquiring it. Recovery during login therefore
rejects the old password without API account-write access.

## Verification and limits

An integration test creates a fresh `*_test` database and real password-authenticated
login roles, migrates as its owner, applies grants, and connects separately as each
runtime role. It proves expected workflows and denied DDL, trigger disabling,
history changes, account provisioning, cross-role reads, temporary tables and
unsafe operator session updates. A production-mode FastAPI test exercises the
restricted API login, trusted Host, secure cookies and hidden docs. The test drops
only its temporary database and roles.

These grants constrain a compromised database login, not a database superuser or
host owner. The API can still read substantial customer data within its schema;
customer isolation remains application authorization rather than PostgreSQL row
security. The operator CLI accepts an asserted audit UUID; this is not human
identity verification. Role grants must be checked in the actual deployed database
after every migration or credential change. TLS/proxy trust, edge limits, MFA,
verified recovery, Docker runtime and independent security review remain open.

Rejected: sharing the schema owner, granting API UPDATE on human accounts for row
locks, using SECURITY DEFINER as a broad privilege escape, or treating a local
grant test as a deployment assessment.

References: [PostgreSQL schema privileges](https://www.postgresql.org/docs/17/ddl-schemas.html),
[GRANT](https://www.postgresql.org/docs/17/sql-grant.html),
[SELECT locking privilege](https://www.postgresql.org/docs/17/sql-select.html).
