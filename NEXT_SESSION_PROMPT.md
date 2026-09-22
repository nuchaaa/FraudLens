Continue FraudLens from completed Phase 14 — local analyst console.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-020-analyst-console-and-scoped-read-model.md, ADR-008, ADR-017,
ADR-018, ADR-019 and docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; framework-free backend/app, FastAPI backend/api,
infrastructure backend/adapters, React/TypeScript/Vite frontend; ml/src is offline.
Phases 0–14 engineering checkpoints complete; production behavioral validation OPEN.
No production risk API or human login exists. Experimental evaluation/review/profile
learning remains opt-in, uncalibrated, production-ineligible and carefully separated.

Phase 14 adds GET /api/v1/console/summary and /worklist. Both are authenticated,
no-store and customer-scoped. Summary counts are exact retained PostgreSQL facts:
UTC transaction event-time “today,” latest evaluation per transaction, HIGH/CRITICAL
suspicious amount and retained case feedback. It explicitly reports no production model
and no calibration. Worklist uses descending keyset pagination (1–100), joins each
immutable transaction to its latest retained experimental evaluation and case state,
and returns null risk rather than inventing a score. Empty scope returns empty data.

The responsive console has Overview, Transactions, Fraud Cases, Customers, Models and
System sections. It shows retained human-readable rule/model explanations, robust profile
windows and explicit missing evidence. Case review uses existing optimistic versioning,
fresh UUID idempotency and a confirmation dialog. It never changes RECEIVED transaction
status, executes suggested actions or treats feedback as learning authorization. Profile
learning controls are intentionally absent because learning requires an independent admin.

The raw expiring service credential is pasted locally and stays only in React memory;
refresh/disconnect clears it. No token is bundled, placed in URLs or persisted in browser
storage. This is not human authentication and must not be exposed remotely. Vite proxies
localhost during development; nginx provides same-origin API proxy/CSP in Compose. No
external fonts/assets or fabricated demo records exist. Case view currently filters the
loaded transaction worklist; no global case-only pagination or scoped audit-list API yet.

Migration head remains 0007_outbox_delivery: 21 business + 2 operational tables, plus
Alembic. Validation: 480 backend/ML tests passed, zero skipped, 94% combined coverage on
PostgreSQL 17.10; two upstream warnings remain. Ruff/format and strict mypy (108 sources),
Python builds and Compose configuration passed. Frontend ESLint, 2 Vitest tests,
TypeScript/Vite production build and npm audit passed; zero known npm vulnerabilities.
Responsive connection screen was visually checked in a real browser. Docker runtime and
remote CI remain unverified. No schema/model/predictive metric changes occurred.

PostgreSQL remains running without TCP: owner-only /private/tmp socket, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data. See development.md.
Never use SQLite. Sandbox socket access may require approval. Business API fails closed
without FRAUDLENS_API_PRINCIPALS; experimental writes require
FRAUDLENS_EXPERIMENTAL_ENABLED=true. The outbox worker remains local-recording-only.

Commands from repository root:
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
cd frontend && npm ci && npm run lint && npm test && npm run build

Important files: frontend/src/{App,pages,api,types,styles}.tsx;
frontend/{package.json,package-lock.json,Dockerfile,nginx.conf};
backend/app/console/{contracts,service}.py; backend/adapters/database/console.py;
backend/api/console.py; tests/integration/test_evaluation_api.py;
frontend/src/App.test.tsx; docs/adr/ADR-020-analyst-console-and-scoped-read-model.md.

Next: Phase 15 — Human authentication and security hardening. First write a threat model
and ADR covering human account lifecycle, Argon2id password hashes, session/JWT choice,
short-lived access, refresh rotation/reuse detection, revocation, CSRF, secure HttpOnly
cookies, trusted proxy/TLS assumptions, brute-force controls and recovery. Do not merely
turn current service tokens into browser storage.

Keep machine service principals for intake and introduce separate analyst/admin identities.
Preserve customer scope, reviewer/admin separation, authorization-before-idempotency replay,
audit/outbox atomicity and experimental opt-in. Add PostgreSQL identity/session state and
HTTP tests for inactive/expired/revoked accounts, rotation/reuse, concurrent sessions,
scope/role changes, CSRF, malformed credentials and secret non-disclosure. Use real
PostgreSQL, not SQLite. Do not expose remotely until TLS/proxy headers, runtime database
grants, cookies/CSP, secret management, rate limits and security review are verified.

Deterministic demo seeding remains Phase 16. Profile weights/corrections, compromised or
colluding confirmations, external outbox consumers/redrive, production model registration
and behavioral validation remain open. Preserve pinned pre-decision evidence; never invent
provenance, calibrated probabilities, delivery guarantees, model health or research metrics.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
