Continue FraudLens from completed Phase 12 — safe experimental profile learning.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-018-safe-profile-learning-authorization.md, ADR-017, ADR-009 and
docs/research/protocol.md. Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; backend/app framework-free, backend/api HTTP,
backend/adapters infrastructure; ml/src offline and excluded from serving wheel.
Phases 0–12 engineering checkpoints complete; production behavioral validation OPEN.
No production risk API, human login, frontend or outbox dispatcher exists.

Phase 12 adds disabled-by-default, admin-only profile-learning authorization. Feedback alone
does not learn. The admin must differ from terminal reviewers; cases must be closed, have one
terminal verdict and be unused. Cold bootstrap requires 5–100 legitimate cases for the same
customer/currency, evaluations captured with no profile, at least two reviewers, one 180-day
window and no amount >=10x the set median. It creates version 1 only when no profile exists.

Existing-profile admission requires verified provenance, an evaluation captured against the
exact current profile version, chronological event time and ACCEPT from the existing pure gate.
Exceptional amounts, late review, stale captures, insufficient history and legacy unverified
profiles are durably quarantined without changing the profile. Confirmed fraud is durably
excluded. Raw intake, enrollment, scores, suggested ALLOW and one verdict never authorize learning.

Learning decision/evidence, optional profile observation/revision, audit, outbox and exact
idempotent response commit atomically. PostgreSQL makes learning records append-only, binds
verified profile heads/revisions to matching ACCEPT decisions, prevents case reuse and checks
review/evaluation identities. Profile reads expose admission_workflow_verified, policy version
and learning decision ID. Legacy profiles remain unverified; no provenance is invented.

Low-weight updates are not implemented because current observations have no weights.
Corrections/retractions are not implemented because append-only history needs explicit
superseding records and replay semantics. Separation of one admin/two reviewers does not prove
resistance to collusion or compromised accounts. Thresholds remain uncalibrated.

Migration head: 0006_safe_profile_learning; 21 business tables. Dependencies unchanged.
Validation: 447 tests passed, zero skipped, 95% combined backend/ML coverage on PostgreSQL
17.10. Ruff/format and strict mypy (100 source files), builds, Compose configuration,
Alembic upgrade/check and migration/schema tests passed. Two upstream deprecation warnings
remain. Prior clean dependency audit applies because the lockfile is unchanged. Docker
runtime and remote CI remain unverified. No new predictive metrics or production claims.

PostgreSQL: owner-only /private/tmp socket, no TCP, port 55439, database fraudlens_test;
cluster ../../work/fraudlens-postgres/data. See development.md. Never use SQLite.
Business API fails closed without FRAUDLENS_API_PRINCIPALS. Experimental writes fail closed
unless FRAUDLENS_EXPERIMENTAL_ENABLED=true. Sandbox socket access may need approval.

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

Important files: backend/app/profile/{learning,gate,entities,service}.py;
backend/api/learning.py; backend/adapters/database/{learning,profiles,models,uow}.py;
infra/migrations/versions/0006_safe_profile_learning.py;
tests/integration/test_profile_learning_api.py;
docs/adr/ADR-018-safe-profile-learning-authorization.md;
backend/app/shared/events.py; backend/adapters/database/history.py.

Next: Phase 13 — Outbox delivery and operational reliability. Inspect current outbox rows,
repository and event contracts. Define PostgreSQL claiming/leases, retry/backoff, crash recovery,
dead-letter visibility and consumer deduplication before implementing a worker. Preserve the
truthful at-least-once boundary: never claim exactly-once external delivery. Delivery happens
after business commit and must not mutate immutable business history.

Test concurrent claimers, lease expiry, bounded batches, retry state, crashes before/after
external handling, acknowledgement and published immutability using PostgreSQL and a local
recording handler—no real external side effects. Keep profile weights/corrections, human login,
deployment hardening and production behavioral validation as separate future work.

Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate trust provenance, calibrated probabilities, delivery guarantees or metrics.
