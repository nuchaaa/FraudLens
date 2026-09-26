Continue FraudLens from Phase 15 IN PROGRESS and the completed supplemental sequence-evidence checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/security/threat-model.md, docs/adr/ADR-021-human-identity-and-sessions.md,
ADR-022-supplemental-sequence-evidence.md, ADR-020/008/017/018/019 and
docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable behavioral fraud detection with safe adaptive customer profiles.
Architecture: framework-free backend/app, FastAPI backend/api, backend/adapters
infrastructure, React/TypeScript/Vite frontend, ml/src offline. Phases 0–14 complete.
Production behavioral validation remains OPEN; all evaluation/model results experimental.

New detector checkpoint: sequence-v1-experimental adds four deterministic 24-hour signals
over the retained strict prior FeatureContext plus candidate: cumulative low-value sequence,
gradual amount escalation, repeated new recipient and cumulative exposure. It catches an
authored low-and-slow example while rules-v1 AMOUNT_ANOMALY remains NOT_MATCHED. A verified
learning-created profile, at least five admitted observations and prior raw activity are
required; missing facts make all signals NOT_EVALUATED. Policy, SHA256, exact Decimal evidence
and uncalibrated flags are retained. New evaluations contain sequence_evidence, but it is
deliberately excluded from risk-v1 scoring/actions. Older exact replays remain unchanged.
No IP/location/login/beneficiary lifecycle, graph intelligence or anomaly model was invented.

The analyst console now distinguishes stored INSUFFICIENT EVIDENCE from no evaluation and
reads nested rule reasons plus matched sequence reasons. A new evaluation/idempotency key is
needed to see sequence evidence on an old transaction; an old stored response cannot mutate.
Offline replay: .venv/bin/python -m backend.adapters.sequence PATH_TO_CONTEXT_JSON.
See docs/architecture/detector-layers.md. Risk-v2 requires a frozen dataset protocol,
validation-only calibration and false-positive/operator-burden evidence; do not add weights.

Phase 15 foundation remains unchanged: pure HumanAccount/SessionFamily policy,
PasswordVerifier port, explicit Argon2id adapter and 32 tests. Five-minute access,
30-minute refresh idle and eight-hour absolute family expiry; rotation never extends
absolute expiry; consumed refresh reuse requires family revocation. Human roles are
analyst/admin; passwords are exact 15–128 Unicode characters and <=512 UTF-8 bytes.
No persisted human account, session or HTTP login exists. The frontend still uses an
in-memory pasted service credential. ADR-021 is proposed.

Validation: 522 tests passed, zero skipped, 95% combined backend/ML coverage on PostgreSQL;
two unchanged upstream warnings. Ruff and strict mypy (115 sources) passed. Frontend ESLint,
3 Vitest tests and TypeScript/Vite build passed. Final format/package/Compose checks are in
PROJECT_STATUS.md and SESSION_LOG.md. Dependencies and schema are unchanged by the detector
checkpoint; prior clean dependency audit applies. Schema remains 0007_outbox_delivery with
23 non-Alembic tables. Docker runtime and remote CI remain unverified.

Next core work: continue Phase 15. Implement PostgreSQL account/session/consumed-refresh/
throttle repositories and atomic audited workflows through domain ports. Use database locks
for rotation/revocation, SHA256 digests of random tokens, account authorization versioning,
bounded shared login throttling, dummy verification and generic errors. Provision/recover/
disable/change scopes through a getpass-based audited operator CLI; never pass passwords in
command arguments. Prevent human/machine principal UUID collisions.

Then implement login/session/refresh/logout HTTP with Secure HttpOnly host-only SameSite
cookies, exact configured Origin and session-bound CSRF on unsafe cookie requests. Keep
machine bearer authentication separate and reject mixed/invalid auth without fallback.
Preserve scope and authorization-before-idempotent-replay. Replace the frontend token screen
only after security tests pass. Test PostgreSQL races, rollback, role/scope changes, refresh
reuse, expiry, CSRF, inactive accounts, secret disclosure and reviewer/admin separation.

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
cd frontend && npm run lint && npm test && npm run build

Important detector files: backend/app/sequence/engine.py;
backend/adapters/sequence/__main__.py; backend/adapters/evaluation.py;
tests/unit/test_sequence_engine.py; docs/adr/ADR-022-supplemental-sequence-evidence.md;
docs/architecture/detector-layers.md; frontend/src/{pages,types}.tsx.
Important security files: backend/app/identity/policy.py; backend/adapters/passwords.py;
tests/unit/test_identity_policy.py; backend/api/dependencies.py; backend/config.py;
backend/app/shared/security.py; backend/adapters/database/models.py; frontend/src/App.tsx,
Connect.tsx and api.ts; infra/migrations/versions.

Do not expose remotely until TLS/proxies, DB grants, cookies/CSP, secrets, edge limits and
security review are verified. Keep experimental opt-in, immutable RECEIVED transactions,
independent learning authorization and pinned pre-decision evidence. Raw intake/enrollment,
matched or unmatched sequences never authorize learning. Demo seeding remains Phase 16.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before stopping.
