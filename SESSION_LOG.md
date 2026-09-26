# Session log

## 2026-09-19 — Foundation and domain checkpoint

- Inspected empty workspace; created separate repository under outputs, preserved
  original specification and left the parent repository untouched.
- Implemented locked Python environment, FastAPI liveness/settings/logging,
  PostgreSQL/Alembic foundation, Docker/Compose and CI definitions.
- Implemented pure domain records, robust rolling profiles, safe admission gate,
  immutable case transitions, risk/decision strategies, model/repository/event
  contracts, audit/feedback values and in-process event publisher.
- Added regression tests for exceptional purchases, fraud exclusion, unverified
  escalating activity, confirmed gradual drift, lifecycle and input invariants.
- Added architecture documentation, six ADRs and research protocol without metrics.
- Verification: 93 passed, 1 PostgreSQL skip, 90% coverage; Ruff/mypy clean;
  dependency audit found no known vulnerabilities; distributions built; Compose
  validated; offline migration SQL rendered; actual HTTP liveness returned 200.
- Fixed initial missing-README packaging timing and Decimal inference issue.
  Two upstream test dependency deprecation warnings remain unsuppressed.
- Docker runtime unavailable; Docker app launch unsuccessful. Container and live
  PostgreSQL remain unverified. No remote CI, trained model or metric claims.
- Next: verify disposable PostgreSQL, then Phase 2 tables, repositories, atomic UoW
  and PostgreSQL transaction/concurrency integration tests.


## 2026-09-19/20 — Phase 2 persistence and completed continuation checkpoint

- Resumed the interrupted persistence work without recreating Phase 0/1. Found native
  PostgreSQL 17.10 and initialized a dedicated synthetic test cluster. Sandbox shared
  memory/socket restrictions required approved execution outside the sandbox.
- Added 14 typed business tables, two Alembic revisions, complete repository ports/
  adapters, explicit-commit UoW, immutable history and serialized case/profile changes.
- Added scoped idempotency locks/records, exact snapshot encoding and durable outbox
  storage with publication metadata. No dispatcher or HTTP business API claimed.
- Tests verified record round trips, commit/default rollback/failed-commit rollback,
  concurrent profile/idempotency writes, immutable SQL history, association constraints
  and migration upgrade/downgrade with metadata matching.
- Final verification: 131 passed, zero skipped, 96% coverage; Ruff/mypy clean;
  dependency audit reports no known vulnerabilities; package builds and Compose
  configuration pass. Two upstream dependency deprecations remain.
- Updated README/architecture/ADRs, added ADR-007 and development runbook, refreshed
  all continuation files. Preserved and ignored user PyCharm .idea settings.
- Test cluster left running with no TCP listener and owner-only Unix socket. Docker
  runtime and remote CI still unverified. No trained model or predictive metrics.
- Next: Phase 3 authenticated synthetic transaction submission/retrieval and HTTP
  idempotency, with atomic audit/outbox effects and FastAPI/PostgreSQL tests.

## 2026-09-20 — Phase 3 authenticated transaction intake

- Added framework-free submission/retrieval and controlled synthetic customer enrollment;
  FastAPI routes require expiring hashed bearer service credentials and role/customer scopes.
- Canonical principal-scoped idempotency locks precede business writes. Successful responses
  replay exactly from PostgreSQL; changed requests and duplicate IDs return explicit conflicts.
- Transaction, authenticated audit, TransactionReceived event and completed response commit
  atomically. Failed audit/outbox/response/commit tests leave no partial records.
- Added bounded body sizes, strict Decimal/time/identifier validation, sanitized errors,
  no-store responses, registry rotation/revocation checks and database lifecycle composition.
- Verified concurrent retries and forced duplicate-ID insertion races against PostgreSQL,
  exact replay across app instances, scope enforcement and no automatic profile admission.
