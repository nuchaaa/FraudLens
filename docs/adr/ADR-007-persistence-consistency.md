# ADR-007: Persistence consistency and historical records

Status: implemented in Phase 2.

## Context

Historical assessments must survive profile changes, concurrent updates must not
overwrite each other, and failed transactions must not leave orphaned outbox events.

## Decision

Use typed SQLAlchemy mappings behind domain repository protocols. One explicit-commit
unit of work owns the session; every other exit rolls back. Repositories flush only.
Profile heads use row locks plus expected versions. Observations and case transitions
are append-only; expired observations remain stored outside the active window.

Keep immutable snapshot JSON with Decimal strings and schema version 1. Deferred
composite foreign keys bind assessment/snapshot identity and enforce customer,
currency and model-feature associations. PostgreSQL triggers protect historical
records against UPDATE/DELETE/TRUNCATE and validate sequential case transitions.

Use transaction-scoped advisory locks for `(principal_id, idempotency_key)` before
business writes. Store the canonical request digest and completed response in the
same commit as business data and outbox events. A caller must return a matching
stored response immediately, before creating additional effects.

## Alternatives

- Automatic commit on successful context exit.
- Optimistic updates without row locking or version predicates.
- Python-only immutability checks.
- An in-memory idempotency dictionary or a separate cache service.

## Why alternatives were rejected

Implicit commits make incomplete workflows easier to persist accidentally. Unchecked
updates lose concurrent admissions. Python-only guards cannot reject direct SQL
edits. An in-memory cache loses deduplication across restarts; a separate service
adds infrastructure without solving atomicity with PostgreSQL.

## Consequences

PostgreSQL integration tests are mandatory; SQLite is not equivalent. Cross-module
writes commit together. Application workflows still must enforce authorization,
label provenance and safe-gate decisions. Triggers protect ordinary writes, not a
privileged administrator who can disable them. Production must separate schema
owner and runtime roles. Model promotion, transaction status evolution and audited
corrections need explicit use cases. Outbox dispatch and consumer deduplication
remain future work; no exactly-once delivery claim is made.
