Continue FraudLens from completed Phase 6 — deterministic rule engine.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-010-feature-context-and-availability.md, ADR-011-deterministic-rules.md
(in docs/adr) and docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Goal: explainable adaptive behavioral fraud detection with safe customer profiles.
Architecture: modular monolith; framework-free backend/app; HTTP backend/api;
infrastructure backend/adapters. Phases 0–6 complete. Authenticated intake/profile reads,
PostgreSQL UoW/idempotency, immutable revisions and 29 behavior-v1 features remain intact.
Phase 6 adds five rules-v1 specifications, stable reasons, evidence and explicit
MATCHED/NOT_MATCHED/NOT_EVALUATED outcomes, policy fingerprints and offline rule CLI.
No model, probabilities, risk API, durable evaluation workflow, SHAP, frontend, human
login, trusted admission API or outbox dispatcher. Transactions remain immutable RECEIVED.
Schema unchanged: 0004_profile_revisions, 15 business tables; dependencies unchanged.

Validation: 282 tests passed, zero skipped, 97% coverage on PostgreSQL 17.10.
Ruff/format, strict mypy (71 backend files), builds and Compose configuration passed.
Existing migration/schema tests passed in the full suite. Two upstream deprecations
remain; Docker runtime and remote CI unverified. No known failing tests or predictive metrics.
Previous dependency audit found no known vulnerabilities; no dependencies changed.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test.
Cluster ../../work/fraudlens-postgres/data; see development.md for restart/stop.
Sandbox socket access may require approved execution outside sandbox; never use SQLite.
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
.venv/bin/python -m backend.adapters.rules --help

Important: backend/app/rules/engine.py; backend/adapters/rules/__main__.py;
tests/unit/test_rule_engine.py; backend/app/features/{context,engine,service}.py;
backend/adapters/features/artifacts.py; docs/adr/ADR-010 and ADR-011.
Rule defaults: amount/median >=10; five prior transfers strictly within five minutes.
Thresholds uncalibrated; no aggregation/probability. Missing input suppresses a rule with
NOT_EVALUATED. Empty reasons do not prove legitimacy. Policies accompany their SHA256.
Feature version/order is strict; changed rules/messages require a new rule version.
No blacklist source exists, so blacklist checks are deferred.

Saved contexts pin original facts. Today's captures may contain late arrivals; event time
does not reconstruct historical knowledge. Require pre-decision profile versions and
source chronology. Raw history is same customer/currency, strictly prior, 180 days,
10,000-row cap; no silent truncation. Artifacts have integrity checks, not authenticity.
Future evaluation must atomically persist context/vector/assessment. Admission provenance
remains unverified. Never treat intake/enrollment or rule matches as learning permission.

Next: Phase 7 — dataset preparation and ML experiments. First inspect research protocol
and dataset suitability: license, labels, time, customer/currency identity, point-in-time
availability and missing fields. Use shared feature code only where source facts support
it. Compare Logistic Regression, Random Forest and XGBoost using leakage-safe splits,
appropriate imbalance handling and validation-only selection. Do not invent dataset
provenance or metrics; synthetic results cannot establish real-world performance.
Training is offline; model integration is Phase 8. Trusted bootstrap, feedback/gate
orchestration, low-weight admission, compromised confirmations and corrections remain open.
Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