- Final suite: 193 passed, zero skipped, 97% coverage; two existing upstream deprecations.
  Ruff/format/strict mypy pass; pip-audit finds no known vulnerabilities; distributions,
  Compose configuration and Alembic upgrade/schema checks pass. No schema/dependency changes.
- Actual local Uvicorn/PostgreSQL smoke passed enrollment, submit, retrieve, exact retry,
  authentication and conflict checks; temporary server and smoke schema were removed.
- Updated README, architecture, runbook, ADR-008 and all checkpoint files. Credentials
  remain fail-closed until explicitly configured; no actual token was committed.
- PostgreSQL remains running on the owner-only Unix socket with no TCP listener.
  Docker runtime and remote CI remain unverified. No predictive metrics claimed.
- Next: Phase 4 profile application workflows, beginning with missing trusted-history,
  cold-start, per-currency as-of and leakage policies; preserve existing robust domain work.

## 2026-09-20 — Phase 4 versioned customer behavior reads

- Reused existing robust profile/window/gate domain; added framework-free scoped retrieval,
  explicit cold/insufficient states, Decimal summaries, hour histograms/typical hours,
  admitted observation frequency and known recipients.
- Added authenticated profile GET route with strict cutoffs, required version pinning for
  explicit historical reads and honest unavailable-history errors. No new admission endpoint.
- Added profile_revisions and migration 0004. PostgreSQL captures head metadata atomically,
  seals committed admission sets using full transaction identity/physical xmin, and protects
  revisions from mutation. Upgrade preserves existing observations and captures current
  heads only, rather than inventing old metadata. Default test DB is upgraded.
- Wrote ADR-009 defining event-time vs knowledge-version semantics and reviewed-source
  bootstrap requirements. Current provenance remains repository admission, not verified
  analyst legitimacy. Public intake/customer enrollment never trains profiles.
- Tested currency/window boundaries, backdated later admissions, policy version preservation,
  DST, missing/cold profiles, quarantine baseline preservation, revision rollback/immutability,
  concurrent readers/writers and migration of populated legacy heads.
- Final verification: 227 passed, no skips, 97% coverage; Ruff/format/strict mypy pass.
  pip-audit reports no known vulnerabilities; package/Compose/Alembic checks pass.
  Two existing upstream deprecations remain. Initial response self-annotation issue fixed.
- Actual Uvicorn/PostgreSQL profile smoke passed cold start, populated pinned median/MAD/p95,
  authentication and cutoff validation. Temporary server/schema removed; native PostgreSQL
  remains running without TCP. Docker execution and remote CI remain unverified.
- Updated all checkpoint files, runbook, architecture and README. No predictive metrics.
- Next: Phase 5 shared versioned feature engine, explicit missing-history/zero-MAD behavior,
  cutoff-safe activity queries and proof against candidate/future/late-data leakage.

## 2026-09-20 — Phase 5 shared feature engine

- Implemented one pure behavior-v1 extractor with 29 ordered finite values, explicit
  missing-history indicators, fixed Decimal precision and finite MAD floor semantics.
- Kept admitted baseline and raw activity separate. Added scoped single-query PostgreSQL
  history with strict candidate/currency/time exclusion and explicit row-limit failure.
- Added immutable capture contexts, explicit profile revision selection and authorization;
  strict versioned artifact adapter and authenticated capture/database-free replay CLI.
- Tested expected values, cold/empty/short histories, device ties, candidate/future bounds,
  currency, old revisions, late arrivals, artifact limits and exact batch/replay parity.
- Final verification: 260 passed, none skipped, 97% coverage; Ruff/format and strict mypy
  (68 backend files) pass. Audit found no known vulnerabilities. Builds, Compose config,
  Alembic upgrade/check and CLI entrypoint pass. Two existing upstream warnings remain.
- Dependencies and schema unchanged (0004_profile_revisions, 15 business tables).
  Existing API tests pass; no new HTTP endpoint or predictive outputs introduced.
- Documented ADR-010, runbook, architecture, shared ML import path and all checkpoint files.
  Capture time does not reconstruct commit history; saved original facts enable replay.
