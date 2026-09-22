# ADR-020: Analyst console and scoped read model

Status: accepted, Phase 14 checkpoint, 2026-09-22.

## Context

The existing HTTP API retrieved transactions, evaluations and cases only by known UUID.
A usable analyst worklist and factual overview cannot be built by guessing identifiers or
inventing client-side metrics. The current service credentials are suitable for localhost
demonstrations but are not human sessions. Experimental results can be absent, contain
insufficient evidence, and are always uncalibrated and production-ineligible.

## Decision

Add a framework-free console read-model port and PostgreSQL adapter. Two authenticated,
read-only endpoints expose an exact scope-filtered summary and a descending keyset-paginated
worklist. The worklist joins immutable transactions to their latest retained experimental
evaluation and case state without modifying any history. Its opaque cursor pins the last
transaction event time and UUID; pages contain at most 100 rows. Empty customer scope returns
empty data rather than leaking existence. All responses use `no-store`.

Summary counts use the same customer scope. “Today” means transaction event timestamps from
UTC midnight through the summary timestamp, not ingestion volume. High-risk count and
suspicious amount use the latest retained evaluation per transaction and only HIGH/CRITICAL
experimental levels. Case counts derive from retained transitions/feedback. The response
states `NO_PRODUCTION_MODEL` and `experimental_results_calibrated=false`; it does not invent
model health, precision, recall or missing risk scores.

Build the console with React, TypeScript and Vite. It includes overview, transaction/case
worklist and details, robust profile lookup, model-evidence limitations and system boundaries.
Review writes reuse the existing API, exact expected version and fresh idempotency key, behind
an explicit confirmation dialog. The UI repeats that feedback does not execute actions or
authorize learning. It does not expose profile-learning controls: those require an independent
admin and multi-case evidence that one browser credential cannot safely collapse.

The pasted bearer credential is held only in React memory. It is never included in source,
URLs, localStorage or sessionStorage and is cleared by refresh/disconnect. Vite proxies to the
localhost API during development. The container serves static assets through nginx and proxies
same-origin API calls, with a restrictive CSP and no external font/assets. This remains an
operator-pasted service credential, not human authentication; remote deployment is prohibited.

## Consequences

The UI can demonstrate retained evidence without a fake dataset or divergent risk logic.
Scoped list/summary tests run on PostgreSQL; UI tests cover connection/error truthfulness,
and the production bundle is type-checked and built. Compose and CI now include the frontend.

No aggregate audit endpoint, model registry, human identity/session, server-side UI session,
saved filters, global case-only pagination or deterministic demo seed exists yet. The case page
filters the currently loaded transaction worklist, so its label says so. An analyst credential
can review but cannot evaluate transactions; a service credential can evaluate but cannot
review. Phase 15 must implement human authentication/RBAC before remote or production use.

Rejected: storing bearer tokens in browser storage, shipping a default credential, embedding
mock metrics, recomputing evaluations in JavaScript, placing SQL in route handlers, offset
pagination, or weakening existing experimental/profile-learning authorization for demo ease.
