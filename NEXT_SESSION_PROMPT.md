Continue FraudLens from Phase 15 IN PROGRESS — tested human identity/security foundation.
Read PROJECT_STATUS.md first, docs/PROJECT_SPECIFICATION.md, development.md,
docs/security/threat-model.md and docs/adr/ADR-021-human-identity-and-sessions.md,
then ADR-020/008/017/018/019 and docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable behavioral fraud detection with safe adaptive customer profiles.
Architecture: framework-free backend/app, FastAPI backend/api, backend/adapters
infrastructure, React/TypeScript/Vite frontend, ml/src offline. Phases 0–14 complete.
Production behavioral validation remains OPEN; all evaluation/model results experimental.

Phase 15 foundation adds pure HumanAccount/SessionFamily policy, PasswordVerifier port,
explicit Argon2id adapter and 32 tests. Five-minute access, 30-minute refresh idle,
eight-hour absolute family expiry; rotation never extends absolute expiry; consumed
refresh reuse requires family revocation. Human roles are analyst/admin; accounts
have authorization versions and optional expiry. Passwords are exact 15–128 Unicode
characters, at most 512 UTF-8 bytes; no trimming/normalization. Argon2id 64 MiB/t=3/p=4.
These are policy components ONLY: no persisted human account, session or HTTP login yet.
Existing frontend still requires pasted in-memory service credentials. ADR-021 is proposed.

Validation: 512 tests passed, zero skipped, 94% combined backend/ML coverage on PostgreSQL;
two unchanged upstream warnings. Ruff/format, strict mypy (111 sources), package builds
passed. See PROJECT_STATUS.md for dependency audit result. Added argon2-cffi 25.1.0 and
locked bindings/cffi/pycparser. Frontend unchanged; its prior 2 tests/build/lint passed.
Docker runtime and remote CI remain unverified. No known failing tests.
Schema remains 0007_outbox_delivery, 23 non-Alembic tables. No new predictive metrics.

Next: implement PostgreSQL account/session/consumed-refresh/throttle repositories and
atomic audited workflows through domain ports. Use database locks for rotation/revocation,
SHA256 digests of random tokens, account policy versioning and a bounded shared login
rate limiter before expensive hashing. Define dummy verification and generic errors.
Provision/recover/disable/change scopes through a getpass-based audited operator CLI;
never passwords in command-line args. Prevent human/machine principal UUID collisions.

Then add login/session/refresh/logout HTTP with Secure HttpOnly host-only SameSite cookies,
exact configured Origin and session-bound CSRF on unsafe cookie requests. Separate machine
bearer auth; reject mixed/invalid auth without fallback. Preserve customer scope and
authorization-before-idempotent replay. Replace frontend token screen only after security
tests pass; serialize refresh, clear customer data on expiry/logout, no browser token storage.
Test PostgreSQL races, rollback, account/role/scope changes, refresh reuse, expiry, CSRF,
malformed auth, secret disclosure and existing independent reviewer/admin learning rules.

PostgreSQL: owner-only /private/tmp socket, port 55439, fraudlens_test, no TCP.
Cluster ../../work/fraudlens-postgres/data. Restart details in development.md. Never SQLite.
Commands from repo root:
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv sync --locked --group ml
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline

Important: backend/app/identity/policy.py; backend/adapters/passwords.py;
tests/unit/test_identity_policy.py; backend/api/dependencies.py; backend/main.py;
backend/config.py; backend/app/shared/security.py; backend/adapters/database/models.py;
frontend/src/App.tsx, Connect.tsx and api.ts; infra/migrations/versions.

No remote exposure until TLS/proxies, DB grants, cookies/CSP, secrets, edge limits and
security review are verified. Keep experimental opt-in, immutable RECEIVED transactions,
independent learning authorization and pinned pre-decision evidence. Demo seeding is Phase 16.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before stopping.
