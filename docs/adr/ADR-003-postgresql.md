# ADR-003: PostgreSQL

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

Assessments, audit and outbox events must be stored atomically with concurrency control.

## Decision

Use PostgreSQL, SQLAlchemy 2 and Alembic. Financial amounts target NUMERIC(18,2); timestamps target TIMESTAMPTZ.

## Alternatives

SQLite as production database; MongoDB; separate stores per module.

## Why alternatives were rejected

SQLite cannot verify PostgreSQL concurrency behavior. Other stores add consistency and operational complexity without a demonstrated need.

## Consequences

PostgreSQL tests require a real disposable server. Phase 0 migration is only a foundation marker. Business tables, constraints and repository adapters are Phase 2.
