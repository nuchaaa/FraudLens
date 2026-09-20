# FraudLens project status

Current checkpoint: **Phase 2 — Persistence implemented and verified on PostgreSQL.**
Next phase: **Phase 3 — Transaction API and durable request idempotency.**
The product is not complete. HTTP currently exposes liveness only.

## Completed phases

- [x] Phase 0: Python 3.13/uv lockfile, FastAPI foundation, configuration, quality tools,
  Docker/Compose definitions, CI definition, README and initial architecture/research docs.
- [x] Phase 1: pure Python domain, robust profiles, safe admission gate, strict cases,
  risk strategies, versioned contracts, audit/feedback/events and invariant tests.
- [x] Phase 2: 14 PostgreSQL business tables, typed SQLAlchemy repositories and migrations.
- [x] Explicit-commit context-managed UoW; rollback on missing commit and failures.
- [x] Decimal/UUID/timezone-aware round trips and versioned immutable profile snapshots.
- [x] Expected profile versions plus row locks; append-only observation storage.
- [x] Database-validated case transitions and append-only audit/assessment/feedback/history.
- [x] Durable outbox insertion and attempts/publication metadata with immutable envelopes.
- [x] Scoped completed-request records, digest conflicts and transaction-scoped idempotency locks.
- [x] Genuine PostgreSQL integration tests, migration upgrade/downgrade and metadata checks.
- [x] Local development runbook, updated architecture and ADR-007.

## Verification — 2026-09-20

- [x] **131 passed, 0 skipped, 2 upstream warnings; 96% combined branch/statement coverage.**
- [x] Includes concurrency, commit/rollback, failed deferred constraints, record round trips,
  direct SQL history mutation rejection, snapshot association and model-feature consistency.
- [x] Ruff lint and formatting pass; strict mypy passes for 52 backend files.
- [x] pip-audit: no known vulnerabilities in unchanged locked dependencies.
- [x] Source/wheel builds pass; Compose configuration validates.
- [x] PostgreSQL 17.10 native server verified. Migration head: `0003_history_guards`.
- [x] HTTP liveness tests pass; stage now reports `persistence-foundation`.
- [ ] Docker image build/start remains unverified: Docker engine unavailable.
- [ ] Remote GitHub Actions run: no remote push/workflow execution performed.

No known failing tests. Unsuppressed warnings concern Starlette TestClient's httpx
support and AnyIO BlockingPortal. Initial formatting issues were fixed. Tests are
real database tests, not SQLite replacements. No model performance is claimed.

## Environment and important commands

Repository: `outputs/fraudlens` in the original workspace. PyCharm `.idea/` files are
preserved and ignored. Dependencies remain unchanged; `.venv` is available.
Native PostgreSQL binaries: `/opt/homebrew/opt/postgresql@17/bin`.
Disposable cluster: `../../work/fraudlens-postgres/data` from the repository.
The cluster is left running without TCP, using owner-only Unix socket permissions.

```sh
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

See `development.md` for restart/stop and another-machine instructions. Sandboxed
execution may need approval for PostgreSQL shared memory/socket access. Test database
names must end in `_test`. The suite creates and removes only its generated schema;
the migration smoke also upgrades the default schema of the supplied test database.

## Important implementation files

- `backend/adapters/database/models.py`: typed mappings and relational constraints.
- `backend/adapters/database/uow.py`: explicit commit/rollback and domain port factory.
- `backend/adapters/database/profiles.py`, `cases.py`: versioned/append-only aggregates.
- `backend/adapters/database/assessments.py`, `history.py`, `transactions.py`: repositories.
- `backend/adapters/database/idempotency.py`, `codec.py`: scoped locks and snapshot encoding.
- `backend/app/shared/ports.py`, `errors.py`: framework-free repository/UoW contracts.
- `backend/app/transaction/idempotency.py`: validated completed-request record.
- `infra/migrations/versions/0002_persistence_business_persistence.py`: business schema.
- `infra/migrations/versions/0003_history_guards.py`: immutable history/case/version triggers.
- `tests/integration/`: actual PostgreSQL tests and isolated schema fixture.
- `docs/adr/ADR-007-persistence-consistency.md`, `development.md`: decisions and runbook.

## Architecture decisions and limitations

- Repositories flush; only UoW commits. Let repository failures exit the UoW so the
  whole operation rolls back. No publication before the durable commit.
- Acquire scoped idempotency locks BEFORE business effects. Matching stored responses
  must short-circuit execution; different request hashes raise IdempotencyConflict.
- Expired observations remain persisted; profile reads return the active window and
  exclude admissions newer than the captured head version.
- Profile repositories validate transaction facts, not analyst legitimacy. Trusted
  enrollment, authorized feedback and gate orchestration remain application work.
- History triggers reject ordinary SQL mutation; privileged DB owners can disable
  them. Restricted runtime grants and authentication/RBAC remain to be implemented.
- Transactions are currently immutable including status. Model provenance is immutable;
  promotion/status workflows and transaction lifecycle must be explicitly designed.
- Outbox pending reads do not claim work. Background dispatch/leases/retries and
  consumer deduplication remain future work. No exactly-once claim.
- No transaction/risk HTTP API, authentication, trained model, SHAP or frontend yet.
- Rules-only assessment provenance must be designed before serving rules-only risk;
  current assessments reference real model metadata, not a fabricated model artifact.
- Uncalibrated profile/decision thresholds, cold-start enrollment, low-weight admission,
  compromised confirmations and correction/retraction replay remain research debt.

## Exact next tasks

1. Read this status, the preserved specification and `development.md`; do not rebuild Phase 2.
2. Start Phase 3: transaction submission/retrieval use cases depending on domain ports.
3. Add validated HTTP request/response models, canonical request hashing, authenticated
   principal scope, replay of stored response/status and conflict mapping.
4. Atomically persist transaction, audit, TransactionReceived outbox event and successful
   idempotent response. Handle duplicate transaction IDs with different keys explicitly.
5. Do not expose unprotected business endpoints or fabricate fraud scores before the
   feature/rule/model phases. Plan a controlled synthetic customer enrollment path.
6. Add FastAPI + PostgreSQL integration tests for successful submission, replay,
   changed-body conflict, duplicate IDs, invalid inputs, authorization and concurrency.
7. Run checks; update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
