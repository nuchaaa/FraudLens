# FraudLens project status

Current checkpoint: **Phase 15 in progress — human identity/security foundation tested. Phase 14 remains complete.**
Next work: **PostgreSQL human accounts/session workflows, HTTP cookies/CSRF and frontend login. Production behavioral validation remains open.**
This is a research/portfolio checkpoint, not a deployed fraud product. Profile reads
do not establish legitimacy, score risk or admit transactions.

## Completed capabilities

- [x] Phase 15 foundation: threat model and proposed ADR-021 human identity/session design.
- [x] Pure human-account scope and session expiry/rotation/revocation policies.
- [x] Explicit Argon2id password adapter, bounded Unicode inputs and secret-safe repr.
- [x] 32 new tests; full regression: 512 passed, zero skipped, 94% combined coverage.
- [ ] PostgreSQL identity/session/consumed-refresh/throttle persistence and atomic audit.
- [ ] Provisioning/recovery CLI, login/refresh/logout/session HTTP, cookies and CSRF.
- [ ] Frontend human login, concurrent HTTP tests, runtime DB grants/deployment hardening.
- Existing console still uses service credentials. No human authentication is enabled yet.

- [x] Phase 14: responsive React 19/TypeScript/Vite local analyst console with six sections.
- [x] Exact scoped PostgreSQL summary and keyset-paginated transaction/evaluation/case worklist.
- [x] Retained explanations, profile reads and explicit-confirmation versioned case review.
- [x] In-memory-only pasted credential; no bundled token, URL/browser storage or external assets.
- [x] Loading/empty/error states, responsive/accessibility basics, nginx CSP and same-origin proxy.
- [x] Frontend ESLint/Vitest/type/build/audit, Compose/CI integration, visual browser inspection.
- [x] ADR-020; no schema migration, model promotion, fabricated metric or dependency change to Python.

- [x] Phase 13: bounded worker through framework-free delivery ports; explicit local operator CLI.
- [x] PostgreSQL SKIP LOCKED claims, database-clock leases, UUID fencing and crash recovery.
- [x] Capped retry/backoff, dead-letter visibility, unknown-envelope isolation and immutable terminals.
- [x] Local recording consumer with durable receipt deduplication; no external effects or fan-out.
- [x] Migration 0007_outbox_delivery; 21 business tables plus 2 operational tables.
- [x] ADR-019, PostgreSQL concurrency/crash/rollback/migration tests and CLI subprocess smoke.

- [x] Phase 12: separately authorized, idempotent profile-learning HTTP workflows.
- [x] Reviewed cold-start bootstrap: 5–100 cases, two reviewers, independent admin.
- [x] Exact-profile-version ordinary admission through the existing conservative pure gate.
- [x] Exceptional/stale/insufficient evidence quarantined; confirmed fraud excluded.
- [x] Immutable learning decisions/evidence and verified provenance on learning-created revisions.
- [x] Atomic profile/revision/evidence/audit/outbox/response writes and concurrency controls.
- [x] Legacy profiles remain unverified; weights/corrections explicitly unavailable.
- [x] ADR-018; migration head 0006_safe_profile_learning; no dependency changes.

- [x] Phase 11: opt-in authenticated evaluation and analyst case/review HTTP workflows.
- [x] Atomic context/vector/policy/result/explanation/audit/outbox/exact-response persistence.
- [x] Truthful scored or insufficient-evidence envelopes with nullable model/profile provenance.
- [x] Scoped durable idempotency, restart replay, optimistic review concurrency and rollback.
- [x] Four append-only PostgreSQL tables with envelope, lifecycle and feedback provenance guards.
- [x] Feedback remains evidence only: no transaction change, action execution, learning or admission.
- [x] ADR-017; migration head 0005_experimental_reviews; feature disabled by default.

- [x] Phase 10: framework-free explanation contract and native XGBoost TreeSHAP adapter.
- [x] Exact vector/model binding, finite shape checks and margin/link reconstruction validation.
- [x] All 29 raw-margin contributions plus bias, stable top-five readable messages and missing masks.
- [x] Optional --explain risk replay for every strategy, keeping rule/hybrid evidence separate.
- [x] 44 additional tests; all 2,400 original seed17 vectors passed numerical reconstruction.
- [x] ADR-016 and retained numerical verification; no dependencies/schema/API changes.

