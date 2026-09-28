Continue FraudLens from Phase 16 IN PROGRESS, after deterministic synthetic facts,
the read-only evidence ledger, guided walkthrough, staged disposable intake,
read-only stage preflight and fixture-bootstrap provenance hardening.
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
Story text is not ground truth. On 2026-09-28 the user authorized step-by-step
local setup. The working public-schema `fraudlens_test` database now contains
the 48 BASELINE fixture transactions and four synthetic customers. Story A
passed read-only preflight; its single 25,000 KZT candidate was then added
and evaluated rules-only with an explicitly absent profile, returning
INSUFFICIENT_EVIDENCE. The read-only walkthrough now shows 49 MATCH / 13
ABSENT. The two analyst accounts are scoped to BC/D, not A; present A with
the local read-only walkthrough or an authorized admin view. A temporary local
test-only machine admin credential created 10 authenticated experimental rules-only
evaluations with explicit absent profiles and 10 review cases, five each
for early BC and D baseline transfers. `analyst-one` entered 10 LEGITIMATE
feedback records and `analyst-two` closed one already-reviewed case; that
closure is not independent reviewer feedback. Two additional absent-profile
evaluations and empty OPEN cases were created for untouched BC/D baseline
transactions: BC `496d0faf-b34c-5e62-83f1-2bc2d8576e2b`, D
`2067e0ff-d1b0-5b14-b049-c1435c14a672`. `analyst-two` entered
NEEDS_INVESTIGATION feedback on both because the available facts did not prove
fraud or legitimacy. The transaction schema lacks merchant/building/location
facts, and small amounts are not legitimacy evidence. Read-only SQL found no
BC/D profile or learning decision. The bulk --apply path creates facts only and
deliberately bypasses staged prerequisites. Do not bulk-apply later candidates
during staged review.
B read-only preflight remains BLOCKED for lack of a verified prior KZT profile.
The read-only walkthrough now tells presenters to run the exact stage preflight
for absent A–E candidates and apply only if READY; do not follow old copied
output that generically suggested applying absent facts. Focused PostgreSQL
renderer test, Ruff/format and mypy passed; no migration or dependency changed.

Current maintenance checkpoint: raw synthetic intake does not automatically
evaluate transactions, so NOT EVALUATED means no retained assessment, not low
risk. Rules-only evaluation is a separate authorized experimental action;
ML-only/hybrid also require an explicitly configured reviewed native behavior-v1
bundle. The synthetic XGBoost adapter replayed a saved context offline, but the
local API has no bundle configured and no production model is approved. The
console now states these distinctions and flags missing sender/receiver names,
merchant/ИП, purpose and verified payment location. Kazakhstan registry lookup
can verify an already identified business but cannot link a real business to
our fictional transfer; do not invent that link or a fraud implication.
GitHub's backend check failed because CI supplied a TCP PostgreSQL URL while the
demo seeder guard requires a local Unix socket. CI now proxies its disposable
PostgreSQL service through an owner-only socket for tests. A separate demo test
was isolated to a fresh schema to remove order dependence. Locally 578 tests
passed, zero skipped, 90% coverage, with Ruff/format/mypy and frontend
lint/9 tests/build passing. The user explicitly authorized publication;
PR https://github.com/nuchaaa/FraudLens/pull/1 is open on branch
`codex/fix-demo-ci-and-evaluation-context`. Both backend and frontend checks
passed on push run 36378777231 and PR run 36378805856. Do not merge without
the user's instruction.

The --progress and --walkthrough commands use a repeatable-read, read-only
PostgreSQL snapshot under a local Unix-socket *_test/non-production guard.
They show exact fact identity, retained evaluations and captured versions,
case/feedback/learning decisions, immutable profile revisions, and A–E manual
steps. Event-time-compatible revisions do NOT prove historical availability.
They cannot generate analyst verdicts or certify behavioral outcomes.

New --apply-stage supports BASELINE (48 background facts), A, B, C, D1–D5 and
E1–E6 with original IDs/idempotency keys. B/C/D/E require a verified prior KZT
profile whose first immutable revision has accepted BOOTSTRAP evidence for at
least five matching fixture baseline admissions and two distinct recorded
reviewers. A verified profile built from unrelated data does not unlock them.
The stored trace does not independently authenticate the people or prove real
legitimacy. C additionally requires a retained B evaluation and an exceptional
amount QUARANTINE learning decision without profile-version advance; later D
stages require a prior ACCEPT learning decision; later E
stages require a prior evaluation. Missing prerequisites fail without writes.
It creates no profiles, reviews or evaluations. A PostgreSQL advisory lock
serializes fixture CLI writes, not arbitrary API writers. It controls local
insertion order but does not reconstruct actual bank arrival/label knowledge.
An isolated migrated-schema test seeded/replayed BASELINE and A, and verified
later stages refuse absent review/profile evidence. Positive reviewer-dependent
paths have NOT been exercised or claimed. No actual reviewers are available.
The new --check-stage STAGE previews READY/BLOCKED/CONFLICT/REPLAYABLE without
writes. It uses the same disposable guard and apply rechecks prerequisites;
preflight is not a reservation or evidence of reviewer legitimacy. A live
read-only check of B reported BLOCKED for absent background facts.

Validation: 578 tests passed, zero skipped, 90% combined backend/ML coverage on
PostgreSQL 17.10. Ruff/format, strict mypy (131 source files), existing migration
tests and offline source/wheel build passed. After the final C-stage guard edit,
11 focused PostgreSQL/unit tests and global Ruff/format/mypy passed. The unchanged frontend last passed
ESLint/nine Vitest tests/build at the previous checkpoint. Two upstream
deprecation warnings remain. Dependencies and migrations unchanged; no known
failing tests. Docker runtime and remote CI unverified.

Current immediate step: preserve the two NEEDS_INVESTIGATION findings and do
not run bootstrap. Additional verified evidence would be needed before either
analyst could support a legitimate verdict; do not script or infer it.
Two friends independently provisioned `analyst-one` and `analyst-two` through
the owner-only CLI, choosing private passwords in Terminal. Read-only SQL
verified that both are active `analyst` accounts scoped to BC customer
`d89ce2ce-b645-54de-a4b5-2c739c253309` and D customer
`4d3da7ed-8d80-51b9-b26e-e7f1bb7ffa3d`; no credential material was read.
Keep their browser sessions separate or sign out between turns; never request
passwords in chat. Case-preparation actions submitted no verdicts. Analyst
feedback is user-entered and does not establish externally verified legitimacy.
Local-only Uvicorn (`127.0.0.1:8000`) and Vite (`127.0.0.1:5173`) were started
with human auth and experimental routes enabled; their HTTP endpoints responded.
If those processes stop, restart using development.md. Do not expose them remotely.

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
The staged CLI and guide are already implemented and tested. If the same
read-only evidence remains absent and no genuine reviewers are available, do
not add more preflight helpers or mark Phase 16 complete. Report the concrete
missing inputs to the user and leave B/C/D as guided, NOT DEMONSTRATED.
The user must supply genuinely independent local reviewer input; account setup
and seeded raw facts alone do not provide evidence for behavioral outcomes.

Disposable PostgreSQL: /private/tmp owner-only Unix socket, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data. Never use
SQLite or production data. Commands from repo root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/python -m backend.adapters.demo --progress
.venv/bin/python -m backend.adapters.demo --walkthrough
.venv/bin/python -m backend.adapters.demo --check-stage B
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
