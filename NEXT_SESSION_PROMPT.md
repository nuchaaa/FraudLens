Continue FraudLens from completed Phase 10 — experimental native explainability.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-016-native-model-explanations.md, ADR-015, ADR-014 and docs/research/protocol.md.
Do not redo completed work.
Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure; ml/src offline, excluded from serving wheel.
Phases 0–10 engineering checkpoints complete; production behavioral validation OPEN.
No HTTP evaluation, durable evaluation workflow, human login or frontend exists.

Phase 10 adds an ExplainableFraudModel port, checked ModelExplanation contract and native
XGBoost TreeSHAP via the existing trusted adapter. Add --explain to the offline risk CLI.
No shap-package dependency was needed. All 29 contributions plus bias reconstruct raw model
margin/log-odds; sigmoid links margin to the uncalibrated model score. Never interpret these
as probability contributions or multiply them into hybrid/rule-score explanations.
Numerical tolerances: margin abs=1e-5/rel=1e-6; score abs=1e-6. Exact vector/model identity
must match the risk prediction. Wrong shape/order, nonfinite values and failed reconstruction
raise errors. Top-five readable contributions have stable ordering and label unavailable
history placeholders explicitly. Rule reasons remain separate; no causal claims.
Rules-only returns no model explanation; hybrid can explain its model while still abstaining.

Phase 9 remains unchanged: rule weights 0.40/0.15/0.25/0.10/0.10, hybrid model_weight=0.5,
thresholds 0.35/0.65/0.85, configurable and uncalibrated. Any unavailable rule makes rule_score
null; rules-only/hybrid return INSUFFICIENT_EVIDENCE with null score/level/action. ML-only
may score explicit missing-history features but discloses unavailable evidence. No fallback.
All actions are suggestions, never executed; production_eligible=false, calibrated=false.

Validation: 409 tests passed, zero skipped, 96% combined backend/ML coverage.
Ruff/format, strict mypy (91 files), builds, Compose configuration and PostgreSQL migration
checks passed. All 2,400 original hash-pinned seed17 prepared vectors passed reconstruction:
max margin difference 2.2863969206809998e-6, max sigmoid score difference 8.22891939034065e-8.
These are numerical software checks, not new predictive metrics or independent SHAP validation.
Actual native hybrid --explain replay passed. Two upstream warnings remain. Dependencies
unchanged; prior clean audit retained. Docker runtime and remote CI remain unverified.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md. Never substitute SQLite.
Schema unchanged: 0004_profile_revisions, 15 business tables. Business API fails closed
without FRAUDLENS_API_PRINCIPALS. Sandbox socket access may require approved execution.

Commands from repository root:
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv sync --locked --group ml
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
.venv/bin/python -m backend.adapters.risk --context ../../work/phase8/first-context.json --strategy hybrid --explain --bundle ../../work/phase8/seed17 --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903
Rules-only uses --strategy rules_only without model arguments; ML-only uses ml_only.

Important: backend/app/explainability/{contracts,service}.py; backend/adapters/ml/xgboost_model.py;
backend/adapters/risk/__main__.py; backend/app/risk/service.py; tests/unit/test_explainability.py;
tests/ml/test_inference.py; ADR-015/016; ml/experiments/phase10-explanations/verification.json.
Local numerical summary/full replay: ../../work/phase10/treeshap-seed17/{verification.json,replay.json}.
Native bundle remains ../../work/phase8/seed17; synthetic originals remain ../../work/phase7/final-seed{17,29,43}.
Model scope KZT/UTC/180-day/30-day; legacy trained_at remains unknown. ULB stays incompatible.
Never load arbitrary pickle/joblib or retune on previously evaluated benchmark test data.

Next: Phase 11 Cases / Feedback preparation. Inspect existing case/feedback/repository
contracts first. Before linking cases, implement the durable experimental evaluation foundation
outlined in ADR-015: append-only scored/insufficient-evidence records, honest absent profile/
model and unknown-training-time provenance, scoped authorization/idempotency, atomic captured
context/vector/policy/explanation/result/audit/outbox/response storage. Plan compatible migrations;
do not invent required RiskAssessment/ModelVersion metadata. Test rollback, immutability,
concurrency and replay conflicts using PostgreSQL. Then connect scoped case and analyst-feedback
workflows with existing strict transitions and immutable actor history. No direct learning.

Preserve pinned pre-decision profiles and strict cutoffs; current captures cannot reconstruct
past availability. Transactions remain immutable RECEIVED. Raw intake/enrollment never establishes
legitimacy. Trusted bootstrap, feedback/gate orchestration, low-weight updates, corrections,
human login, frontend and outbox dispatch remain open. No unprotected writes or production promotion.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate research metrics.