- PostgreSQL remains running without TCP. Docker execution and remote CI remain unverified.
- Next: Phase 6 deterministic versioned rule engine and reason codes on captured features.

## 2026-09-20 — Phase 6 deterministic rules

- Added pure rules-v1 specifications on behavior-v1 with five stable reason codes,
  explicit three-state outcomes and observed/threshold/missing evidence.
- Recorded experimental policy parameters and canonical fingerprints. Added offline
  artifact rule replay; no new HTTP writes, scoring, admission, schema or dependencies.
- Added 22 tests covering boundaries, missing input, exact reason order, policy/version
  checks and replay without database/configuration. Full PostgreSQL suite: 282 passed,
  none skipped, 97% coverage; two existing upstream deprecations.
- Ruff/format, strict mypy (71 files), distributions, Compose configuration and CLI help
  passed. Existing migration checks passed in suite. Prior dependency audit remains current
  for the unchanged lockfile; it was not rerun this session.
- Documented ADR-011, README/architecture/runbook and all three checkpoint files.
- Docker runtime/remote CI remain unverified; no predictive metrics claimed.
- Next: Phase 7 dataset suitability, leakage-safe preparation and offline model comparison.

## 2026-09-20 — Phase 7 synthetic offline experiment checkpoint

- Assessed external candidates; no dataset license/availability contract approved. Added
  original stochastic synthetic source with explicit event/arrival/label clocks and static
  authored bootstrap. No historical knowledge or trusted-admission provenance invented.
- Shared production feature replay excludes unavailable/future facts; chronological splits
  filter immature labels and withhold a quarter of customers from fitting/selection.
- Trained Logistic Regression, Random Forest and XGBoost on three seeds. Validation AP
  selected XGBoost each time; recorded final-test AP 0.7313/0.5757/0.6427. Synthetic-only
  results are ineligible for production; no real-world or adaptive-gate claims.
- Saved raw source, prepared values, split IDs, models, predictions and report hashes under
  ../../work/phase7/final-seed{17,29,43}; committed only summary reports, not model binaries.
- Added optional ML dependencies and lock entries; Homebrew libomp 22.1.8 was required on
  macOS. CI includes ML tests, strict mypy covers backend/ML. No schema/API changes.
- Verification: 289 passed, no skips, 96% combined backend/ML coverage; two upstream warnings.
  Ruff/format/mypy (77 files), locked offline sync, build, Compose and Alembic check pass.
  Updated dependency audit found no known vulnerabilities. Remote CI/Docker unverified.
- Added ADR-012, dataset assessment, measured results and updated checkpoint/runbook files.
- Next: external dataset suitability and defensible production baseline remain Phase 7 work;
  Phase 8 serving integration must not silently promote synthetic experiment artifacts.

## 2026-09-20–21 — Phase 7 external retrospective benchmark

- Verified ULB v3 public metadata via Kaggle API, preserving source/license evidence and
  ODbL/DbCL attribution. Downloaded anonymized bytes outside Git with pinned SHA256.
- Froze protocol before import/training: V1…V28/Amount under ulb-pca-v1, first identical
  feature occurrence, 86,400/129,600-second partitions, fixed models/seed and validation selection.
- Imported 284,807 rows; excluded 9,144 later identical feature tuples. Labels/arrivals,
  customer identity/currency and upstream PCA scope remain unknown; no behavioral mapping.
- First import stopped pre-training on quoted CSV values. Fixed parser and added a regression
  test; no protocol/model/selection changes. Complete run is ../../work/phase7/ulb-benchmark-v1-run2.
- Logistic Regression selected by validation AP; final test AP 0.733432, precision 0.274854,
  recall 0.824561, F1 0.412281. No production eligibility, calibration or adaptation claim.
- Verification: 304 passed, none skipped, 96% backend/ML coverage, two upstream warnings.
  Ruff/format/strict mypy (81 files), package builds and Compose configuration passed.
  PostgreSQL migration/schema tests passed. No dependency/schema change; prior audit retained.
