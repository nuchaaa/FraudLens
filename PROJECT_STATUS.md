# FraudLens project status

Current checkpoint: **Phase 7 — Synthetic and external retrospective benchmark checkpoints complete.**
Next work: **Phase 8 explicitly experimental inference; production behavioral validation remains open.**
This is a research/portfolio checkpoint, not a deployed fraud product. Profile reads
do not establish legitimacy, score risk or admit transactions.

## Completed capabilities

- [x] Public ULB metadata resolves version 3 and listed ODbL/DbCL terms; source/CSV hashes saved.
- [x] Strict bounded fetch/import, quoted CSV support, independent ulb-pca-v1 feature contract.
- [x] Frozen day-based split and label-independent feature-duplicate policy; no invented history.
- [x] Fixed LR/RF/XGBoost comparison, validation-only selection, final selected-model test.
- [x] 15 new tests plus full prior regressions; source notice, ADR-013 and measured report.

- [x] Phase 7 engineering checkpoint: original deterministic synthetic event generator,
  event/arrival/label clocks, static authored bootstrap and chronological/customer splits.
- [x] Production feature reuse; no target-derived admission; late-arrival replay exclusion.
- [x] Logistic Regression, Random Forest, XGBoost comparisons for seeds 17/29/43.
- [x] Validation-only selection/thresholds; final test and held-out customers evaluated once
  per recorded run for the selected model. No production promotion.
- [x] Reproducibility artifacts/hashes, measured reports and seven ML pipeline tests.
- [x] Optional ML group, CI definition updated, ADR-012 and dataset suitability review.
- [x] ULB v3 license/version evidence, pinned import and separate ulb-pca-v1 benchmark.
- [ ] Suitable point-in-time behavioral dataset and production model selection.

- [x] Phase 6: rules-v1, five deterministic specifications with stable reason codes.
- [x] Explicit MATCHED / NOT_MATCHED / NOT_EVALUATED outcomes, evidence and missing flags.
- [x] Configurable experimental policy retained with canonical SHA256 fingerprint.
- [x] Pure captured-context evaluation and database-free local rule replay CLI.
- [x] 22 additional tests for boundaries, missing data, compatibility and exact replay.
- [x] ADR-011 defines semantics; no new database tables, dependencies or HTTP routes.

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

## Verification — 2026-09-20–21

- [x] **304 passed, 0 skipped, 2 upstream warnings; 96% combined backend/ML coverage.**
- [x] Actual PostgreSQL 17.10, including prior-phase regressions.
- [x] Migration upgrade/downgrade/metadata tests and upgrade with populated legacy profile data.
- [x] Concurrent reader pins its version before another writer commits; old versions exclude
  backdated later admissions and retain their original timezone/window policy.
- [x] Ruff lint/format and strict mypy pass (81 backend/ML source files).
- [x] pip-audit: no known vulnerabilities; updated optional ML dependencies audited.
- [x] Source/wheel builds and Compose configuration pass.
- [x] Native database upgraded; head is 0004_profile_revisions, with 15 business tables.
- [x] Actual local Uvicorn/PostgreSQL smoke passed: cold start, populated pinned profile,
  median/MAD/p95, authentication and cutoff validation, plus prior intake smoke checks.
  Temporary HTTP server and smoke schema were cleaned up.
- [ ] Docker image execution remains unverified; Docker engine unavailable.
- [ ] Remote CI has not been pushed/run.

