Continue FraudLens from completed Phase 13 — leased local outbox delivery.
Read PROJECT_STATUS.md first, then docs/PROJECT_SPECIFICATION.md, development.md,
docs/adr/ADR-019-outbox-delivery.md, ADR-018, ADR-017 and docs/research/protocol.md.
Do not redo completed work.

Repository: /Users/nurasilkirgizbek/Documents/Codex/2026-09-19/if-my-chat-gpt-open-my-2/outputs/fraudlens
Architecture: modular monolith; framework-free backend/app, HTTP backend/api,
infrastructure backend/adapters; ml/src offline and excluded from serving wheel.
Phases 0–13 engineering checkpoints complete; production behavioral validation OPEN.
No production risk API, human login or frontend exists. Experimental evaluation,
review and independently authorized profile-learning APIs remain opt-in and scoped.

Phase 13 adds a framework-free bounded dispatcher and PostgreSQL delivery queue:
SKIP LOCKED claims, fresh UUID fencing, database-clock leases, retry/backoff,
crash recovery, dead-letter visibility and immutable local consumer receipts.
The sole destination is local-recording-v1. No external messages, fraud actions,
automatic learning, fan-out or exactly-once external guarantee. Receipt commit and
acknowledgement are separate; redelivery deduplicates the receipt transactionally.

Default policy: 60-second lease, five total claims, exponential retries from 5 seconds
to 1 hour. Claim crashes count as attempts; expired final claims dead-letter. There
is no heartbeat, handler timeout, ordering guarantee or audited redrive. Unreadable
envelopes dead-letter as unsupported_envelope; unknown schema versions retry/fail.
CLI status shows counts, live/expired leases and at most 100 dead-letter details.
An empty run does not establish an empty backlog. All workers must use the same policy.
Legacy publication helpers cannot bypass leased/terminal records. Published events,
terminal delivery rows and receipts are immutable. Backfill does not invent receipts.

Migration head: 0007_outbox_delivery. 21 business + 2 operational tables, plus Alembic.
Validation: 479 passed, zero skipped, 94% combined backend/ML coverage on PostgreSQL.
Ruff/format, strict mypy (103 source files), Alembic upgrade/check, builds and Compose
configuration passed. Real local worker CLI subprocess run/status passed in a disposable
schema. Two upstream warnings remain. Dependencies unchanged; prior clean audit retained,
not rerun. Docker runtime and remote CI remain unverified. No predictive metrics added.

PostgreSQL 17.10 remains running: owner-only /private/tmp socket, no TCP, port 55439,
database fraudlens_test; cluster ../../work/fraudlens-postgres/data. See development.md.
Never use SQLite. Sandbox socket access may require approved execution.
Business API fails closed without FRAUDLENS_API_PRINCIPALS; experimental writes require
FRAUDLENS_EXPERIMENTAL_ENABLED=true. The worker is a local database-operator CLI, not
an HTTP endpoint or automatic API startup task; restrict its database/host access.

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
.venv/bin/python -m backend.adapters.events status
.venv/bin/python -m backend.adapters.events run --limit 100

Important files: backend/app/shared/{delivery,events}.py;
backend/adapters/database/{delivery,history,models}.py;
backend/adapters/events/__main__.py; infra/migrations/versions/0007_outbox_delivery.py;
tests/integration/test_outbox_delivery.py; tests/unit/test_delivery.py; ADR-019.
Existing workflow contracts: backend/api/{transactions,profiles,evaluations,learning}.py;
backend/app/evaluation/{contracts,service}.py; backend/app/profile/learning.py.

Next: Phase 14 — React/TypeScript/Vite analyst frontend. First inventory real endpoint
contracts and missing scoped paginated list/read projections. Build the console on real
retained data; never invent dashboard counts, scores, model health or research metrics.
Show experimental/uncalibrated labels, absent scores, loading/empty/error states and
accessible transaction/evaluation/case/profile views. Keep immutable RECEIVED transaction
status distinct from evaluations and review state. Preserve exact original explanations.

Design safe local service-credential handling without bundled secrets or persistent browser
tokens. Human login remains Phase 15; do not bypass scope/authentication/experimental opt-in.
Any review/learning controls need clear confirmation, idempotency, role checks and the same
reviewer/independent-admin separation as the API. Existing profile bootstrap needs 5–100
closed legitimate cases, two reviewers and independent admin; exceptional activity remains
quarantined. Verdict/intake/enrollment/model suggestions never independently authorize learning.

Low-weight updates/corrections, compromised/colluding confirmations, external consumers and
audited redrive, human login, runtime grants/deployment hardening and production behavioral
validation remain separate future work. Preserve pre-decision captured facts and profiles;
current captures cannot reconstruct past availability. ULB remains separate from behavior-v1;
native models are synthetic-only, uncalibrated and production-ineligible.

Update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md before ending.
Never fabricate provenance, calibrated probabilities, delivery guarantees or research metrics.
