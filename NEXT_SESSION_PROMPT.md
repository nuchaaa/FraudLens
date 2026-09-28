Continue FraudLens from Phase 16 IN PROGRESS. Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md, docs/demo/README.md, docs/security/deployment-gates.md and ADR-029–032. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: framework-free backend/app, FastAPI backend/api, PostgreSQL adapters, React/TypeScript frontend and offline ml/src. Phases 0–14 are complete. Phase 15 production human auth remains fail-closed pending institutional recovery, real four-role/TLS deployment and independent security review. Production behavioral validation is OPEN; models/rules/sequences are experimental and production-ineligible.

Phase 16 fixture demo-scenarios-v1 has four synthetic customers, 62 deterministic KZT transactions and five authored stories: A normal-looking, B 8M vehicle payment, C later 500k new recipient for B's customer, D gradual 45k–110k, E six-transfer escalation. Story text is not a verified label. The local Unix-socket fraudlens_test DB currently has the 48 BASELINE facts plus story A (49 MATCH / 13 ABSENT). A has a retained rules-only INSUFFICIENT_EVIDENCE evaluation with explicitly absent profile. B --check-stage is BLOCKED because no verified prior KZT profile exists. No profile revision or learning decision was written.

Two friends provisioned separate local analyst accounts scoped to BC/D and entered their own feedback. analyst-one marked 10 earlier cases LEGITIMATE; analyst-two marked two additional BC/D cases NEEDS_INVESTIGATION because available facts do not establish fraud or legitimacy. The ten LEGITIMATE entries are not external verification, and a prior case closure by analyst-two is not a second verdict. Preserve all immutable evidence. Do not bootstrap from uncertain cases, script review verdicts, infer legitimacy from small amounts, or bulk-apply later candidate stages. B/C baseline preservation and D adaptation remain NOT DEMONSTRATED. Genuine independent evidence and authorized reviews are needed before any admission.

The demo CLI already has guarded --progress, --walkthrough, --check-stage and --apply-stage BASELINE/A/B/C/D1–D5/E1–E6. Later stages require prior verified profile and retained workflow evidence. Review docs/demo/README.md before use. Versions must be pinned before each decision; event-time-compatible revisions do not establish historical availability. The CLI cannot reconstruct actual bank arrival or labels.

Raw transaction intake does not auto-evaluate. NOT EVALUATED means no retained assessment, not low risk. Rules-only evaluation is separate and experimental. ML-only/hybrid also require a reviewed, explicitly configured native behavior-v1 model bundle; the local API currently has none. A saved synthetic XGBoost context replayed offline, proving software operation, not field performance. The console discloses absent sender/receiver names, merchant/ИП, purpose and verified payment location. Kazakhstan public registration lookup cannot identify who received a fictional transfer. Do not attach a real business to synthetic transactions or invent transaction context; source-linked sanitized payment facts would be needed for enrichment.

Maintenance PR https://github.com/nuchaaa/FraudLens/pull/1 is OPEN, not merged. Branch codex/fix-demo-ci-and-evaluation-context fixes GitHub backend CI's TCP-versus-Unix-socket mismatch, isolates demo tests, corrects staged walkthrough guidance, and clarifies the console. The code-bearing commit da2c005 passed both backend and frontend checks on push and PR runs 36379022107 and 36379026221; inspect checks on any newer documentation-only head before claiming it green. Local validation: 578 passed, zero skipped, 90% combined backend/ML coverage on PostgreSQL 17.10; Ruff, format, strict mypy (131 source files), frontend lint/9 Vitest tests/build passed. Two upstream deprecation warnings remain. Do not merge without the user's instruction.

Next: inspect current retained evidence read-only. If reviewers cannot obtain independently verifiable transaction-linked facts, keep BC/D admissions and stories B/C/D pending; explain the concrete missing evidence rather than add more helper code. If the user supplies a legitimate sanitized payment source, design provenance-aware optional merchant/payee/place fields, explicit unavailable states and point-in-time capture before implementation; do not infer these from public registries. Do not claim synthetic scores as predictive metrics or promote the model. Phase 15 release gates remain separate.

Disposable PostgreSQL uses owner-only /private/tmp Unix socket, port 55439, database fraudlens_test; cluster ../../work/fraudlens-postgres/data. Never use SQLite or production data. From repo root:
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

Before stopping, update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md. Never fabricate metrics, identities, transaction facts or reviewer evidence.