No known failing tests. The unchanged warnings concern Starlette's httpx TestClient
and AnyIO BlockingPortal deprecations. Synthetic and external retrospective metrics are recorded; no production behavioral performance is claimed.

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
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
UV_CACHE_DIR=../../work/uv-cache ../../work/bootstrap/bin/uv build --offline
```

Install `uv sync --locked --group ml` for the full test suite.
See development.md for restart/stop and expiring credential setup. Business endpoints
fail closed without FRAUDLENS_API_PRINCIPALS. No actual API token is committed or left
configured. Run .venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 after setup.
Sandboxed PostgreSQL access may need approved execution outside the sandbox.
Tests require a disposable *_test database and use a generated schema; the migration
smoke also upgrades its default schema. Never substitute SQLite.

## Important files

- ml/src/datasets/ulb.py; ml/src/features/ulb.py; ml/src/training/ulb_benchmark.py.
- tests/ml/test_ulb_benchmark.py; ml/experiments/ulb-retrospective-v1/{README.md,report.json}.
- docs/research/ulb-{benchmark-protocol.md,NOTICE.md,source-metadata.json,source-manifest.json}.
- docs/adr/ADR-013-external-retrospective-benchmark.md.

- ml/src/datasets/{synthetic,prepare}.py; ml/src/training/experiment.py.
- tests/ml/test_experiment.py; ml/experiments/phase7-synthetic-v1/{README.md,seed*.json}.
- docs/adr/ADR-012-offline-experiment-boundaries.md; docs/research/dataset-assessment.md.
- pyproject.toml/uv.lock: optional ml group; strict mypy now includes ML source.

- backend/app/rules/engine.py: policy, specifications, outcomes and pure context evaluation.
- backend/adapters/rules/__main__.py: offline rule replay CLI.
- tests/unit/test_rule_engine.py; docs/adr/ADR-011-deterministic-rules.md.

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

- ULB v3 is eligible only for an anonymized retrospective benchmark, not behavior-v1.
  Unknown customer/currency/device/arrival/label availability and PCA fitting scope are
  explicit limitations. No held-out-customer or adaptation claim can be made.
- Import: 284,807 rows; 9,144 later identical feature tuples excluded independently of labels.
  Train/validation/test = 140,216 / 46,357 / 89,090; boundaries 86,400 / 129,600 seconds.
- Logistic Regression won validation AP. At frozen validation threshold 0.95, final-test
  AP=0.733432, precision=0.274854, recall=0.824561, F1=0.412281, FPR=0.002787.
  These are measured retrospective results, not a production policy or calibrated probability.
- Source: ../../work/phase7/ulb-v3/creditcard.csv; complete artifacts:
  ../../work/phase7/ulb-benchmark-v1-run2. The first attempt stopped pre-training on quoted
  numeric CSV parsing; the fix was tested without changing the evaluation protocol.
- Dependencies/schema unchanged this session. Prior clean dependency audit still applies
  to the unchanged lockfile; it was not rerun. API loads no model and retains fail-closed access.

- Synthetic models are trained and measured, but production_eligible=false. XGBoost won
  validation AP for all three seeds. Test AP ranged 0.5757–0.7313; this reflects authored
  distributions only. No external generalization or safe-adaptation result is claimed.
- Full local artifacts: ../../work/phase7/final-seed17, final-seed29 and final-seed43.
  Committed JSON reports contain hashes; raw data/model files stay outside Git.
- Original generator uses one event/customer/day, KZT, static synthetic bootstrap, two-day
  label delay and 0/2/120-minute arrivals. Held-out customers have authored prior history.
- Tests use the optional ml group (`uv sync --locked --group ml`). macOS XGBoost required
  libomp 22.1.8, now installed via Homebrew. API dependencies and DB schema are unchanged.

- rules-v1 requires exact behavior-v1 order/version. Five codes: AMOUNT_ANOMALY,
  NEW_RECIPIENT, HIGH_VELOCITY, UNUSUAL_TIME and DEVICE_CHANGED.
- Default inclusive thresholds: 10x admitted median and five prior transfers in five
  minutes. Both are uncalibrated. Full policy plus fingerprint accompany each report.
- Missing history means NOT_EVALUATED; empty reasons are not a safe/fraud-free verdict.
  No rule score, probability, automatic action or durable assessment is produced.
- Blacklist checks are deferred until an explicit authoritative versioned input exists.

- Feature version behavior-v1 fixes 29 names/order, policy and imputation. Baseline minimum
  is five; absolute amount deviation divides by max(MAD, 0.01) with explicit floor flags.
- Raw activity spans strictly (candidate - 180 days, candidate), same customer/currency,
  excluding candidate ID. More than 10,000 rows fails explicitly instead of truncating.
- Local artifacts preserve exact input facts and Decimal strings. SHA256 is integrity,
  not authenticity; 16 MiB limit and create-only writes. No durable assessment persistence yet.
- A new capture can see late arrivals. Replay saved original contexts for past decisions;
  current event-time queries cannot reconstruct historical knowledge. Capture time is not
  commit time. Declared offline provenance requires independent dataset validation.
- Training batches and inference preparation call the same pure extractor. Offline synthetic models and measured reports exist, all ineligible for production. Capture/replay integration passed with PostgreSQL; replay
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
  or an append-only lifecycle; no risk API, serving ML, SHAP, human login or frontend exists.
- Outbox dispatch/claims/consumer deduplication, idempotency retention, centralized revocation,
  rate limits, database grants and deployment hardening remain unfinished.
- Service credentials are configuration snapshots; rotate while retaining principal UUID
  and restart all processes to apply revocation/scope changes. Remote use requires TLS.

## Exact next tasks

1. Read status/specification/runbook, ADR-010/012/013, source notice and both measured reports.
2. Begin Phase 8 with an explicitly experimental inference boundary: inspect FraudModel,
   FraudPrediction and ModelVersion contracts and actual saved synthetic behavior-v1 artifacts.
3. Design a trusted artifact manifest/loader with exact hash, model/feature versions/order,
   training provenance and experimental eligibility. Never load arbitrary uploaded pickle.
4. Implement the appropriate model adapter and offline captured-context replay with parity,
   incompatible/corrupt artifact, feature-version and failure tests; no invented model metadata.
5. Keep ulb-pca-v1 separate: no mapping from PCA components to customer behavior. Do not
   promote either benchmark into production or introduce unprotected business writes.
6. Durable atomic evaluation/context persistence and immutable transaction lifecycle need
   their own design. Admission, production validation and adaptive research remain unfinished.
7. Run checks and update PROJECT_STATUS.md, NEXT_SESSION_PROMPT.md and SESSION_LOG.md.
