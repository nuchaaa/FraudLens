# ADR-001: Modular monolith

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

A portfolio research system needs clear ownership without distributed operations.

## Decision

Use a single deployable backend with transaction, profile, features, rules, ML, risk, cases, feedback and audit modules.

## Alternatives

Microservices; a single unstructured CRUD service.

## Why alternatives were rejected

Microservices add distributed consistency and deployment costs; unstructured code obscures fraud invariants.

## Consequences

Modules communicate through application services and ports. Database transactions stay local. Extraction remains possible but is not an initial goal.
