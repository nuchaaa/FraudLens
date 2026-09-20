# FraudLens project status

Current checkpoint: **Phase 5 — Shared versioned feature engine complete.**
Next phase: **Phase 6 — Rule engine and reason codes.**
This is a research/portfolio checkpoint, not a deployed fraud product. Profile reads
do not establish legitimacy, score risk or admit transactions.

## Completed capabilities

- [x] Phase 5: shared pure `behavior-v1` extractor with 29 ordered finite features.
- [x] Explicit missing/insufficient history, finite MAD floor, strict baseline/activity separation.
- [x] Scoped read-only capture, pinned revisions and cutoff-safe PostgreSQL activity history.
- [x] Strict input artifacts, authenticated local capture and database-free exact replay.
- [x] Candidate/future/currency exclusion, device ties, late-arrival and batch parity tests.
- [x] ADR-010 documents feature formulas and limits on historical availability claims.

- [x] Phases 0–3: Python 3.13/uv, framework-free domain, PostgreSQL repositories/UoW,
  immutable history, concurrency, snapshots, outbox, authenticated transaction intake
  and retrieval, admin customer enrollment, atomic scoped idempotency/replay.
- [x] Phase 4: GET /api/v1/customers/{customer_id}/profiles/{currency}, using existing scopes.
- [x] Existing median/MAD/p95/mean and short/long windows reused without reimplementation.
- [x] Explicit UNINITIALIZED / EMPTY / INSUFFICIENT_HISTORY / SUFFICIENT_HISTORY states;
  absent statistics stay null and no profile is created by a read.
- [x] Per-window counts, observation frequency, local hour histogram, frequency-qualified
  typical hours and known recipients. Decimal statistics serialize as strings.
- [x] Historical queries require a pinned revision; strict event cutoffs exclude the
  candidate instant, lower window boundary and admissions from later versions.
- [x] Immutable profile revision journal preserves version-specific timezone/window policy.
- [x] Database admission guard seals committed revision sets; later transactions cannot append
  to a prior version. Existing row locking/version checks still govern updates.
- [x] Migration 0004_profile_revisions captures existing heads without inventing older versions.
- [x] Scope, cold-start, cutoff, currency, DST, revision, rollback, concurrency and upgrade tests.
- [x] ADR-009 and updated README, architecture, development and continuation files.

## Verification — 2026-09-20

- [x] **260 passed, 0 skipped, 2 upstream warnings; 97% combined branch/statement coverage.**
- [x] Actual PostgreSQL 17.10, including prior-phase regressions.
- [x] Migration upgrade/downgrade/metadata tests and upgrade with populated legacy profile data.
- [x] Concurrent reader pins its version before another writer commits; old versions exclude
  backdated later admissions and retain their original timezone/window policy.
- [x] Ruff lint/format and strict mypy pass (68 backend files).
- [x] pip-audit: no known vulnerabilities; dependencies/lockfile unchanged.
- [x] Source/wheel builds and Compose configuration pass.
- [x] Native database upgraded; head is 0004_profile_revisions, with 15 business tables.
- [x] Actual local Uvicorn/PostgreSQL smoke passed: cold start, populated pinned profile,
  median/MAD/p95, authentication and cutoff validation, plus prior intake smoke checks.
  Temporary HTTP server and smoke schema were cleaned up.
- [ ] Docker image execution remains unverified; Docker engine unavailable.
- [ ] Remote CI has not been pushed/run.

No known failing tests. The unchanged warnings concern Starlette's httpx TestClient
and AnyIO BlockingPortal deprecations. No predictive metrics have been measured or claimed.

## Environment and commands

Repository: outputs/fraudlens in the original workspace. PyCharm .idea files remain ignored.
The native disposable PostgreSQL cluster is still running without TCP, owner-only
socket /private/tmp, port 55439, database fraudlens_test.
Binaries: /opt/homebrew/opt/postgresql@17/bin.
Cluster: ../../work/fraudlens-postgres/data from repository root.

```sh
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
```

See development.md for restart/stop and expiring credential setup. Business endpoints
fail closed without FRAUDLENS_API_PRINCIPALS. No actual API token is committed or left
configured. Run .venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 after setup.
Sandboxed PostgreSQL access may need approved execution outside the sandbox.
Tests require a disposable *_test database and use a generated schema; the migration
smoke also upgrades its default schema. Never substitute SQLite.

## Important files

- backend/app/features/{context,engine,service,contracts}.py: shared versioned feature path.
- backend/adapters/features/{artifacts,__main__}.py: authenticated capture and offline replay.
- backend/adapters/database/transactions.py: scoped strict-cutoff history query.
- tests/unit/test_feature_engine.py; tests/integration/test_feature_capture.py.
- docs/adr/ADR-010-feature-context-and-availability.md: exact 29-feature contract.

