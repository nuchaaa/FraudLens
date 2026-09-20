Continue FraudLens from completed Phase 3. Read PROJECT_STATUS.md first, then
docs/PROJECT_SPECIFICATION.md, development.md and docs/adr/ADR-008-transaction-api-and-service-credentials.md.
Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; backend/app is framework-free domain/application,
backend/api is HTTP, backend/adapters is infrastructure.

Completed: Phases 0–3. PostgreSQL persistence has 14 business tables, typed repositories,
atomic explicit-commit UoW, immutable history, concurrency, snapshots and durable outbox.
Phase 3 adds authenticated POST/GET /api/v1/transactions and admin POST /api/v1/customers,
expiring hashed service credentials with roles/customer scopes, canonical idempotency,
exact durable replay, conflict handling and atomic transaction/audit/outbox/response writes.
Migration head remains 0003_history_guards. Intake stays RECEIVED; no risk scores,
profile admission, ML, SHAP, human login, frontend or outbox dispatcher exists.

Validation: 193 tests passed, none skipped, 97% coverage on PostgreSQL 17.10.
Ruff, strict mypy, pip-audit, package builds, Compose configuration and Alembic checks
passed. Actual Uvicorn/PostgreSQL HTTP smoke passed. Two upstream deprecations remain.
Docker execution and remote CI are unverified; no known failing tests.

Database remains running without TCP: owner-only socket /private/tmp, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data from repository.
See development.md for restart/stop and API credential setup. Sandboxed socket access
may require approved execution outside the sandbox. Never substitute SQLite.
FRAUDLENS_API_PRINCIPALS is empty by default: business requests fail closed. Credential
rotation preserves principal UUID; policy changes require restarting every API process.

Commands from repository root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline

Important files: backend/app/transaction/service.py; backend/app/shared/security.py;
backend/api/{transactions,dependencies,errors,limits}.py; backend/adapters/security.py;
backend/app/profile/{entities,gate}.py; backend/adapters/database/{profiles,uow,models}.py;
tests/integration/test_transaction_api.py; tests/unit/test_api_security.py.

Next: Phase 4 — Customer behavior. First inspect existing profile domain, gate,
repositories and tests; median/MAD/p95, short/long windows and snapshots already exist.
Specify missing trusted-history/cold-start policies and per-currency as-of behavior,
then implement scoped profile retrieval/application workflows through ports. Test
history cutoffs, future-data leakage, currency isolation, concurrency and preservation
of normal baselines after exceptional purchases. Customer enrollment and raw transaction
intake do not establish legitimacy; do not automatically admit their data to profiles.

Transactions remain immutable; plan separate evaluation state or append-only lifecycle.
Trusted admission/gate orchestration, low-weight updates, compromised confirmations and
corrections remain unresolved; thresholds are uncalibrated. Human authentication,
runtime database grants and deployment hardening remain future work.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate research metrics.
