Continue FraudLens from Phase 16 IN PROGRESS after the fictional review-evidence checkpoint. Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md, docs/demo/README.md, docs/security/deployment-gates.md and ADR-029–033. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: framework-free backend/app, FastAPI backend/api, PostgreSQL adapters, React/TypeScript frontend and offline ml/src. Phases 0–14 are complete. Phase 15 production human auth remains fail-closed pending institutional recovery, real four-role/TLS deployment and independent security review. Production behavioral validation is OPEN; models/rules/sequences are experimental and production-ineligible.

Phase 16 demo-scenarios-v1 has four synthetic customers, 62 deterministic KZT transactions and five authored stories. The latest read-only audit of the local disposable fraudlens_test database found 49 MATCH / 13 ABSENT facts, 13 evaluations, 12 cases, 10 LEGITIMATE and 2 NEEDS_INVESTIGATION feedback entries, and zero learning decisions/profile revisions. Story A has retained rules-only INSUFFICIENT_EVIDENCE with explicitly absent profile. B --check-stage remains BLOCKED for no verified KZT profile. The fixture story text is not a verified label.

Two local analysts supplied their own feedback. analyst-two marked two BC/D cases NEEDS_INVESTIGATION because facts do not establish fraud or legitimacy. Do not infer legitimacy from small amounts or treat analyst-one's ten LEGITIMATE entries as external verification. Preserve immutable evidence. Do not bootstrap from uncertain cases, script verdicts, or bulk-apply later candidate stages. B/C baseline preservation and D adaptation remain NOT DEMONSTRATED. Profile revisions must be pinned before decisions; event-time-compatible revisions do not prove historical availability.

New: `demo-review-evidence-v1` is a separate deterministic role-play package for all 62 fixture IDs, SHA-256 `436c1c24119a12a7df63bf9f6ea4888a19c021b1eec94d4df945e83983687185`. It contains obviously fictional names, purposes, locations and artifact summaries. Every entry is synthetic-only, real_world_verified=false, production-ineligible and verdict-free. Baseline/A/B/D contain authored SUPPORT; C/E deliberately show UNAVAILABLE support. An authenticated scope-checked experimental no-store endpoint serves one entry and the console displays it with a role-play warning. It never changes transaction facts, features, risk, cases or profiles. See ADR-033.

The local console also lets an authenticated admin explicitly run rules-only evaluations from an unevaluated transaction detail view, selecting an absent-profile assertion or pinned pre-decision revision. The admin may then open a review case as a separate action. The backend enforces role/scope, CSRF, idempotency and experimental opt-in; analysts cannot submit evaluations. No verdict or profile learning is created by either action. Raw intake still does not auto-evaluate. ML-only/hybrid require a reviewed native behavior-v1 model bundle; none is configured in the local API.

PR #1 was verified MERGED at remote head `9857c84`. PR #2, https://github.com/nuchaaa/FraudLens/pull/2, contains the later console evaluation/case flow and this fictional evidence checkpoint; both backend and frontend checks passed on its initial head. PR #2 remains open and must not be merged without explicit instruction. Latest local validation: the pre-change baseline was 579 Python and 11 frontend tests; after this checkpoint 582 Python tests passed on PostgreSQL 17.10 with 90% combined coverage, plus Ruff, format, strict mypy (133 source files), frontend ESLint/12 Vitest tests/build. Two upstream deprecation warnings remain. No migration or dependency changed.

Next: restart the local API and console with experimental mode, have the two actual analysts independently review newly opened BC and D baseline cases using the packet, and do not tell them which verdict to choose. The two earlier NEEDS_INVESTIGATION cases remain unresolved evidence, not candidates for bootstrap. Only if at least five appropriate legitimate cases per customer include two distinct stored reviewers may an admin invoke the separate bootstrap workflow. Then verify B quarantine and baseline preservation, C against the pinned pre-decision revision, and ordered D adaptation. If reviewers do not support legitimacy, leave the story NOT DEMONSTRATED. Phase 15 remote release gates remain separate.

Disposable PostgreSQL: owner-only /private/tmp Unix socket, port 55439, database fraudlens_test; cluster ../../work/fraudlens-postgres/data. Never use SQLite or production data. From repo root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/python -m backend.adapters.demo --evidence-package
.venv/bin/python -m backend.adapters.demo --progress
.venv/bin/python -m backend.adapters.demo --walkthrough
.venv/bin/python -m backend.adapters.demo --check-stage B
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
cd frontend && npm run lint && npm test && npm run build

Before stopping, update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
