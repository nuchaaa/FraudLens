# FraudLens project status

Current checkpoint: **Phase 3 — Authenticated synthetic transaction API implemented and verified.**
Next phase: **Phase 4 — Customer behavior application workflows.**
The product is not complete. Intake does not evaluate fraud risk or admit profile data.

## Completed phases and capabilities

- [x] Phase 0: Python 3.13/uv foundation, FastAPI, configuration, Docker/Compose and CI definitions.
- [x] Phase 1: pure domain, robust profiles, initial safe gate, cases, risk strategies and ports.
- [x] Phase 2: 14 PostgreSQL tables, typed repositories, explicit-commit atomic UoW,
  immutable history, profile/case concurrency, snapshots, outbox and idempotency storage.
- [x] Phase 3: framework-free transaction submission/retrieval and synthetic customer enrollment.
- [x] POST /api/v1/transactions and GET /api/v1/transactions/{transaction_id}.
- [x] Admin-only POST /api/v1/customers creates customer/audit records, never trusted observations.
- [x] Expiring high-entropy bearer service credentials stored as SHA-256 digests;
  admin/service/analyst roles and explicit customer scope, with fail-closed configuration.
- [x] Canonical request hashing, authenticated principal/key locking before writes,
  exact stored 201 replay, changed-body conflicts and explicit duplicate-ID conflicts.
- [x] Atomic transaction, authenticated audit, TransactionReceived outbox and response commit.
- [x] Decimal-string money, aware timestamps, strict fields, bounded 16 KiB bodies,
  sanitized errors and no-store responses.
- [x] PostgreSQL-backed API tests, token rotation/revocation, rollback and concurrent request tests.
- [x] ADR-008, API setup/examples and updated architecture/runbook.

## Verification — 2026-09-20

- [x] **193 tests passed, 0 skipped, 2 upstream warnings; 97% combined branch/statement coverage.**
- [x] Real PostgreSQL 17.10, including migrations, immutable history and Phase 2 regressions.
- [x] API tests verify exact replay across app instances, scoped credentials/keys, changed-body
  conflicts, rollback at audit/outbox/response/commit stages and forced duplicate-ID insert races.
- [x] Ruff lint/format and strict mypy pass (59 backend files).
- [x] pip-audit reports no known vulnerabilities in unchanged locked dependencies.
- [x] Source/wheel builds and Compose configuration pass.
- [x] Alembic upgrade/check pass; unchanged migration head: 0003_history_guards.
- [x] Actual Uvicorn + PostgreSQL HTTP smoke passed: enrollment, submission, retrieval,
  exact replay, 401 authentication and 409 conflict. Temporary smoke schema/server cleaned up.
- [ ] Docker image build/start: still unverified; Docker engine unavailable.
- [ ] Remote CI: not pushed or executed.

No known failing tests. The two unsuppressed warnings remain upstream Starlette
httpx TestClient and AnyIO BlockingPortal deprecations. No model performance is claimed.

## Environment and commands

Repository: outputs/fraudlens in the original workspace. PyCharm .idea files are
preserved/ignored. Dependencies are unchanged. PostgreSQL remains running without TCP
on owner-only socket /private/tmp, port 55439; database fraudlens_test.
Binaries: /opt/homebrew/opt/postgresql@17/bin.
Cluster: ../../work/fraudlens-postgres/data from the repository.

```sh
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
```

See development.md for PostgreSQL restart/stop, expiring credential generation and API
examples. Set FRAUDLENS_API_PRINCIPALS before authenticated use; no actual credential
was committed or left configured by this session. Run .venv/bin/uvicorn backend.main:app
--reload --host 127.0.0.1 after configuration. Sandboxed PostgreSQL socket/shared-memory
access may require approved execution outside the sandbox. Tests require *_test and
create/remove their own schema; the migration smoke also upgrades the default schema.

## Important files

- backend/app/transaction/service.py: intake/retrieval/enrollment, canonical digest and atomic flow.
- backend/app/shared/security.py and errors.py: authorization and framework-free errors.
- backend/api/transactions.py, dependencies.py, errors.py, limits.py: HTTP boundary.
- backend/adapters/security.py: validated configured credential registry.
- backend/main.py and config.py: composition, database lifecycle and secret configuration.
- backend/adapters/database/uow.py: atomic UoW and explicit uniqueness conflict translation.
- backend/adapters/database/{models,profiles,cases,idempotency,assessments,history,transactions,codec}.py:
  previously verified persistence adapters.
- backend/app/profile/entities.py and gate.py: existing robust statistics and safe admission domain.
- tests/integration/test_transaction_api.py and tests/unit/test_api_security.py: Phase 3 tests.
- docs/adr/ADR-008-transaction-api-and-service-credentials.md and ADR-007-persistence-consistency.md.
- development.md, README.md and docs/architecture/README.md.

## Decisions, partial work and limitations

- Domain/application code stays framework-free. Repositories flush; only UoW commits.
  Matching replay checks current authorization first and returns without business writes.
- Service credentials are not human login/password authentication. Registry policy is
  read at startup: rotation/revocation requires restarting every process; expiry is
  checked per request. Keep principal UUID stable for rotation, never reuse for another identity.
- Human authentication/session lifecycle, distributed rate/time limits, restricted
  runtime database grants and deployment security review remain. Local synthetic demo only;
  remote deployment requires TLS. The configured DB owner can disable history triggers.
- Successful idempotency records have no retention/purge policy yet; failures are not cached.
- Transactions remain immutable including RECEIVED status. Evaluation needs separately
  derived state or an explicit append-only lifecycle, not silent historical mutation.
- Outbox storage exists; dispatch, claims/leases/retries and consumer deduplication do not.
- Profile repositories validate transaction facts, not analyst legitimacy. Customer
  enrollment adds no trusted observations. Trusted bootstrap/admission and gate orchestration
  still need application policies. Existing robust stats/windows must not be reimplemented.
- Gate thresholds remain uncalibrated. Cold start, low-weight admission, compromised
  confirmations, corrections/retractions and event-time leakage remain research debt.
- No feature engine, risk evaluation HTTP API, trained ML, SHAP, human login or frontend.
  Rules-only assessment provenance must be designed without inventing model metadata.

## Exact next tasks

1. Read this file, docs/PROJECT_SPECIFICATION.md, development.md and ADR-008; preserve Phase 3.
2. Begin Phase 4 by inspecting existing profile entities/gate/repositories/tests. Identify only
   missing application behavior; median/MAD/p95, short/long windows and snapshots already exist.
3. Specify cold-start/trusted-history provenance, per-currency as-of reads and event-time ordering
   before exposing profile application workflows. Raw intake or admin customer creation is not
   proof of legitimate behavior. Do not blindly admit received transactions.
4. Implement scoped profile retrieval and required history/statistics capabilities through ports;
   use versioned atomic persistence for any authorized profile changes.
5. Test missing/cold profiles, currency isolation, as-of boundaries, future-history exclusion,
   concurrency and exceptional-purchase baseline preservation using PostgreSQL where appropriate.
6. Keep ML/evaluation/outbox dispatch for their planned phases; never fabricate metrics.
7. Run checks and update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
