# Session log

## 2026-09-19 — Foundation and domain checkpoint

- Inspected empty workspace; created separate repository under outputs, preserved
  original specification and left the parent repository untouched.
- Implemented locked Python environment, FastAPI liveness/settings/logging,
  PostgreSQL/Alembic foundation, Docker/Compose and CI definitions.
- Implemented pure domain records, robust rolling profiles, safe admission gate,
  immutable case transitions, risk/decision strategies, model/repository/event
  contracts, audit/feedback values and in-process event publisher.
- Added regression tests for exceptional purchases, fraud exclusion, unverified
  escalating activity, confirmed gradual drift, lifecycle and input invariants.
- Added architecture documentation, six ADRs and research protocol without metrics.
- Verification: 93 passed, 1 PostgreSQL skip, 90% coverage; Ruff/mypy clean;
  dependency audit found no known vulnerabilities; distributions built; Compose
  validated; offline migration SQL rendered; actual HTTP liveness returned 200.
- Fixed initial missing-README packaging timing and Decimal inference issue.
  Two upstream test dependency deprecation warnings remain unsuppressed.
- Docker runtime unavailable; Docker app launch unsuccessful. Container and live
  PostgreSQL remain unverified. No remote CI, trained model or metric claims.
- Next: verify disposable PostgreSQL, then Phase 2 tables, repositories, atomic UoW
  and PostgreSQL transaction/concurrency integration tests.


## 2026-09-19/20 — Phase 2 persistence and completed continuation checkpoint

- Resumed the interrupted persistence work without recreating Phase 0/1. Found native
  PostgreSQL 17.10 and initialized a dedicated synthetic test cluster. Sandbox shared
  memory/socket restrictions required approved execution outside the sandbox.
- Added 14 typed business tables, two Alembic revisions, complete repository ports/
  adapters, explicit-commit UoW, immutable history and serialized case/profile changes.
- Added scoped idempotency locks/records, exact snapshot encoding and durable outbox
  storage with publication metadata. No dispatcher or HTTP business API claimed.
- Tests verified record round trips, commit/default rollback/failed-commit rollback,
  concurrent profile/idempotency writes, immutable SQL history, association constraints
  and migration upgrade/downgrade with metadata matching.
- Final verification: 131 passed, zero skipped, 96% coverage; Ruff/mypy clean;
  dependency audit reports no known vulnerabilities; package builds and Compose
  configuration pass. Two upstream dependency deprecations remain.
- Updated README/architecture/ADRs, added ADR-007 and development runbook, refreshed
  all continuation files. Preserved and ignored user PyCharm .idea settings.
- Test cluster left running with no TCP listener and owner-only Unix socket. Docker
  runtime and remote CI still unverified. No trained model or predictive metrics.
- Next: Phase 3 authenticated synthetic transaction submission/retrieval and HTTP
  idempotency, with atomic audit/outbox effects and FastAPI/PostgreSQL tests.

## 2026-09-20 — Phase 3 authenticated transaction intake

- Added framework-free submission/retrieval and controlled synthetic customer enrollment;
  FastAPI routes require expiring hashed bearer service credentials and role/customer scopes.
- Canonical principal-scoped idempotency locks precede business writes. Successful responses
  replay exactly from PostgreSQL; changed requests and duplicate IDs return explicit conflicts.
- Transaction, authenticated audit, TransactionReceived event and completed response commit
  atomically. Failed audit/outbox/response/commit tests leave no partial records.
- Added bounded body sizes, strict Decimal/time/identifier validation, sanitized errors,
  no-store responses, registry rotation/revocation checks and database lifecycle composition.
- Verified concurrent retries and forced duplicate-ID insertion races against PostgreSQL,
  exact replay across app instances, scope enforcement and no automatic profile admission.
- Final suite: 193 passed, zero skipped, 97% coverage; two existing upstream deprecations.
  Ruff/format/strict mypy pass; pip-audit finds no known vulnerabilities; distributions,
  Compose configuration and Alembic upgrade/schema checks pass. No schema/dependency changes.
- Actual local Uvicorn/PostgreSQL smoke passed enrollment, submit, retrieve, exact retry,
  authentication and conflict checks; temporary server and smoke schema were removed.
- Updated README, architecture, runbook, ADR-008 and all checkpoint files. Credentials
  remain fail-closed until explicitly configured; no actual token was committed.
- PostgreSQL remains running on the owner-only Unix socket with no TCP listener.
  Docker runtime and remote CI remain unverified. No predictive metrics claimed.
- Next: Phase 4 profile application workflows, beginning with missing trusted-history,
  cold-start, per-currency as-of and leakage policies; preserve existing robust domain work.

## 2026-09-20 — Phase 4 versioned customer behavior reads

- Reused existing robust profile/window/gate domain; added framework-free scoped retrieval,
  explicit cold/insufficient states, Decimal summaries, hour histograms/typical hours,
  admitted observation frequency and known recipients.
- Added authenticated profile GET route with strict cutoffs, required version pinning for
  explicit historical reads and honest unavailable-history errors. No new admission endpoint.
- Added profile_revisions and migration 0004. PostgreSQL captures head metadata atomically,
  seals committed admission sets using full transaction identity/physical xmin, and protects
  revisions from mutation. Upgrade preserves existing observations and captures current
  heads only, rather than inventing old metadata. Default test DB is upgraded.
- Wrote ADR-009 defining event-time vs knowledge-version semantics and reviewed-source
  bootstrap requirements. Current provenance remains repository admission, not verified
  analyst legitimacy. Public intake/customer enrollment never trains profiles.
- Tested currency/window boundaries, backdated later admissions, policy version preservation,
  DST, missing/cold profiles, quarantine baseline preservation, revision rollback/immutability,
  concurrent readers/writers and migration of populated legacy heads.
- Final verification: 227 passed, no skips, 97% coverage; Ruff/format/strict mypy pass.
  pip-audit reports no known vulnerabilities; package/Compose/Alembic checks pass.
  Two existing upstream deprecations remain. Initial response self-annotation issue fixed.
- Actual Uvicorn/PostgreSQL profile smoke passed cold start, populated pinned median/MAD/p95,
  authentication and cutoff validation. Temporary server/schema removed; native PostgreSQL
  remains running without TCP. Docker execution and remote CI remain unverified.
- Updated all checkpoint files, runbook, architecture and README. No predictive metrics.
- Next: Phase 5 shared versioned feature engine, explicit missing-history/zero-MAD behavior,
  cutoff-safe activity queries and proof against candidate/future/late-data leakage.
