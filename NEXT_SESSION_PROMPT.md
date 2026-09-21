Continue FraudLens from completed Phase 11 — durable experimental evaluation and review.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-017-durable-experimental-evaluations-and-review.md, ADR-009, ADR-015,
ADR-016 and docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure; ml/src offline and excluded from serving wheel.
Phases 0–11 engineering checkpoints complete; production behavioral validation OPEN.
No production risk API, human login, frontend, trusted admission API or outbox dispatcher.

Phase 11 adds disabled-by-default authenticated experimental evaluation, cases and analyst
review. One PostgreSQL commit stores captured context, 29-value vector, rules/policy,
optional model manifest/explanation, scored or insufficient result, audit, outbox and exact
idempotent response. GET and retries return stored bytes without recomputation. Four new
tables are append-only with database envelope/lifecycle/feedback provenance guards.
Transactions remain immutable RECEIVED and profiles are never changed by evaluation/review.

Service/admin principals may evaluate transactions in customer scope. Analyst/admin may
create/review cases in scope. Strict transitions and expected versions reject conflicting
reviewers. Feedback records actor, verdict and comment but never authorizes learning,
executes an action or retrains a model. Rules-only has null model provenance. ML-only/hybrid
require the configured reviewed native bundle and independently pinned manifest digest.
Unknown legacy trained_at stays null. There is no model upload or serving pickle/joblib.

Migration head: 0005_experimental_reviews; 19 business tables. Dependencies unchanged.
Validation: 436 tests passed, zero skipped, 95% combined backend/ML coverage on PostgreSQL
17.10. Ruff/format and strict mypy (97 source files), builds, Compose configuration,
Alembic upgrade/check and migration/schema tests passed. Two upstream deprecation warnings
remain. Prior clean dependency audit applies because the lockfile is unchanged. Docker
runtime and remote CI remain unverified. No new predictive metrics or production claims.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md. Never use SQLite.
Business API fails closed without FRAUDLENS_API_PRINCIPALS. Experimental writes also fail
closed unless FRAUDLENS_EXPERIMENTAL_ENABLED=true. Sandbox socket access may need approval.

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

Important files: backend/app/evaluation/{contracts,service}.py;
backend/adapters/evaluation.py; backend/api/evaluations.py;
backend/adapters/database/{evaluations,models,uow}.py;
infra/migrations/versions/0005_experimental_reviews_experimental_reviews.py;
tests/integration/test_evaluation_api.py; docs/adr/ADR-017-durable-experimental-evaluations-and-review.md;
backend/app/profile/{entities,gate,service}.py; backend/adapters/database/profiles.py.

Evaluation requests accept only transaction/profile-version/strategy/manifest identity;
never accept caller scores, vectors, policies, explanations or arbitrary models. Authorization
precedes replay and the scoped idempotency lock precedes writes. Late arrivals may change a
new capture but cannot alter a stored evaluation. Current capture still cannot reconstruct
past knowledge unless the original context was retained. All risk scores/actions remain
uncalibrated, production_eligible=false and operational_action_executed=false.

Next: Phase 12 — Safe Adaptive Profile Update. First inspect the existing pure gate,
profile revision repository and new review provenance. Specify a separately authorized
feedback-to-gate workflow, trusted cold-start/bootstrap and correction/retraction semantics
before adding writes. Define ordinary versus low-weight admission and exceptional legitimate
quarantine without allowing repeated self-reinforcement or compromised confirmations.

Do not treat raw intake, customer enrollment, a risk score, suggested ALLOW or one analyst
verdict as permission to learn. Preserve immutable evaluation/case/feedback history and
profile revisions. Any future admission must atomically persist observation/revision/audit/
outbox/idempotent response and pass PostgreSQL authorization, rollback, replay, uniqueness,
concurrency and history tests. Thresholds remain uncalibrated. Outbox dispatch, human login,
deployment hardening and production behavioral validation remain future work.

Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate trust provenance, calibrated probabilities or research metrics.
