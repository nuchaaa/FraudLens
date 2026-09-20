Continue FraudLens from the completed Phase 2 persistence checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md and development.md.
Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; backend/app is framework-free domain; backend/api
is HTTP; backend/adapters contains infrastructure.

Completed: Phase 0/1 plus 14 PostgreSQL business tables, typed repositories,
explicit-commit atomic UoW, immutable history triggers, profile/case concurrency,
snapshot provenance, durable outbox storage and scoped idempotency primitives.
Migration head: 0003_history_guards. No transaction API, authentication, ML model,
SHAP or frontend exists yet. Outbox dispatch is not implemented.

Validation: 131 tests passed, none skipped, 96% coverage on PostgreSQL 17.10.
Ruff and strict mypy passed; pip-audit found no known vulnerabilities; package
builds and Compose configuration passed. Two upstream deprecation warnings remain.
Docker execution and remote CI are unverified. No known failing tests.

PostgreSQL is left running without TCP on owner-only socket /private/tmp, port
55439. Database: fraudlens_test. Cluster: ../../work/fraudlens-postgres/data from
the repository. See development.md for restart/stop. Sandboxed socket access may
require approved execution outside the sandbox; do not substitute SQLite.

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

Important files: backend/adapters/database/{models,uow,profiles,cases,idempotency,
assessments,history,transactions,codec}.py; backend/app/shared/{ports,errors}.py;
backend/app/transaction/idempotency.py; infra/migrations/versions; tests/integration;
docs/adr/ADR-007-persistence-consistency.md.

Next: Phase 3 transaction submission/retrieval use cases and FastAPI routes.
Acquire the authenticated principal's idempotency lock before business writes;
canonicalize requests; replay matching stored responses; reject changed bodies
and duplicate transaction IDs explicitly. Commit transaction, audit, outbox event
and stored response atomically. Add authorization and FastAPI/PostgreSQL tests.
Do not fabricate risk predictions or expose unprotected business writes.

Profile repositories check transaction facts, not analyst legitimacy. Gate
orchestration, trusted enrollment, low-weight admission and corrections remain.
Transactions are immutable; plan status evolution explicitly. Update all three
checkpoint files before ending each session. Never fabricate research metrics.