- [x] Phase 9: pure rules-only, ML-only and hybrid composition on one captured context.
- [x] Versioned configurable rule weights, hybrid weight and decision thresholds; full policy hash.
- [x] Explicit null scores/actions for insufficient required rule evidence; no silent fallback.
- [x] Stable rule reasons/evidence, input fingerprint, real model identity and replay clocks.
- [x] Offline risk CLI, 36 new tests, ADR-015 and future atomic evaluation design boundary.
- [x] Every suggested action remains experimental and unexecuted; no API/schema/dependency changes.

- [x] Phase 8: native XGBoost FraudModel adapter and pure captured-context inference service.
- [x] Independently pinned manifests, exact model/report hashes, feature order and runtime checks.
- [x] Restricted exporter for three reviewed synthetic runs; inference never loads pickle/joblib.
- [x] Explicit KZT/UTC/180-day/30-day scope and uncalibrated experimental output flags.
- [x] Native seed17 export matches all 2,400 saved scores exactly (maximum difference 0.0).
- [x] Database-free replay CLI, 25 new tests, ADR-014 and committed manifest/parity evidence.
- [ ] HTTP inference, durable model registration and atomic context/vector/assessment persistence.

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

## Verification — 2026-09-20–22

- [x] **512 passed, 0 skipped, 2 upstream warnings; 94% combined backend/ML coverage.**
- [x] Actual PostgreSQL 17.10, including prior-phase regressions.
- [x] Migration upgrade/downgrade/metadata tests and upgrade with populated legacy profile data.
- [x] Concurrent reader pins its version before another writer commits; old versions exclude
  backdated later admissions and retain their original timezone/window policy.
- [x] Ruff lint/format and strict mypy pass (111 backend/ML source files).
- [x] Frontend ESLint, 2 Vitest tests, TypeScript production build and npm audit pass.
- [x] Browser visual inspection passed for the responsive connection screen; no external assets.
- [x] Phase 15 locked dependency audit: no known vulnerabilities, including the ML/dev groups.
  Added argon2-cffi 25.1.0 and locked bindings/cffi/pycparser; existing versions unchanged.
- [x] Source/wheel builds and Compose configuration pass.
- [x] Native database upgraded; head is 0007_outbox_delivery, with 23 non-Alembic tables.
- [x] Actual worker CLI subprocess recorded/acknowledged an event and reported status in a disposable schema.
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

- backend/app/identity/policy.py: pure account/session policy; not HTTP authentication.
- backend/adapters/passwords.py; tests/unit/test_identity_policy.py: Argon2id and policy tests.
- docs/security/threat-model.md; docs/adr/ADR-021-human-identity-and-sessions.md: design and release gates.

- frontend/src/{App,pages,api,types,styles}.tsx: local console, read views and review controls.
- frontend/{package.json,Dockerfile,nginx.conf}: locked toolchain, static serving and same-origin proxy.
- backend/app/console/{contracts,service}.py: framework-free scoped console read boundary.
- backend/adapters/database/console.py; backend/api/console.py: exact summary and worklist endpoints.
- tests/integration/test_evaluation_api.py; frontend/src/App.test.tsx: scope/cursor/UI tests.
- docs/adr/ADR-020-analyst-console-and-scoped-read-model.md.

- backend/app/shared/delivery.py: queue port, policy, claim and bounded dispatcher.
- backend/adapters/database/delivery.py: PostgreSQL leases, retries, status and local consumer.
- backend/adapters/events/__main__.py: explicit `run --limit` and `status` operator CLI.
- infra/migrations/versions/0007_outbox_delivery.py; tests/integration/test_outbox_delivery.py.
- docs/adr/ADR-019-outbox-delivery.md: delivery contract and operational limits.