- backend/app/profile/read_model.py: descriptive policy, status and summaries.
- backend/app/profile/service.py: scope, revision selection and strict cutoff orchestration.
- backend/api/profiles.py: validated profile HTTP contract.
- backend/adapters/database/profiles.py: latest/pinned revision reads through the domain port.
- backend/adapters/database/models.py: profile_revisions mapping plus earlier persistence.
- infra/migrations/versions/0004_profile_revisions.py: journal, backfill and admission guard.
- tests/integration/test_profile_api.py and test_migrations.py; tests/unit/test_profile_reads.py.
- docs/adr/ADR-009-profile-reads-and-history.md: exact temporal and trust contract.
- backend/app/profile/entities.py and gate.py: existing robust domain and initial safe gate.
- backend/app/features/contracts.py: existing ordered finite FeatureVector contract.
- backend/app/transaction/service.py, backend/api/transactions.py, backend/adapters/security.py:
  unchanged Phase 3 workflow/security; docs/adr/ADR-008-transaction-api-and-service-credentials.md.

## Decisions and remaining limitations

- Feature version behavior-v1 fixes 29 names/order, policy and imputation. Baseline minimum
  is five; absolute amount deviation divides by max(MAD, 0.01) with explicit floor flags.
- Raw activity spans strictly (candidate - 180 days, candidate), same customer/currency,
  excluding candidate ID. More than 10,000 rows fails explicitly instead of truncating.
- Local artifacts preserve exact input facts and Decimal strings. SHA256 is integrity,
  not authenticity; 16 MiB limit and create-only writes. No durable assessment persistence yet.
- A new capture can see late arrivals. Replay saved original contexts for past decisions;
  current event-time queries cannot reconstruct historical knowledge. Capture time is not
  commit time. Declared offline provenance requires independent dataset validation.
- Training batches and inference preparation call the same pure extractor. No trained model
  or predictive metrics exist. Capture/replay integration passed with PostgreSQL; replay
  succeeded with invalid DB/config settings, proving no live data dependency.

- Explicit as_of requires version; future cutoff -> 422, unknown revision -> 404, cutoff
  before selected revision's head -> 409. Default reads use current time/latest revision.
  Read interval is (as_of - window, as_of), per customer/currency.
- Version-pinned replay is NOT wall-clock knowledge reconstruction. Inference/research
  must retain the version captured before the original decision. A version selected today
  cannot be assumed available for past predictions. No historical commit times are invented.
- Migration backfills only current heads; older lost metadata cannot be recovered.
  Do not downgrade a real revision archive: re-upgrade restores current heads only.
- Revision admission checks use the full PostgreSQL transaction ID and physical xmin;
  writes use the top-level UoW without nested database savepoints. A DB owner can still
  bypass triggers. Restricted runtime grants remain security work.
- history_source=repository_admissions and admission_workflow_verified=false disclose
  the present provenance boundary. Customer creation/raw intake do not authorize learning.
- Trusted bootstrap needs independent reviewed source evidence, immutable transaction IDs,
  curator/time/policy provenance and atomic audit/events. No bootstrap/admission API exists.
  Authorized feedback and gate orchestration remain Phase 11/12.
- Five-observation minimum and typical-hour count/share thresholds (2 / 10%) are
  uncalibrated descriptive policies. SUFFICIENT_HISTORY is not a risk/trust verdict.
- Observation frequency is admitted count / configured window days, not raw intake velocity.
  Phase 5 supplies bounded raw device/recipient activity and velocity; recipient account age
  and external history completeness are unavailable.
- Cold start, low-weight admission, compromised confirmations and corrections/retractions
  remain unresolved research debt. Reads preserve quarantine/fraud exclusion.
- Transactions remain immutable RECEIVED records. Evaluation needs separate derived state
  or an append-only lifecycle; no risk API, trained ML, SHAP, human login or frontend exists.
- Outbox dispatch/claims/consumer deduplication, idempotency retention, centralized revocation,
  rate limits, database grants and deployment hardening remain unfinished.
- Service credentials are configuration snapshots; rotate while retaining principal UUID
  and restart all processes to apply revocation/scope changes. Remote use requires TLS.

## Exact next tasks

1. Read this status, specification, development.md and ADR-010; preserve completed Phases 0–5.
2. Phase 6: inspect existing rules Specification/RuleResult/RuleVersion contracts and risk
   reasons/strategies. Implement deterministic versioned rules with stable reason codes.
3. Define missing-history behavior and explicit experimental thresholds. Rules must consume
   the captured feature contract without querying newer facts or automatically admitting data.
4. Test exact boundaries, cold starts, deterministic explanations, version compatibility and
   context replay. Do not label heuristic outputs calibrated fraud probabilities.
5. Keep rule evaluation separate from later ML inference and atomic assessment persistence;
   plan immutable transaction evaluation state explicitly. Never invent model metadata.
6. Run checks and update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