- Added source notice, frozen protocol, ADR-013, measured report and all checkpoint updates.
- Next: Phase 8 experimental artifact-verified inference; production behavioral validation
  remains open. Docker runtime and remote CI still unverified; native PostgreSQL stays running.

## 2026-09-21 — Phase 8 explicitly experimental native inference

- Inspected original synthetic reports/artifacts and existing FraudModel/FraudPrediction/
  ModelVersion contracts. Legacy trained_at is unknown; preserved null without registration.
- Added restricted export of independently pinned reviewed synthetic pickle bytes to native
  UBJSON. Seed17 conversion matched all 2,400 saved feature scores exactly (difference 0.0).
  No training, tuning or new predictive metrics; original experiment artifacts unchanged.
- Added strict manifest/native adapter, exact feature/runtime/provenance validation, pure
  KZT/UTC/180-day/30-day context service and offline CLI exposing uncalibrated_score.
  Actual native CLI replay passed from original synthetic source facts. No HTTP/DB writes.
- Added 25 tests for parity, corruption, incompatible provenance/features/scope, invalid
  outputs, clock ordering, missing files, bounded reads and pinned-before-unpickle export.
- Verification: 329 passed, none skipped, 95% combined backend/ML coverage, two existing
  upstream warnings. Ruff/format, strict mypy (86 files), builds and Compose config pass.
  Compose config requires POSTGRES_PASSWORD; checked with a temporary non-secret dummy value.
  PostgreSQL migration/schema checks passed in the full suite. Dependencies/schema unchanged;
  prior clean audit retained. Docker execution and remote CI remain unverified.
- Added ADR-014, committed manifest/parity evidence, runbook/architecture/README updates and
  all three checkpoint files. Native model bytes remain outside Git under work/phase8/seed17.
- Next: Phase 9 experimental risk/decision composition with explicit rule scoring/missingness;
  production behavioral validation and atomic evaluation provenance/storage remain open.

## 2026-09-21 — Phase 9 experimental Risk + Decision

- Inspected existing strategies, decision policy, rules and inference. Added pure composition
  over saved contexts with configurable versioned weights/thresholds and full policy hash.
- Rules-only and hybrid abstain on any required unavailable rule; partial reasons remain.
  ML-only discloses missing evidence. No silent fallback, calibrated probability, executed
  action, profile admission, model registration, HTTP endpoint or database write introduced.
- Added offline CLI with input/manifest fingerprints, full feature/rule evidence and actual
  clocks. Native seed17 replay passed and correctly abstained on missing prior activity.
  Original model/data and benchmark metrics unchanged; no predictive metrics claimed.
- Added 36 tests covering strategies, partial/cold histories, boundaries, stable reasons,
  fingerprint changes, incompatible contracts, failures, clocks and native-model CLI replay.
- Full PostgreSQL verification: 365 passed, no skips, 96% combined coverage, two existing
  warnings. Ruff/format/strict mypy (89 files), builds and Compose config passed. Schema and
  dependencies unchanged; prior clean audit retained. Docker runtime/remote CI unverified.
- Documented ADR-015 formulas, limitations and future append-only nullable-provenance/atomic
  evaluation design. Updated README, architecture, development and three checkpoint files.
- Next: Phase 10 experimental explainability with exact output-space/additivity semantics.
  Production validation and durable HTTP evaluation remain open; PostgreSQL remains running.

## 2026-09-21 — Phase 10 native experimental explainability

- Verified XGBoost native contribution semantics against primary docs and installed 3.2.0.
  Added framework-free explanation port/contracts plus non-approximate native TreeSHAP.
- Bound all 29 contributions, base, margin and score to exact evaluated model/vector.
  Added finite/shape/additivity/link validation, stable signed top-five readable messages,
  explicit missing placeholders and separate rule evidence. Existing CLI gains --explain.
