Continue FraudLens from the completed Phase 5 feature-engine checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md
and docs/adr/ADR-010-feature-context-and-availability.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app is framework-free domain/application,
backend/api is HTTP, backend/adapters is infrastructure.
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.

Completed: Phases 0–5, including authenticated transaction/profile APIs, scoped durable
idempotency, PostgreSQL persistence/UoW and immutable profile revisions. Phase 5 adds
29 ordered finite behavior-v1 features, explicit missing-history/MAD-floor indicators,
scoped read-only feature capture, strict versioned artifacts and authenticated capture/
offline replay CLI. Training batches and inference preparation share the pure extractor.
No scoring, trained ML, SHAP, human login, frontend, admission API or outbox dispatcher.
Migration head remains 0004_profile_revisions; 15 business tables; no dependency changes.

Validation: 260 tests passed, zero skipped, 97% coverage on PostgreSQL 17.10.
Ruff/format, strict mypy (68 backend files), pip-audit, builds, Compose configuration and
Alembic checks passed. PostgreSQL capture and offline CLI replay passed integration tests.
Two upstream deprecation warnings remain. Docker execution and remote CI are unverified.
Prior Uvicorn/PostgreSQL profile smoke passed in Phase 4; no new HTTP routes in Phase 5.

PostgreSQL remains running without TCP: owner-only /private/tmp socket, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data from repository.
See development.md for restart/stop and expiring credential setup. Sandbox socket access
may require approved execution outside the sandbox; never substitute SQLite.
Business access fails closed without FRAUDLENS_API_PRINCIPALS.

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
.venv/bin/python -m backend.adapters.features --help

Important files: backend/app/features/{context,engine,service,contracts}.py;
backend/adapters/features/{artifacts,__main__}.py; backend/adapters/database/transactions.py;
backend/app/shared/ports.py; tests/unit/test_feature_engine.py;
tests/integration/test_feature_capture.py; docs/adr/ADR-009-profile-reads-and-history.md.

Feature contract: profile version must be explicit, or explicitly assert absent profile.
Never use a revision containing the candidate. All windows exclude both boundaries.
Raw history is same customer/currency, strictly prior, bounded to 180 days/10,000 rows;
overflow fails instead of truncating. Baseline minimum=5; deviation denominator=max(MAD,
0.01), with missing/floor flags. Thresholds are uncalibrated. See ADR-010 for all formulas.
Recipient observed age is bounded activity age, not account age. Device ties can be missing.

Saved contexts pin facts; recapturing today may include late arrivals and does not
reconstruct historical availability. Retain contexts before original decisions. Capture
clock is not commit time. Declared offline source does not verify chronology. Artifacts
have SHA256 integrity, not authenticity; contain transaction facts; limit 16 MiB, no
overwrite. Future evaluation must persist context/vector/assessment atomically.
Profile provenance remains repository_admissions; admission_workflow_verified=false.

Next: Phase 6 — Rule Engine. Inspect existing Specification/RuleResult/RuleVersion and
risk reason contracts. Implement deterministic versioned rules/reason codes on captured
features, with explicit cold-start/missing behavior and experimental thresholds. Test
boundaries, stable explanations, version compatibility and replay. Do not fabricate
probabilities/model metadata or introduce unprotected business writes. Preserve phase
boundaries: ML and atomic evaluation integration are later work.

Do not admit raw intake or treat customer enrollment as legitimacy. Trusted bootstrap,
authorized feedback/gate orchestration, low-weight admission, compromised confirmations
and corrections remain unresolved. Transactions stay immutable RECEIVED records;
plan separate evaluation state. Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and
SESSION_LOG.md before ending. Never fabricate research metrics.
