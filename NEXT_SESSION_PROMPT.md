Continue FraudLens from Phase 16 IN PROGRESS. Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md, docs/demo/README.md, docs/security/deployment-gates.md and ADR-029–032. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: framework-free backend/app, FastAPI backend/api, PostgreSQL adapters, React/TypeScript frontend and offline ml/src. Phases 0–14 are complete. Phase 15 production human auth remains fail-closed pending institutional recovery, real four-role/TLS deployment and independent security review. Production behavioral validation is OPEN; models/rules/sequences are experimental and production-ineligible.

Phase 16 demo-scenarios-v1 has four synthetic customers, 62 deterministic KZT transactions and five authored stories. The latest read-only audit of the local disposable fraudlens_test database found 49 MATCH / 13 ABSENT facts, 13 evaluations, 12 cases, 10 LEGITIMATE and 2 NEEDS_INVESTIGATION feedback entries, and zero learning decisions/profile revisions. Story A has retained rules-only INSUFFICIENT_EVIDENCE with explicitly absent profile. B --check-stage remains BLOCKED for no verified KZT profile. The fixture story text is not a verified label.

Two local analysts supplied their own feedback. analyst-two marked two BC/D cases NEEDS_INVESTIGATION because facts do not establish fraud or legitimacy. Do not infer legitimacy from small amounts or treat analyst-one's ten LEGITIMATE entries as external verification. Preserve immutable evidence. Do not bootstrap from uncertain cases, script verdicts, or bulk-apply later candidate stages. B/C baseline preservation and D adaptation remain NOT DEMONSTRATED. Profile revisions must be pinned before decisions; event-time-compatible revisions do not prove historical availability.

The local console now lets an authenticated admin explicitly run rules-only evaluations from an unevaluated transaction detail view, selecting an absent-profile assertion or pinned pre-decision revision. The admin may then open a review case as a separate action. The backend enforces role/scope, CSRF, idempotency and experimental opt-in; analysts cannot submit evaluations. No verdict or profile learning is created by either action. Raw intake still does not auto-evaluate. ML-only/hybrid require a reviewed native behavior-v1 model bundle; none is configured in the local API. The saved synthetic XGBoost offline replay proves adapter operation, not field performance. The demo has no sender/receiver names, merchant/ИП, purpose or verified payment place; do not attach real businesses to fictional transfers. Source-linked sanitized payment facts would be required for enrichment.

PR https://github.com/nuchaaa/FraudLens/pull/1 is OPEN and unmerged on branch codex/fix-demo-ci-and-evaluation-context. The remote branch includes the PostgreSQL socket CI fix, isolated demo tests, corrected walkthrough guidance and context disclosure. The admin console evaluation/case change is committed LOCALLY but not pushed: automatic approval review rejected its GitHub egress for lack of trusted authorization for this exact payload. Do not bypass; obtain explicit user approval before pushing. Latest local validation: 579 passed, zero skipped, 90% combined coverage on PostgreSQL 17.10; Ruff, format, strict mypy (131 source files), frontend ESLint/11 Vitest tests/build passed. Two upstream deprecation warnings remain. Check latest remote CI only after an authorized push; do not merge without the user's instruction.

Next: If reviewers can obtain independent transaction-linked facts, capture provenance and actual authorized reviews before any trusted bootstrap or later story stages. If not, leave B/C/D pending and explain the missing evidence instead of adding more demo helper code. Do not fabricate metrics, identities, transaction facts or reviewer evidence. Phase 15 remote release gates remain separate.

Disposable PostgreSQL: owner-only /private/tmp Unix socket, port 55439, database fraudlens_test; cluster ../../work/fraudlens-postgres/data. Never use SQLite or production data. From repo root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/python -m backend.adapters.demo --progress
.venv/bin/python -m backend.adapters.demo --walkthrough
.venv/bin/python -m backend.adapters.demo --check-stage B
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
cd frontend && npm run lint && npm test && npm run build

Before stopping, update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
