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
