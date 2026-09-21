Continue FraudLens from completed Phase 9 — experimental Risk + Decision.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-015-experimental-risk-and-decision.md, ADR-014, ADR-010, ADR-011,
ADR-012 and docs/research/protocol.md. Do not redo completed work.
Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure; ml/src offline, excluded from serving wheel.
Phases 0–9 engineering checkpoints complete; production behavioral validation OPEN.
No HTTP risk/inference, durable evaluation workflow, SHAP or frontend exists.

Phase 9 adds pure rules-only/ML-only/hybrid composition, risk-v1-experimental policy,
complete policy fingerprint and offline replay CLI. Reuses existing rules/model/decision
ports. Rule weights in rules-v1 order: 0.40/0.15/0.25/0.10/0.10; complete rule score is
matched-weight sum divided by total weight. Hybrid default model_weight=0.5; decision
thresholds 0.35/0.65/0.85. All configurable, authored and uncalibrated; no test-set tuning.
Any NOT_EVALUATED rule makes rule_score null. Rules-only/hybrid then return
INSUFFICIENT_EVIDENCE with null score/level/action, preserving partial evidence.
ML-only can score missing-history indicators but still discloses unavailable rules.
All actions are suggestions: operational_action_executed=false, production_eligible=false,
calibrated=false, admission_workflow_verified=false. No fallback or learning permission.
Reports retain exact features, rules, settings, context/manifest fingerprints and clocks.

Phase 8 native XGBoost adapter remains pinned, synthetic-only, KZT/UTC/180-day/30-day scope.
Inference never loads pickle/joblib. Legacy trained_at remains unknown; do not fabricate
ModelVersion metadata. ULB ulb-pca-v1 remains separate and behaviorally incompatible.
No new predictive metrics, training or benchmark retuning occurred in Phase 9.

Validation: 365 tests passed, zero skipped, 96% combined backend/ML coverage.
Ruff/format, strict mypy (89 files), builds, Compose configuration and PostgreSQL
migration/schema tests passed. Actual native hybrid replay correctly abstained for the
saved first context with no prior activity. Two upstream warnings remain. Dependencies
unchanged; prior clean audit retained. Docker runtime and remote CI remain unverified.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md. Never use SQLite.
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
.venv/bin/python -m backend.adapters.risk --context ../../work/phase8/first-context.json --strategy hybrid --bundle ../../work/phase8/seed17 --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903
For rules-only use --strategy rules_only and omit model arguments. ML-only uses ml_only.

Important: backend/app/risk/service.py; backend/adapters/risk/__main__.py;
backend/app/decision/policy.py; backend/app/rules/engine.py;
backend/adapters/ml/{bundle,xgboost_model}.py; backend/app/fraud/{ports,service}.py;
tests/unit/test_risk_service.py; tests/ml/test_inference.py; ADR-015.
Native bundle: ../../work/phase8/seed17; original synthetic artifacts: ../../work/phase7/final-seed{17,29,43}.

Next: Phase 10 — experimental Explainability. Inspect existing contracts, captured vectors,
native Booster and risk results. Verify supported SHAP/native TreeSHAP APIs using primary
documentation. Define raw-margin versus uncalibrated-score semantics, feature ordering,
base value/additivity tolerance and separation from rule/hybrid scores. Implement offline
technical contributions plus factual readable explanations, with parity/additivity,
missingness/order/replay/failure tests. Audit dependencies if changed. No causal claims,
calibration claims, arbitrary pickle loading or silent production promotion.

Preserve pinned pre-decision profiles and strict cutoffs. Current captures do not reconstruct
past availability. Transactions remain immutable RECEIVED. ADR-015 records future atomic
evaluation/context/vector/audit/outbox/response design; do not force experimental results
into persistence contracts by inventing unknown model/profile metadata. Raw intake/enrollment
never authorizes learning. Trusted bootstrap, feedback/gate orchestration, low-weight updates,
corrections, human login, frontend and outbox dispatch remain open. No unprotected writes.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate research metrics.