- backend/app/profile/learning.py: independent authorization, bootstrap and gate orchestration.
- backend/api/learning.py; backend/adapters/database/learning.py: opt-in HTTP and persistence.
- backend/app/profile/entities.py; backend/adapters/database/profiles.py: revision provenance.
- infra/migrations/versions/0006_safe_profile_learning.py: immutable learning evidence and guards.
- tests/integration/test_profile_learning_api.py; docs/adr/ADR-018-safe-profile-learning-authorization.md.

- backend/app/evaluation/{contracts,service}.py: truthful envelopes and atomic workflows.
- backend/adapters/evaluation.py: server-controlled rules/native-model composition.
- backend/api/evaluations.py: opt-in scoped evaluation/case/review routes.
- backend/adapters/database/evaluations.py and models.py: durable repositories/mappings.
- infra/migrations/versions/0005_experimental_reviews_experimental_reviews.py: four
  append-only tables and database provenance/lifecycle guards.
- tests/integration/test_evaluation_api.py; docs/adr/ADR-017-durable-experimental-evaluations-and-review.md.

- backend/app/explainability/{contracts,service}.py: typed port, invariants and readable explanation.
- backend/adapters/ml/xgboost_model.py: native TreeSHAP; backend/adapters/risk/__main__.py: --explain.
- tests/unit/test_explainability.py; tests/ml/test_inference.py: contract/native/CLI tests.
- docs/adr/ADR-016-native-model-explanations.md; ml/experiments/phase10-explanations/verification.json.

- backend/app/risk/service.py: policy, fingerprint, missingness and three-mode composition.
- backend/adapters/risk/__main__.py: offline configurable policy/model replay.
- tests/unit/test_risk_service.py; tests/ml/test_inference.py: domain and native CLI checks.
- docs/adr/ADR-015-experimental-risk-and-decision.md: semantics and persistence design boundary.

- backend/adapters/ml/{bundle,xgboost_model,__main__}.py: strict native loading and replay.
- backend/app/fraud/service.py: framework-free scoped captured-context prediction.
- ml/src/training/export_model.py: reviewed, pinned, one-time native conversion.
- tests/ml/test_inference.py; docs/adr/ADR-014-experimental-native-inference.md.
- ml/experiments/phase8-native-export/{README.md,manifest.json,parity.json}.

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

- Learning requires a closed case with exactly one terminal verdict and an admin authorizer
  distinct from the reviewer. A case is single-use evidence. Feedback alone never learns.
- Bootstrap requires 5–100 legitimate cases for one customer/currency, at least two reviewers,
  absent-profile captures, one 180-day window and no amount >=10x the set median. These are
  conservative authored thresholds, not calibration or proof against collusion.
- Existing-profile legitimate admission requires verified provenance, the exact current
  captured profile version, chronological event time and an ACCEPT from the existing gate.
  Exceptional, late, stale-version, insufficient-history and legacy-profile inputs quarantine.
  Confirmed fraud is excluded. Profile versions advance only for ACCEPT.
- Learning decision/evidence, optional profile observation/revision, audit, outbox and exact
  response commit atomically. PostgreSQL binds verified heads to matching immutable ACCEPT
  decisions and rejects history changes. Concurrent bootstrap/update writers serialize.
- Legacy profiles are migrated with `admission_workflow_verified=false`; provenance is never
  invented. Reads expose policy/decision identity for verified revisions.
- Low-weight updates remain unavailable because observations have no weight. Corrections and
  retractions remain unavailable because append-only history needs superseding records and
  replay semantics. No score, ALLOW suggestion, intake, enrollment or verdict bypasses this.

- `FRAUDLENS_EXPERIMENTAL_ENABLED` defaults false. Rules-only can run without a model;
  ML-only/hybrid require the configured reviewed native bundle and independent manifest pin.
- Evaluation input is a transaction/profile version/strategy, not caller scores or vectors.
  Capture and evaluation use one UoW; exact response bytes are stored and replayed after restart.
- `experimental_evaluations` truthfully permits absent profile/model provenance and unknown
  legacy `trained_at`. SCORED requires finite score/decision fields; INSUFFICIENT_EVIDENCE
  requires them null. All results remain production-ineligible and execute no action.
