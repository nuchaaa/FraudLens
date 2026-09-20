Continue FraudLens from the completed Phase 4 profile-read checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md
and docs/adr/ADR-009-profile-reads-and-history.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; backend/app is framework-free domain/application,
backend/api is HTTP, backend/adapters is infrastructure.

Completed: Phases 0–4. Authenticated transaction submission/retrieval, admin customer
enrollment, scoped durable idempotency, atomic audit/outbox/response writes and PostgreSQL
persistence remain intact. Phase 4 adds scoped GET /api/v1/customers/{customer_id}/profiles/{currency},
explicit cold/insufficient history, robust short/long summaries, hour counts/typical hours,
known recipients, observation frequency and immutable profile revision replay.
Migration head: 0004_profile_revisions; 15 business tables. No risk scoring, trained ML,
SHAP, frontend, human login, trusted admission API or outbox dispatcher exists.

Validation: 227 tests passed, none skipped, 97% coverage on PostgreSQL 17.10.
Ruff, strict mypy (62 backend files), pip-audit, package builds, Compose configuration,
Alembic checks and actual Uvicorn/PostgreSQL profile HTTP smoke passed.
Two upstream deprecations remain; Docker execution and remote CI are unverified.
No known failing tests. Dependencies are unchanged.

PostgreSQL remains running without TCP: owner-only socket /private/tmp, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data from repository.
See development.md for restart/stop and expiring service credential setup.
Sandboxed socket access may require approved execution outside the sandbox; never use SQLite.
Business endpoints fail closed without FRAUDLENS_API_PRINCIPALS.

Commands from repository root:
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline

Important files: backend/app/profile/{read_model,service,entities,gate}.py;
backend/api/profiles.py; backend/adapters/database/{profiles,models}.py;
backend/app/shared/ports.py; backend/app/features/contracts.py;
infra/migrations/versions/0004_profile_revisions.py;
tests/integration/{test_profile_api,test_migrations}.py; tests/unit/test_profile_reads.py.

Profile contract: explicit as_of requires a pinned version; exclude both the candidate
instant and lower window boundary. Future cutoffs -> 422, unavailable revisions -> 404,
cutoffs before a revision head -> 409. Later admissions cannot alter committed revisions.
Upgrade backfills current heads only; never invent older metadata. Revision guards use
PostgreSQL transaction identity/xmin and the top-level UoW; no nested savepoint writes.
Historical replay needs the version captured before the original decision; selecting a
version today is not proof it was available historically. No knowledge_at reconstruction
or fabricated commit times. history_source=repository_admissions and
admission_workflow_verified=false disclose unresolved provenance.

Next: Phase 5 — Feature Engine. Inspect the existing FeatureVector contract and profile
views first. Define ordered/versioned features, explicit missing-history indicators and
finite zero-MAD behavior, then implement shared pure production feature extraction for
future training and inference. Separate trusted baseline features from raw activity;
add only required cutoff-safe repository queries for velocity/device/recipient history,
with explicit availability semantics. Test deterministic ordering, cold starts, currency
isolation, candidate exclusion, future/late-data leakage and training/inference parity.

Do not automatically admit raw intake or treat admin enrollment as legitimacy. Trusted
bootstrap, authorized feedback/gate orchestration, low-weight admission, compromised
confirmations and corrections remain unresolved; thresholds are uncalibrated.
Transactions remain immutable RECEIVED records; plan evaluation state separately.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate research metrics.
