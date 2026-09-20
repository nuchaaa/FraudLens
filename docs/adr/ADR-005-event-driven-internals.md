# ADR-005: Internal events and transactional outbox

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

Feedback, audit and profiling must be decoupled without losing events across process crashes.

## Decision

Define immutable domain events and an in-process publisher port. Implement durable outbox writes atomically with business updates in PostgreSQL in Phase 13.

## Alternatives

Kafka immediately; publish before database commit; untracked background tasks.

## Why alternatives were rejected

Kafka is unnecessary infrastructure. Publishing before commit or using volatile background tasks can lose or invent side effects.

## Consequences

The current synchronous adapter is not durable. Handler exceptions propagate. Future dispatch is at-least-once; handlers need event-ID deduplication. Never promise exactly-once delivery.


Phase 2 update: durable outbox insertion, attempts/publication metadata and atomic business/outbox commits are implemented. Background dispatch, leases and consumer deduplication remain Phase 13 work.