- Checked all 2,400 hash-verified original seed17 prepared rows: max margin reconstruction
  error 2.2863969206809998e-6 and sigmoid error 8.22891939034065e-8, within fixed tolerances.
  Real native CLI explanation passed while hybrid correctly retained insufficient evidence.
  These are implementation checks, not new predictive metrics; no retraining/test tuning.
- Added 44 tests. Full PostgreSQL suite: 409 passed, no skips, 96% combined coverage;
  two existing warnings. Ruff/format/strict mypy (91 files), builds and Compose config pass.
  No new dependencies or schema changes; prior audit retained. Docker/remote CI unverified.
- Documented ADR-016, numerical verification summary, runbook, architecture and checkpoint files.
  No causal/calibration claim, operational action, database write or model promotion introduced.
- Next: Phase 11 Cases / Feedback preparation, starting with durable experimental evaluation
  and truthful nullable provenance before case linking. PostgreSQL remains running locally.

## 2026-09-21 — Phase 11 durable experimental evaluation and review

- Added disabled-by-default authenticated evaluation routes that derive server-controlled
  facts, features, rules, risk and optional native explanation. Callers cannot supply scores,
  vectors, policies, explanations or models. Rules-only and model strategies retain truthful
  nullable provenance; unknown legacy training time remains null.
- Added an atomic application workflow for context/vector/policy/result/audit/outbox/exact
  idempotent response persistence. Authorization precedes replay, advisory locking precedes
  writes, and GET/restart replay returns stored bytes without querying current history.
- Added scoped analyst/admin cases and strict review transitions with optimistic versions.
  Feedback records actor/verdict/comment but never changes a transaction/profile, executes
  an action, admits history or trains a model.
- Added migration 0005 with experimental_evaluations, evaluation_cases,
  evaluation_case_transitions and evaluation_feedback. PostgreSQL rejects UPDATE, DELETE and
  TRUNCATE and enforces envelope identity/status plus transition/feedback provenance.
- Tested native and rules-only modes, missing evidence, exact replay after restart, late
  arrivals, scope/role failures, malformed envelopes, all rollback points, concurrent retry,
  concurrent reviewers and immutable history against PostgreSQL 17.10.
- Final suite: 436 passed, no skips, 95% combined backend/ML coverage; two unchanged upstream
  warnings. Ruff/format, strict mypy (97 source files), migrations, package builds and Compose
  configuration pass. No dependencies or predictive metrics changed; prior audit retained.
- Added ADR-017 and updated README, architecture, runbook and all checkpoint files. Migration
  head is 0005_experimental_reviews with 19 business tables. Docker runtime and remote CI
  remain unverified; production behavioral validation remains open.
- Next: Phase 12 safe adaptive profile updates, beginning with separately authorized
  feedback-to-gate provenance, trusted bootstrap/cold start and correction semantics.

## 2026-09-21 — Phase 12 safe experimental profile learning

- Added admin-only, disabled-by-default profile learning as a decision separate from analyst
  feedback. The authorizer must differ from terminal reviewers; cases are closed, terminal,
  scoped and single-use. Exact durable idempotent replay remains authorization-first.
- Added reviewed cold-start bootstrap requiring 5–100 legitimate cases, one customer/currency,
  absent-profile evaluations, at least two reviewers, one active 180-day window and no amount
  >=10x median. These are authored uncalibrated safeguards, not production validation.
- Orchestrated existing-profile updates through the pure gate. Exact current profile capture
  and verified provenance are required. Ordinary legitimate activity is admitted; exceptional,
  stale, late, insufficient or legacy evidence quarantines; confirmed fraud is excluded.
- Added immutable learning decision/evidence tables and provenance fields on profile heads and
  revisions. PostgreSQL binds verified revisions to matching ACCEPT decisions, validates review/
  evaluation evidence, prevents case reuse and rejects history mutation. Legacy heads remain false.