- Experimental cases link only to stored evaluations. Analyst/admin scope, strict lifecycle,
  expected versions and row locks govern review. Terminal feedback must match its transition
  actor/time. PostgreSQL rejects UPDATE/DELETE/TRUNCATE for all four Phase 11 tables.
- Evaluation and review each atomically commit business evidence, audit, outbox and durable
  idempotent response. Outbox delivery supports local recording only. Feedback never directly admits profile
  history, changes immutable RECEIVED transactions, retrains a model or proves legitimacy.
- API/PostgreSQL integration includes restart replay, late arrivals, rollbacks, malformed
  envelopes, authorization, concurrent retries/reviewers and native-model provenance. No new
  predictive metrics, tuning or production validation occurred.

- explanation-v1-experimental uses native non-approximate XGBoost TreeSHAP with all trees.
  Full ordered contributions + bias reconstruct raw model margin (log-odds), not probability
  or heuristic hybrid/rule scores. Stable sigmoid links margin to the uncalibrated score.
- Numerical checks: margin absolute/relative tolerances 1e-5/1e-6; score absolute 1e-6.
  Exact vector/model identity must match the evaluated prediction. Missing/corrupt/incompatible
  outputs fail; no fabricated explanation or fallback. Base is a model reference, not fraud rate.
- Readable top-five contributions rank by absolute magnitude with feature-order tie breaking.
  Missing history values are labelled placeholders; zero-MAD flooring is described explicitly.
  Rules-only has no model explanation. Hybrid abstention remains even when its model is explained.
- All 2,400 original hash-pinned seed17 prepared rows passed reconstruction: maximum margin
  difference 2.2863969206809998e-6; sigmoid score difference 8.22891939034065e-8. These are
  software checks, not predictive metrics or independent second-implementation SHAP validation.
- Actual --explain saved-context replay passed. Local numerical summary and full report:
  ../../work/phase10/treeshap-seed17/{verification.json,replay.json}; summary committed in
  ml/experiments/phase10-explanations. No training/tuning, new dependencies or database writes.
- Attributions depend on model-internal path statistics and correlated input representations;
  they do not prove causality, legitimacy, calibration or production suitability. No external
  background dataset, causal interpretation or contribution-to-probability conversion added.

- risk-v1-experimental uses full positive rules-v1 weights (0.40, 0.15, 0.25, 0.10, 0.10)
  in stable code order. Complete rule score is matched-weight sum / total-weight sum.
  Default hybrid weight 0.5 and decision thresholds 0.35/0.65/0.85 are authored illustration,
  not empirical calibration. Parameters plus missingness semantics have a canonical hash.
- Any unavailable rule makes rule_score null. Rules-only/hybrid return INSUFFICIENT_EVIDENCE
  with null score/level/action and all partial evidence; no subset renormalization or fallback.
  ML-only may score explicit missing-history features while reporting unavailable evidence.
- Suggested actions are never executed. No score/ALLOW suggestion authorizes admission or
  confirms legitimacy. All results remain production_eligible=false and calibrated=false.
- Offline replay retains vector, context identity/source/capture time, policy/rule evidence,
  manifest pin and canonical context digest. Actual inference/evaluation timestamps change.
  Existing native seed17 replay passed with the saved context; hybrid abstained correctly
  because prior raw history is absent. No new predictive metrics or model tuning occurred.
- ExperimentalRiskResult does not fabricate a persisted RiskAssessment. ADR-015 sketches
  an append-only evaluation envelope with nullable/unknown provenance and atomic scoped
  idempotent context/vector/evidence/result/audit/outbox/response writes for future work.

- Native bundle: ../../work/phase8/seed17; original synthetic source remains unchanged.
  Manifest SHA256: 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903.
  Native SHA256: 429dc7ec772d7f78700c9e608a43f3eb6152f1c3b0d88af399240d779e7a1d65.
  Model version is experimental-xgb- followed by the full native SHA256.
- Actual CLI replay passed using ../../work/phase8/first-context.json, hydrated from the
  original synthetic source. No retraining or new predictive performance measurement occurred.
