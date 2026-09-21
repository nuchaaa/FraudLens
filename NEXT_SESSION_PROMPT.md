Continue FraudLens from the completed Phase 7 external retrospective benchmark checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-013-external-retrospective-benchmark.md, ADR-012, docs/research/protocol.md,
docs/research/ulb-benchmark-protocol.md and ulb-NOTICE.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure, ml/src offline (excluded from serving wheel).
Phases 0–6 and Phase 7 synthetic/external benchmark engineering checkpoints are complete.
Production behavioral validation remains OPEN. No serving model or risk API exists.

New: public Kaggle metadata verified ULB dataset ID 310/version 3 and listed ODbL/DbCL
terms. Hash-pinned download/import, strict CSV validation, separate ulb-pca-v1 contract,
label-independent duplicate exclusion, frozen time splits and fixed three-model comparison.
Dataset fields cannot support behavior-v1: no customer/recipient/device/currency fields,
arrival/label availability or known PCA fitting scope. Do not invent these facts.

Measured external run: 284,807 source rows, 9,144 later identical feature tuples excluded.
Train/validation/test: 140,216/46,357/89,090 rows; boundaries 86,400/129,600 elapsed seconds.
Logistic Regression won validation average precision. At validation-selected threshold
0.95: final-test AP 0.733432, precision 0.274854, recall 0.824561, F1 0.412281,
FPR 0.002787 (94 TP, 248 FP, 20 FN, 88,728 TN). Retrospective evidence only;
production_eligible=false and behavioral_compatible=false. Do not retune on this test.
Earlier synthetic behavior-v1 XGBoost runs remain intact and production-ineligible.

Validation: 304 tests passed, zero skipped, 96% combined backend/ML coverage.
Ruff/format, strict mypy (81 files), builds, Compose configuration and PostgreSQL
migration/schema tests passed. Two upstream deprecations remain. Dependencies unchanged;
prior clean audit applies. Docker runtime and remote CI unverified. No known failing tests.

PostgreSQL remains running: no TCP, owner-only /private/tmp socket, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data. See development.md.
Schema unchanged: 0004_profile_revisions, 15 business tables. Never substitute SQLite.
Sandbox socket access may require approved execution. macOS libomp is installed.

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
Use --group ml with uv run for tests/types. Experiment output directories must be new.

Important new files: ml/src/datasets/ulb.py; ml/src/features/ulb.py;
ml/src/training/ulb_benchmark.py; tests/ml/test_ulb_benchmark.py;
ml/experiments/ulb-retrospective-v1/{README.md,report.json}; docs/research/ulb-*.
Source: ../../work/phase7/ulb-v3/creditcard.csv. Complete external artifacts:
../../work/phase7/ulb-benchmark-v1-run2. First attempt failed before training on quoted
numeric CSV; parser fixed and regression-tested without changing protocol/settings.
Synthetic artifacts: ../../work/phase7/final-seed17, final-seed29, final-seed43.
Load joblib only from trusted locally generated artifacts. Neither model is in the API.

Next: Phase 8 — explicitly experimental inference. First inspect FraudModel,
FraudPrediction and ModelVersion ports and actual saved synthetic behavior-v1 artifacts.
Design a trusted manifest/loader with exact model hash, feature version/order, training
provenance and experimental eligibility. Implement the model adapter and captured-context
replay with parity, corrupt/incompatible artifact and failure tests. Never load arbitrary
uploaded pickle or invent model metadata. Keep ulb-pca-v1 separate from behavior-v1.
No silent production promotion, unprotected writes or fabricated calibrated probabilities.

Preserve pinned pre-decision profiles and strict cutoffs. Current captures do not reconstruct
past availability. Transactions stay immutable RECEIVED; atomic evaluation/context storage
needs separate design. Raw intake/enrollment never establishes legitimacy. Trusted bootstrap,
feedback/gate orchestration, low-weight admission, corrections, human login, SHAP, frontend
and outbox dispatch remain future work. Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md
and SESSION_LOG.md before ending. Never fabricate metrics.
