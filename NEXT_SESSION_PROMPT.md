Continue FraudLens. Read PROJECT_STATUS.md first and docs/PROJECT_SPECIFICATION.md.
Do not redo completed work. Repository: outputs/fraudlens in the original workspace.

Goal: explainable behavioral fraud detection with safe adaptive customer profiles.
Architecture: modular monolith; backend/app is pure Python domain, backend/api is
HTTP, backend/adapters is infrastructure. Current checkpoint: Phase 0 foundation
and Phase 1 domain implemented; Docker/PostgreSQL runtime verification outstanding.
Next phase: Phase 2 — Persistence.

Completed: uv/Python 3.13 foundation, FastAPI liveness, Docker/Alembic/CI definitions,
domain entities, robust profiles, initial safe update gate, strict cases, risk
strategies, model/event/repository ports, tests, six ADRs and research protocol.
No business tables, transaction API, authentication, ML model, SHAP or frontend yet.

Checks: 93 tests passed, 1 PostgreSQL test skipped, 90% coverage; Ruff and strict
mypy passed; pip-audit found no known vulnerabilities; distributions, Compose
configuration, offline migration SQL and live HTTP smoke passed. No failing tests.
Two upstream Starlette/AnyIO deprecation warnings remain. Docker engine unavailable.

Important: backend/app/profile/entities.py and gate.py; backend/app/cases/entities.py;
backend/app/shared/ports.py and events.py; backend/adapters/database/base.py;
infra/migrations; tests; docs/architecture/README.md; docs/research/protocol.md.

First make disposable PostgreSQL available and verify the existing migration test.
Then implement Phase 2 tables/migrations, repositories and atomic context-managed
UoW. Test rollback, uniqueness, immutable history and profile concurrency using
PostgreSQL, not SQLite. Plan durable scoped idempotency for Phase 3.

Commands from repository root:
uv sync --locked
uv run pytest --cov=backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run alembic upgrade head
uv build

Set FRAUDLENS_DATABASE_URL for Alembic and TEST_DATABASE_URL for disposable DB tests.
Original workspace fallback: ../../work/bootstrap/bin/uv with
UV_CACHE_DIR=../../work/uv-cache; existing .venv/bin tools also work.

Gate thresholds are uncalibrated. Cold start, compromised confirmations and
low-weight admission remain unresolved. Never fabricate metrics. Before stopping,
update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