- Atomically commits decision/evidence, optional observation/revision, audit, outbox and exact
  response. Tested rollback, replay, authorization, separation of duties, stale captures,
  exceptional baseline preservation, fraud exclusion, immutability and concurrent bootstrap/update.
- Deliberately left low-weight admission and correction/retraction unavailable because current
  append-only observations cannot represent weights or superseding facts honestly.
- Final verification: 447 passed, no skips, 95% combined coverage; two unchanged upstream
  warnings. Ruff/format, strict mypy (100 source files), Alembic, builds and Compose pass.
  Dependencies and predictive metrics unchanged; Docker runtime/remote CI remain unverified.
- Added ADR-018 and updated README, architecture, development and checkpoint files. Migration
  head is 0006_safe_profile_learning with 21 business tables.
- Next: Phase 13 durable outbox claiming/delivery/retry reliability with truthful at-least-once
  semantics and consumer deduplication contract.

## 2026-09-21 — Phase 13 leased local outbox delivery

- Defined ADR-019 before implementing the dispatcher: single local recording destination,
  database-clock leases, UUID fencing, capped exponential retries, visible dead letters and
  truthful at-least-once semantics. No external effects or exactly-once external guarantee.
- Added framework-free delivery policy/port/dispatcher and PostgreSQL short claim/completion
  transactions. SKIP LOCKED permits concurrent workers; expired claims recover after crashes.
  Stale tokens cannot acknowledge/fail another lease. Legacy helpers reject leased/terminal rows.
- Added migration 0007_outbox_delivery: atomic delivery-state initialization/backfill and immutable
  consumer receipts. Historical publication remains intact without invented receipts. Schema has
  21 business tables plus two operational tables (24 including Alembic).
- Local receipt effect and consumer deduplication commit together, before separate acknowledgement.
  Published events, terminal delivery rows and receipt history resist mutation. Unknown envelopes
  dead-letter without blocking valid work; unsupported schema versions retry/fail explicitly.
- Added operator `python -m backend.adapters.events run --limit 100` and `status`; no HTTP route,
  auto-start worker, network consumer or profile-learning side effect. Payloads/secrets stay out
  of CLI output; bounded status includes dead-letter identities and active/expired lease counts.
- Verified concurrency, locks, bounded batches, backoff/exhaustion, crashes before/after handling,
  stale slow handlers, claim/ack rollback, deduplication, immutability and populated migration.
  Real subprocess CLI run/status passed in a disposable PostgreSQL schema.
- Final checks: 479 passed, zero skipped, 94% combined backend/ML coverage, two unchanged upstream
  warnings. Ruff/format, strict mypy (103 source files), Alembic upgrade/check, builds and Compose
  configuration passed. Dependencies unchanged; audit not rerun. Docker runtime/remote CI remain
  unverified. No research metrics or production validation added.
- Updated README, architecture/runbook and all checkpoint files. Next: Phase 14 analyst frontend,
  beginning with real scoped API contract inventory and safe local credential handling.

## 2026-09-22 — Phase 14 local analyst console

- Added ADR-020 and a framework-free console read-model port. PostgreSQL supplies an exact,
  customer-scoped summary and descending keyset worklist joining immutable transactions to their
  latest retained experimental evaluation/case. Empty scope returns empty data; reads are no-store.
- Summary semantics are explicit: UTC transaction event time, latest retained evaluation,
  HIGH/CRITICAL suspicious amount and retained case feedback. It reports no production model and
  no calibration instead of inventing model health, scores or predictive metrics.
- Built a responsive React 19/TypeScript/Vite console with overview, transactions, cases,
  customers, models and system sections. It renders retained explanations/profile statistics,
  missing evidence and immutable RECEIVED status. Review writes retain expected-version and fresh
  idempotency protections behind an explicit confirmation dialog.
- The raw credential is operator-pasted and held in React memory only; refresh/disconnect clears it.
  No source/URL/localStorage/sessionStorage secret, default credential, external font or mock data.
  Human login remains Phase 15 and the console is local-only.