- Export parity is software equivalence, not accuracy, calibration or production evidence.
  The adapter checks exact behavior-v1 order, XGBoost runtime and report provenance; the
  context service enforces KZT/UTC/180-day/30-day scope. ULB inputs are incompatible.
- Legacy reports do not contain exact training time. Manifest trained_at=null is intentional;
  exported_at is actual export time. No ModelVersion record is created: its required
  trained_at cannot be truthfully supplied. Never substitute file modification/export times.
- FraudPrediction retains its legacy probability field internally; CLI exposes it as
  uncalibrated_score, with synthetic_only=true, production_eligible=false, calibrated=false.
  Replay preserves scores/versions but generates a new actual inference timestamp.
- Trusted manifest digest must come from independent reviewed provenance. Adjacent file
  hashes alone do not establish trust. Only the restricted offline exporter deserializes
  verified reviewed pickle bytes; native inference never loads uploaded pickle/joblib.

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
  The rule engine itself produces no score; Phase 9 composes a separate heuristic index.
  No calibrated probability, automatic action or durable assessment is produced.
- Blacklist checks are deferred until an explicit authoritative versioned input exists.

- Feature version behavior-v1 fixes 29 names/order, policy and imputation. Baseline minimum
  is five; absolute amount deviation divides by max(MAD, 0.01) with explicit floor flags.
- Raw activity spans strictly (candidate - 180 days, candidate), same customer/currency,
  excluding candidate ID. More than 10,000 rows fails explicitly instead of truncating.
- Local artifacts preserve exact input facts and Decimal strings. SHA256 is integrity,
  not authenticity; 16 MiB limit and create-only writes. Phase 11 now durably retains
  experimental evaluation envelopes while legacy risk assessments remain unchanged.
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
- history_source=repository_admissions remains explicit. Legacy revisions disclose
  admission_workflow_verified=false; Phase 12 revisions bind verified policy/decision evidence.
  Customer creation/raw intake do not authorize learning.
- Five-observation minimum and typical-hour count/share thresholds (2 / 10%) are
  uncalibrated descriptive policies. SUFFICIENT_HISTORY is not a risk/trust verdict.
- Observation frequency is admitted count / configured window days, not raw intake velocity.
  Phase 5 supplies bounded raw device/recipient activity and velocity; recipient account age
  and external history completeness are unavailable.
- Cold start now has conservative multi-review bootstrap. Low-weight admission,
  compromised/colluding confirmations and corrections/retractions remain research debt.
- Transactions remain immutable RECEIVED records. Experimental evaluation/review is separate
  derived append-only state; no production risk API or human login exists. The local console
  uses operator-pasted service credentials and is not approved for remote exposure.
- External outbox destinations/audited redrive, idempotency retention, centralized revocation,
  rate limits, database grants and deployment hardening remain unfinished.
- Service credentials are configuration snapshots; rotate while retaining principal UUID
  and restart all processes to apply revocation/scope changes. Remote use requires TLS.

## Exact next tasks

1. Read status/specification/runbook and ADR-021/threat-model plus ADR-020/008/017/018.
2. Continue Phase 15 from its tested pure policy and password adapter. Do not redo the foundation.
   ADR-021 is proposed: HTTP/persistence integration must satisfy its security requirements.
3. Keep service principals for machine intake and separate human analyst/admin identities. Preserve
   customer scope, reviewer/admin separation and authorization-first durable idempotency replay.
4. Add PostgreSQL identity/session schema, least-privilege application workflows, audit events and
   brute-force/rate-limit policy before replacing the console's pasted-token connection screen.
5. Test expiry/revocation, role/scope changes, credential rotation, CSRF, concurrent sessions,
   inactive accounts, separation of duties and secret non-disclosure on PostgreSQL and HTTP.
6. Do not expose remotely until TLS/proxy headers, runtime database grants, CSP/cookie settings,
   deployment secrets and security review are complete. Never weaken experimental/profile gates.
7. Keep deterministic demo seeding (Phase 16), research experiments, corrections/weights and
   external delivery/redrive separate. Update all three checkpoint files before stopping.
