# ADR-002: Hexagonal architecture

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

Fraud policy must remain testable without an HTTP server, database or ML framework.

## Decision

Keep backend/app pure Python. HTTP, persistence, ML and event adapters implement typed ports.

## Alternatives

Active Record domain models; ORM entities in endpoints.

## Why alternatives were rejected

Both couple policy tests to infrastructure and make model substitution harder.

## Consequences

Some mapping code is intentional. An AST dependency test protects the boundary. Application services and full unit-of-work lifecycle arrive with persistence.