- Added nginx static serving/same-origin API proxy with restrictive CSP, frontend Docker/Compose
  service and frontend CI job. Docker runtime remains unverified because the engine is unavailable.
- Verified 480 backend/ML tests on PostgreSQL, zero skips, 94% coverage and two unchanged upstream
  warnings. Ruff/format and strict mypy (108 sources), Python package build and Compose config pass.
  Frontend ESLint, 2 Vitest tests, TypeScript/Vite production build and npm audit pass with zero
  known vulnerabilities. Responsive connection screen received a real browser visual inspection.
- Schema remains 0007_outbox_delivery (21 business + 2 operational tables). Python dependencies,
  model artifacts and predictive metrics are unchanged. Remote CI remains unverified.
- Next: Phase 15 human authentication and security hardening, beginning with a threat model and
  session/revocation design before any remote exposure.

## Phase 15 foundation — 2026-09-22

- Added a threat model and proposed ADR-021 for separate human identities, revocable
  opaque sessions, refresh reuse detection, cookie/CSRF boundaries, operator recovery,
  shared throttling and outstanding deployment controls.
- Implemented framework-free human-account and session lifecycle policy, including
  exclusive expiry boundaries, absolute lifetime, authorization versions and revocation.
- Added explicit Argon2id adapter (64 MiB, t=3, p=4), exact bounded Unicode password
  handling and secret-safe token-container repr. Locked Argon2 and its dependencies.
- 32 new tests; full PostgreSQL/ML suite: 512 passed, zero skipped, 94% coverage,
  two unchanged upstream warnings. Ruff/format, strict mypy (111 files), builds passed.
- Audit of all locked dependency groups found no known vulnerabilities.
- Phase 15 remains IN PROGRESS. No human HTTP authentication or persistence is enabled;
  service credential startup and console behavior remain unchanged. Next: atomic
  PostgreSQL accounts/sessions/throttle, operator provisioning and HTTP/browser wiring.

## 2026-09-26 — Supplemental sequence evidence checkpoint

- Added pure `sequence-v1-experimental` evidence over the retained strict FeatureContext.
  Four candidate-inclusive 24-hour signals cover cumulative baseline-sized transfers,
  gradual amount escalation, repeated new recipients and cumulative exposure.
- The authored low-and-slow regression matches sequence evidence while rules-v1
  AMOUNT_ANOMALY remains NOT_MATCHED. A verified learning-created profile, five admitted
  observations and prior raw activity are mandatory; absent facts yield NOT_EVALUATED.
- Retained evidence includes exact Decimal counts/amounts/ratios, missing indicators,
  the complete uncalibrated policy and its SHA256. A database-free CLI replays saved context.
- New experimental evaluation envelopes retain sequence evidence atomically. Existing
  behavior-v1, rules-v1, native artifacts, risk-v1 scores/actions and old exact idempotent
  responses are unchanged. A future risk-v2 requires separately validated calibration.
- Fixed the console to distinguish stored INSUFFICIENT EVIDENCE from no evaluation and to
  render the actual nested rule reason contract plus matched sequence reasons. Older stored
  envelopes without sequence evidence remain compatible.
- Documented the layered detector architecture and unavailable graph/device/network inputs.
  No IP, location, login lifecycle, cross-customer graph, anomaly model or metric was invented.
- Final PostgreSQL/ML regression: 522 passed, zero skipped, 95% combined coverage and two
  unchanged upstream warnings. Ruff/format, strict mypy (115 sources), Python build, Compose
  configuration, frontend ESLint, 3 Vitest tests and TypeScript/Vite build passed. Schema and
  dependencies are unchanged; the prior clean dependency audit remains applicable.
- Phase 15 remains IN PROGRESS. Next core work is PostgreSQL human identity/session/throttle
  persistence and audited HTTP/browser integration. Detector follow-up is a separately
  versioned dataset protocol and risk-v2 validation, not an arbitrary score weight.
