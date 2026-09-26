Continue FraudLens from Phase 15 IN PROGRESS, after local human-session,
PostgreSQL role-boundary and native HTTPS-edge checkpoints. Read
PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/security/{threat-model,deployment-gates,mfa-and-recovery-requirements}.md,
docs/adr/ADR-023-runtime-database-roles.md, ADR-024-local-https-edge-checkpoint.md,
ADR-021, ADR-022, ADR-020, ADR-008, ADR-017, ADR-018 and ADR-019. Do not redo
completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable behavioral fraud detection with safe adaptive customer profiles.
Architecture: framework-free backend/app, FastAPI backend/api, infrastructure
backend/adapters, React/TypeScript/Vite frontend, offline ml/src. Phases 0–14
are complete. Production behavioral validation remains OPEN; all model and
evaluation results are experimental and production-ineligible.

Phase 15 local human sessions are complete: four PostgreSQL identity tables in
0008_human_identity (27 non-Alembic tables total), typed repository/UoW, audited
operator getpass CLI, opt-in opaque hashed session login/refresh/logout, bounded
shared PostgreSQL throttling, consumed-refresh replay detection, current account
checks, exact Origin and CSRF, HttpOnly host-only SameSite Strict cookies. Machine
bearer auth remains separate; mixed auth is rejected. The console uses human login.
Auth defaults disabled; production config requires HTTPS origin and Secure cookies.

The dedicated-schema grant plan separates migrator owner, API, worker and operator
logins. Production processes verify effective privileges; the API cannot DDL,
disable history triggers, mutate immutable records or provision human accounts.
Login/operator changes share an advisory account lock and login rereads current
password hash after locking. Real-role PostgreSQL integration passed. Current
localhost Compose still uses owner credentials and stays development-only.

New local edge checkpoint: frontend/Dockerfile.production and
nginx.production.conf.template require an explicit DNS host and mounted cert/key.
They reject unknown Host/SNI, terminate TLS, set CSP/HSTS, replace forwarded
headers and bound body, requests, concurrency and timeouts. Backend Dockerfile
starts Uvicorn with --no-proxy-headers; development nginx also sanitizes headers.
Homebrew nginx 1.31.4 accepted the rendered config. An actual self-signed local
Nginx/FastAPI/PostgreSQL smoke verified HTTPS frontend, Host 421, Origin 403,
Secure/HttpOnly __Host- cookies and session, body 413, rate 429, HTTP 308 and
forged forwarded-header replacement with an echo upstream. Temporary database,
certificate, cookies and processes were removed. This used the app's test mode,
not the four-role production topology. Docker Desktop cannot launch on this host:
its executable is missing and daemon socket absent. The candidate container image,
remote hostname/certificate, load budget and deployed network remain unverified.

MFA and independently verified recovery requirements are now written in
docs/security/mfa-and-recovery-requirements.md. They are NOT implemented.
Before remote human login, implement phishing-resistant WebAuthn with origin/RP
binding, one-use challenges, current account checks and audited factor lifecycle;
require two independent authenticated operators and out-of-band proof for recovery.
Do not weaken password/session, review/learning separation or service auth. Obtain
an independent security assessment before any remote exposure. Local TLS evidence
is not deployment approval, production perimeter validation or a load test.

Validation: 534 PostgreSQL/ML tests passed, zero skipped, 92% coverage; two
upstream Starlette/AnyIO warnings. Ruff/format, strict mypy (122 source files),
Alembic check, Python builds and Compose configuration passed. Frontend ESLint,
5 Vitest tests and TypeScript/Vite build passed. Dependencies/schema/model
unchanged; prior locked audit found no known vulnerabilities. No predictive
metrics were added. Docker runtime and remote CI remain unverified.

Supplemental sequence-v1-experimental remains retained evidence, not risk-v1
scoring. Its authored low-and-slow example is no field-performance proof. No
invented IP, location, graph or account-age facts. Intake, enrollment, feedback
and matched rules never authorize profile learning.

Next: continue Phase 15 with reviewed MFA/recovery implementation and a combined
four-role HTTPS container topology when a working Docker engine and deployment
target are available. Verify real hostname/certificate, browser/proxy trust,
operating limits under load, secret rotation, backup/restore and incident recovery.
Do not run grant changes against the existing public-schema demo or touch
production data. Deterministic demo seeding is Phase 16; risk-v2 calibration,
corrections/weights and external outbox delivery are separate.

PostgreSQL: owner-only /private/tmp socket, port 55439, database fraudlens_test,
no TCP; cluster ../../work/fraudlens-postgres/data. See development.md. Sandboxed
socket access may need approved execution. Never substitute SQLite.
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

Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before stopping.
