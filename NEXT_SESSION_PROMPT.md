Continue FraudLens from Phase 15 IN PROGRESS, after the completed local human-session
and dedicated PostgreSQL role-boundary checkpoints. Read PROJECT_STATUS.md first,
then docs/PROJECT_SPECIFICATION.md, development.md, docs/security/threat-model.md,
docs/security/deployment-gates.md, docs/adr/ADR-023-runtime-database-roles.md,
ADR-021, ADR-022, ADR-020, ADR-008, ADR-017, ADR-018 and ADR-019. Do not redo
completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable behavioral fraud detection with safe adaptive customer profiles.
Architecture: framework-free backend/app, FastAPI backend/api, infrastructure
backend/adapters, React/TypeScript/Vite frontend, offline ml/src. Phases 0–14 are
complete. Production behavioral validation remains OPEN; all model/evaluation
results are experimental and production-ineligible.

Phase 15 local checkpoint: four PostgreSQL identity tables in migration
0008_human_identity (27 non-Alembic tables total), typed repository and atomic
explicit-commit UoW. Operator getpass CLI provisions, recovers, disables/enables
and changes role/scope with audit and session revocation. Opt-in human login,
session, refresh and logout use hashed opaque tokens, shared bounded PostgreSQL
throttling, consumed-refresh replay detection, current account/version checks,
exact Origin and CSRF on browser writes. Local cookies are HttpOnly, host-only
and SameSite Strict; production config requires Secure cookies and HTTPS origin.
Machine bearer credentials remain separate, mixed auth is rejected, customer
scope and authorization-before-idempotency are preserved. The console uses
human login, restores/refreshes sessions and no longer asks for pasted tokens.
Auth defaults disabled; provision and enable locally using development.md.

The new database grant plan requires a dedicated non-public schema and four distinct
login roles: migrator owner, API, worker and identity operator. It revokes PUBLIC
database/schema/table privileges and applies an exact reviewed table matrix.
Production API, worker and operator processes verify effective grants at startup.
The API cannot write human accounts; login and operator changes instead serialize
on a transaction-scoped account advisory lock and reread the password hash after
locking. A recovery during login denies the old password. Current localhost Compose
still uses owner credentials and remains a development-only topology.

Validation: 534 tests passed, zero skipped, 92% combined backend/ML coverage on
PostgreSQL 17.10; two upstream Starlette/AnyIO warnings. Ruff/format, strict
mypy (122 source files), Alembic check, Python builds and Compose config
passed. Frontend ESLint, 5 Vitest tests and TypeScript/Vite build passed.
Operator CLI was exercised as a subprocess. Locked dependency audit after
Argon2 found no known vulnerabilities; no dependency/schema changes this checkpoint.
The new role test created and removed a separate *_test database with four real
password-authenticated PostgreSQL logins. It verified positive API/worker/operator
workflows and denied DDL, trigger disabling, history mutation, account provisioning,
TEMP and cross-role access; production-mode FastAPI login/Host/cookies were exercised
against the restricted API role. No real TLS proxy or remote deployment was tested.
Docker runtime and remote CI remain unverified. No predictive metrics added.

Supplemental sequence-v1-experimental remains retained evidence, not part of
risk-v1 scoring. Its authored low-and-slow example does not establish field
performance. No invented IP, location, graph intelligence or account-age facts.
Raw intake/enrollment, feedback or matched rules never authorize profile learning.

Next core work: apply and verify the four-role plan in a dedicated deployed
database, keeping role secrets outside application source and owner credentials
out of runtime processes. Verify actual TLS proxy, Host/Origin/forwarded-header
trust, Secure cookie and CSP behavior, edge request/concurrency/time limits,
secret rotation and operational recovery. Implement MFA and independently
verified human recovery, then obtain an independent security assessment before
any remote exposure. A policy document is not an implementation or approval.
Do not claim local TestClient checks or PostgreSQL throttles are a perimeter.
Deterministic demo seeding is Phase 16; risk-v2 dataset/calibration research,
corrections/weights and external outbox delivery are separate.

PostgreSQL: owner-only /private/tmp socket, port 55439, database fraudlens_test,
no TCP; cluster ../../work/fraudlens-postgres/data. See development.md for
restart/stop and CLI usage. Never substitute SQLite or touch production data.
Commands from repository root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
cd frontend && npm run lint && npm test && npm run build

Important: backend/adapters/database/grants.py; tests/integration/test_database_roles.py;
docs/adr/ADR-023-runtime-database-roles.md; docs/security/deployment-gates.md;
backend/app/identity/{policy,service,ports}.py;
backend/adapters/database/identity.py; backend/adapters/identity/__main__.py;
backend/api/{auth,dependencies}.py; backend/config.py; backend/main.py;
frontend/src/{App.tsx,Connect.tsx,api.ts}; tests/integration/test_human_auth.py;
infra/migrations/versions/0008_human_identity.py; docs/security/threat-model.md.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before stopping.
