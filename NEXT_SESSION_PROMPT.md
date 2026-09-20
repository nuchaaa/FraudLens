Continue FraudLens from the Phase 7 synthetic offline experiment checkpoint.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-012-offline-experiment-boundaries.md, docs/research/protocol.md and
docs/research/dataset-assessment.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; backend/app framework-free; backend/api HTTP;
backend/adapters infrastructure; ml/src offline experiments, excluded from serving wheel.
Phases 0–6 remain complete. Phase 7 engineering pipeline is implemented; external-data
validation and production baseline selection remain OPEN. Do not call the synthetic
winner a validated production model.

New: original synthetic-behavior-v1 generator, explicit event/arrival/label clocks,
static authored bootstrap, point-in-time replay through production behavior-v1 features,
chronological splits with label maturity, held-out customers, three-model comparison,
validation-only selection and threshold tuning, artifact hashes and measured reports.
Seeds 17/29/43 compare Logistic Regression, Random Forest and XGBoost; XGBoost had best
validation average precision each time. Selected-model final-test AP: 0.7313/0.5757/0.6427.
All results are synthetic_only=true, production_eligible=false. No real-world fraud or
adaptive-profile effectiveness claim. No source dataset has been approved/imported.

Validation: 289 tests passed, none skipped, 96% combined backend/ML coverage. Ruff/format,
strict mypy (77 source files), locked sync, package builds, Compose and Alembic checks
passed. Updated dependency audit found no known vulnerabilities. Two upstream deprecations
remain. Docker execution and remote CI are unverified. No known failing tests.

Optional ml dependency group: scikit-learn 1.8.0, XGBoost 3.2.0 (plus locked dependencies).
macOS libomp 22.1.8 installed for XGBoost. Backend runtime dependencies/schema unchanged.
Migration head 0004_profile_revisions; 15 business tables. PostgreSQL remains running
without TCP on owner-only /private/tmp socket, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md for restart/stop.
Sandboxed socket access may need approved execution; never substitute SQLite.

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
.venv/bin/python -m ml.src.training.experiment --output work/new-run --seed 17
When using uv run, pass --group ml for tests/types. Experiment output must not exist.

Important: ml/src/datasets/{synthetic,prepare}.py; ml/src/training/experiment.py;
tests/ml/test_experiment.py; ml/experiments/phase7-synthetic-v1/{README.md,seed*.json};
pyproject.toml; uv.lock; ADR-010/011/012. Full local artifacts are outside Git at
../../work/phase7/final-seed17, final-seed29 and final-seed43. Reports retain hashes,
versions, splits, model parameters and metrics. Joblib files may only be loaded from
trusted local runs. No model is registered or loaded in the API.

Dataset limitations: one event/customer/day, KZT only, authored distributions and static
bootstrap, two-day label delay, 0/2/120-minute arrival delay. Labels are stochastic latent
conditions, not rule outputs. Held-out customers have prior synthetic history, not cold
starts. Current work does not test adaptation, burst fraud, compromised feedback or
real-world performance. No calibrated probabilities or confidence intervals claimed.

First next: resolve Phase 7 external-data eligibility: license/version, schema, identity,
currency, chronology and label/arrival availability. ULB/PaySim are candidates only;
Kaggle terms were not verified. If facts cannot support behavior-v1, define a separate
honest benchmark contract instead of inventing fields. Freeze evaluation protocol before
new test inspection. Production selection remains blocked on defensible evidence.
Phase 8 can follow a validated baseline or an explicitly experimental demo boundary;
never silently promote current synthetic artifacts into business endpoints.

Preserve all earlier safeguards: pinned pre-decision profile versions, strict cutoffs,
no raw-intake admission, no invented historical commit times. Transactions remain immutable
RECEIVED. Trusted bootstrap/feedback/gate orchestration, corrections, low-weight admission,
human login, SHAP, frontend and outbox dispatch remain future work. Business routes fail
closed without configured expiring service credentials. Update PROJECT_STATUS.md,
NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending. Never fabricate metrics.
