Continue FraudLens from Phase 16 IN PROGRESS, after deterministic synthetic facts,
the read-only evidence ledger, guided walkthrough and staged disposable intake.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/demo/README.md, docs/adr/ADR-032-staged-disposable-demo-intake.md,
ADR-031, ADR-030, ADR-029 and docs/security/deployment-gates.md.
Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: framework-free backend/app, FastAPI backend/api, PostgreSQL adapters,
React/TypeScript frontend and offline ml/src. Phases 0–14 complete. Phase 15
remote human security remains an external release gate; production human auth
fails closed. No institutional proof issuer/notice process or two independently
authenticated remote admins are available. Current Compose uses owner credentials;
Docker engine, four-role TLS topology and independent review remain unverified.
Production behavioral validation is OPEN; models/rules/sequences are experimental.

Phase 16 demo-scenarios-v1: stable UUIDv5 IDs, four customers, 62 KZT facts and
five authored stories: normal A, 8M vehicle B, 500k new-recipient C for B's
customer, gradual 45k–110k D and six-transfer 50k–500k E. Manifest SHA256:
4645220dd30cfabb12e8a22688a45035d81e352fe2ef5998f6f16a33019f26c8.
Story text is not ground truth. The working public-schema test DB remains
unseeded: the last read-only smoke showed 62 ABSENT facts. The bulk --apply
path creates facts only and deliberately bypasses staged prerequisites.

The --progress and --walkthrough commands use a repeatable-read, read-only
PostgreSQL snapshot under a local Unix-socket *_test/non-production guard.
They show exact fact identity, retained evaluations and captured versions,
case/feedback/learning decisions, immutable profile revisions, and A–E manual
steps. Event-time-compatible revisions do NOT prove historical availability.
They cannot generate analyst verdicts or certify behavioral outcomes.

New --apply-stage supports BASELINE (48 background facts), A, B, C, D1–D5 and
E1–E6 with original IDs/idempotency keys. B/C/D/E require a verified prior KZT
profile; C additionally requires retained B evaluation and separate learning
decision; later D stages require a prior ACCEPT learning decision; later E
stages require a prior evaluation. Missing prerequisites fail without writes.
It creates no profiles, reviews or evaluations. A PostgreSQL advisory lock
serializes fixture CLI writes, not arbitrary API writers. It controls local
insertion order but does not reconstruct actual bank arrival/label knowledge.
An isolated migrated-schema test seeded/replayed BASELINE and A, and verified
later stages refuse absent review/profile evidence. Positive reviewer-dependent
paths have NOT been exercised or claimed. No actual reviewers are available.

Validation: 576 tests passed, zero skipped, 90% combined backend/ML coverage on
PostgreSQL 17.10. Ruff/format, strict mypy (131 source files), existing migration
tests and offline source/wheel build passed. The unchanged frontend last passed
ESLint/nine Vitest tests/build at the previous checkpoint. Two upstream
deprecation warnings remain. Dependencies and migrations unchanged; no known
failing tests. Docker runtime and remote CI unverified.

Next: To complete the five-story demonstration, obtain actual authorized local
analyst sessions and independent reviewer evidence. Do NOT script unverified
human verdicts, automatically admit intake, or treat story text as legitimacy
or fraud. If reviewers remain unavailable, leave B/C baseline preservation and
D gradual adaptation as guided, NOT DEMONSTRATED. With real inputs, use existing
evaluation/case/bootstrap/learning APIs, pin profile versions BEFORE decisions,
then inspect B's gate action, B/C immutable revisions and median preservation,
and D's ordered accepted revisions. Show cold/insufficient evidence explicitly.
Do not fabricate metrics, claim production performance, or promote models.
Phase 15 remote security remains closed.

Disposable PostgreSQL: /private/tmp owner-only Unix socket, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data. Never use
SQLite or production data. Commands from repo root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/python -m backend.adapters.demo --progress
.venv/bin/python -m backend.adapters.demo --walkthrough
.venv/bin/python -m backend.adapters.demo --apply-stage BASELINE  # only when explicitly seeding the disposable DB
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
cd frontend && npm run lint && npm test && npm run build

Important: backend/app/demo/{scenarios,stages}.py;
backend/adapters/demo/{__main__,progress,walkthrough}.py;
tests/{unit/test_demo_scenarios,integration/test_demo_seed}.py;
docs/demo/README.md and ADR-029/030/031/032. Update PROJECT_STATUS.md,
NEXT_SESSION_PROMPT.md and SESSION_LOG.md before stopping.
