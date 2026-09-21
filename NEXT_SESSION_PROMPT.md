Continue FraudLens from completed Phase 8 — explicitly experimental native inference.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-014-experimental-native-inference.md, ADR-010, ADR-011, ADR-012 and
docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure; ml/src offline and excluded from serving wheel.
Phases 0–8 engineering checkpoints complete; production behavioral validation OPEN.
No risk API, HTTP inference, durable evaluation workflow, SHAP or frontend exists.

Phase 8 adds a native XGBoost FraudModel adapter, strict independently pinned manifest,
reviewed synthetic-only exporter, pure scoped context service and database-free replay CLI.
Checks bind native model/report hashes, exact behavior-v1 order and XGBoost runtime.
Inference never loads pickle/joblib. Only the restricted offline exporter may deserialize
verified bytes from the three independently pinned reviewed Phase 7 synthetic reports.
Scope: KZT, UTC, 180/30-day profile windows. CLI returns uncalibrated_score with
synthetic_only=true, production_eligible=false and calibrated=false. No database writes.
Legacy reports lack exact trained_at: preserve null; exported_at is actual export time.
Do not invent timestamps or create ModelVersion records with fabricated provenance.

Validation: 329 tests passed, zero skipped, 95% combined backend/ML coverage;
Ruff/format, strict mypy (86 files), builds, Compose configuration and PostgreSQL
migration/schema tests passed. Native export matched all 2,400 saved scores exactly
(maximum difference 0.0); real offline CLI replay passed. This is software parity,
not new predictive performance. Two upstream warnings remain. Dependencies unchanged;
prior clean audit retained. Docker runtime and remote CI remain unverified.

Local native bundle: ../../work/phase8/seed17; context: ../../work/phase8/first-context.json.
Trusted manifest SHA256: 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903.
Committed evidence: ml/experiments/phase8-native-export/{README.md,manifest.json,parity.json}.
Synthetic originals: ../../work/phase7/final-seed17, final-seed29, final-seed43.
ULB remains separate ulb-pca-v1, retrospective-only, behaviorally incompatible.
Its frozen final-test AP 0.733432 is already recorded; do not retune on that test.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md. Never use SQLite.
Schema unchanged: 0004_profile_revisions, 15 business tables. Business API fails closed
without FRAUDLENS_API_PRINCIPALS. Sandbox socket access may require approved execution.

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
.venv/bin/python -m backend.adapters.ml --bundle ../../work/phase8/seed17 --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903 --context ../../work/phase8/first-context.json

Important files: backend/adapters/ml/{bundle,xgboost_model,__main__}.py;
backend/app/fraud/{ports,service}.py; ml/src/training/export_model.py;
tests/ml/test_inference.py; backend/app/rules/engine.py; backend/app/risk/strategies.py.

Next: Phase 9 — Risk + Decision. Inspect existing strategies and decision policy first.
Define versioned rule-to-score mapping, explicit missing-input/NOT_EVALUATED semantics,
weights and experimental thresholds. Compose rules/model on one captured context through
ports, with deterministic replay, boundary, compatibility and failure tests. Keep scores
uncalibrated and production-ineligible. Atomic evaluation storage/model registration needs
separate provenance design; current ModelVersion requires an unknown legacy trained_at.

Preserve pinned pre-decision profiles and strict cutoffs. Current captures do not reconstruct
past availability. Transactions remain immutable RECEIVED. Intake/enrollment never authorizes
learning. Trusted bootstrap, feedback/gate orchestration, low-weight updates, corrections,
human login, SHAP, frontend and outbox dispatch remain open. No unprotected business writes.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate research metrics or silently promote experimental models.
