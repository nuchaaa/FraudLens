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

## 2026-09-26 — Phase 15 local human sessions

- Added migration 0008_human_identity with PostgreSQL human accounts, session families,
  consumed refresh tokens and bounded shared login throttling. Account and refresh history
  guards retain immutable evidence until the token family's absolute expiry.
- Implemented typed identity repository, framework-free identity workflows and explicit-commit
  UoW integration. Operator CLI uses getpass for provision/recovery, disable/enable and policy
  changes; account/session/audit writes commit or roll back together. Human and machine
  principal UUID collisions are rejected.
- Added opt-in FastAPI login/session/refresh/logout, short-lived opaque access cookies,
  refresh rotation/reuse family revocation, current account authorization checks, exact
  Origin and CSRF checks. Human cookies and machine bearer credentials cannot be mixed;
  existing customer scope and authorization-before-idempotency remain intact.
- Replaced the console's pasted bearer form with human login, session restore and serialized
  refresh. Access/refresh secrets remain HttpOnly cookies; local CSRF stays in tab memory.
  Human auth defaults disabled. Local HTTP is explicitly configured and not remote-ready.
- PostgreSQL/HTTP tests exercise rotation races, reuse, revocation, throttling, rollback,
  role/scope changes, origin/CSRF, cookie flags, audit and a real CLI subprocess. Full suite:
  532 passed, zero skipped, 93% combined backend/ML coverage, two unchanged upstream warnings.
  Ruff/format, strict mypy (121 files), Alembic check, Python build, Compose configuration,
  frontend ESLint, 5 Vitest tests and TypeScript/Vite build passed. The locked dependency
  audit after Argon2 remained clean; no dependency changes in this checkpoint.
- Schema head is 0008_human_identity, 27 non-Alembic tables. Docker runtime and remote CI
  remain unverified. Phase 15 remains IN PROGRESS: restricted runtime DB roles, verified
  TLS/proxy and edge controls, MFA/recovery assurance and external review are required
  before remote exposure. No research metrics or production model claims were added.

## 2026-09-26 — Phase 15 dedicated PostgreSQL role boundary

- Added a reviewed grant plan for a dedicated non-public PostgreSQL schema: separate
  migration owner, API, outbox worker and identity operator login roles. It revokes
  PUBLIC database/schema/table privileges, denies TEMP and schema creation, applies
  explicit table grants and fails on unknown tables or unexpected effective grants.
  Production entry points verify their actual role before serving or operating.
- The first real-role test exposed that `SELECT FOR UPDATE` on `human_accounts` needs
  UPDATE permission. Login and operator changes now share a transaction-scoped
  account advisory lock; login rereads current policy and password hash after it.
  A recovery raced against an old-password login now rejects that login. The API
  retains SELECT-only account access; the operator can only revoke session rows.
- A PostgreSQL integration test creates a separate disposable *_test database, runs
  all migrations as a distinct owner, applies grants, connects with three separate
  runtime passwords, proves positive API/worker/operator workflows and denies DDL,
  trigger disabling, immutable-history changes, account provisioning, TEMP and
  cross-role reads. It then drops only that database and its four temporary roles.
  Production-mode FastAPI startup/login, Host rejection and Secure cookies also
  passed under the restricted API login.
- The final privilege audit added column-level and Alembic-version-table checks;
  regression tests reject unexpected PUBLIC grants even when table-level checks
  alone would miss them.
- Full PostgreSQL/ML suite: 534 passed, zero skipped, 92% combined coverage and two
  unchanged upstream warnings. Ruff/format, strict mypy (122 source files), Alembic
  check, source/wheel build and Compose configuration passed. Frontend source and
  dependencies did not change; the prior ESLint, five Vitest tests and build remain
  applicable. No schema/dependency/model change or new predictive metric occurred.
- Added ADR-023 and a deployment-gates runbook. The current localhost Compose file
  still connects as schema owner and was not promoted. Real TLS/proxy behavior,
  edge limits, MFA and verified recovery, secret operations, Docker runtime,
  remote CI and independent security review remain unverified. Phase 15 stays open.

## 2026-09-26 — Phase 15 native HTTPS-edge checkpoint

- Added a separate candidate production frontend image and nginx configuration. It
  requires a validated DNS hostname and mounted TLS certificate/key, rejects unknown
  SNI/Host, sets HSTS/CSP, strips or replaces forwarded client headers, and includes
  explicit request-body, rate, concurrency and timeout bounds. The backend container
  now disables Uvicorn proxy-header trust; development nginx also sanitizes headers.
- Installed Homebrew nginx 1.31.4 to test the rendered configuration. `nginx -t`
  passed. A real self-signed local Nginx → Uvicorn → disposable PostgreSQL smoke
  verified HTTPS frontend and CSP/HSTS, Host 421, Origin 403, valid login/session
  with Secure/HttpOnly `__Host-` cookies, body 413, repeated-login 429 and known-host
  HTTP 308 redirect. A separate echo upstream confirmed that spoofed Forwarded,
  forwarded-host, client-IP and protocol headers were removed or replaced.
- The smoke used test-mode application settings and a one-day local certificate.
  Temporary database, certificate/key, cookies and processes were removed. It did
  not combine the proxy with the four-role production database topology and did not
  test an external hostname, CA certificate or load budget. Docker Desktop could
  not launch because this installation lacks an executable; the engine socket is
  absent. Thus the candidate container image remains unrun.
- Documented phishing-resistant WebAuthn and two-operator, out-of-band verified
  recovery requirements. These controls are not implemented; local login remains
  unapproved for remote exposure. Added ADR-024 and updated deployment gates.
- Full PostgreSQL/ML regression: 534 passed, zero skipped, 92% coverage and two
  unchanged upstream warnings. Ruff/format, strict mypy (122 sources), Alembic
  check, Python build, Compose configuration, frontend ESLint, five Vitest tests
  and TypeScript/Vite build passed. No schema, dependency, model or predictive
  metric changed. Phase 15 remains IN PROGRESS pending deployed topology,
  MFA/recovery implementation, operations and independent security review.

## 2026-09-27 — Phase 15 fail-closed remote human-auth checkpoint

- Found that production mode could still issue password-only human sessions even
  with the prior HTTPS/Secure-cookie requirement. Application construction now
  rejects production human-auth enablement until WebAuthn and verified recovery
  are implemented. Production with human auth disabled retains its restricted-role
  API startup and returns 503 from a valid human-login request.
- The getpass identity CLI now refuses production mode before opening a database.
  It also refuses a non-public dedicated runtime schema where the connected role
  cannot CREATE, including if the process is mislabeled development. Local owner
  and disposable test-schema CLI workflows remain intact; this is not operator
  authentication or protection against a privileged database owner.
- Added ADR-025 with the fail-closed decision and proposed durable WebAuthn
  challenge/assertion and two-operator recovery flow. Updated runbooks and threat
  model. No MFA, recovery protocol, migration or dependency was implemented here.
- Full PostgreSQL/ML regression: 535 passed, zero skipped, 92% combined coverage
  with the same two upstream warnings. Ruff/format and strict mypy (122 sources)
  passed. Alembic check, offline source/wheel builds, Compose configuration with
  a placeholder password, frontend ESLint, five Vitest tests and TypeScript/Vite
  build passed. Dependencies were unchanged and the prior locked audit was not rerun.
  Docker engine, combined role/TLS deployment and independent assessment remain
  unavailable. Production behavioral validation is still open.

## 2026-09-27 — Phase 15 local WebAuthn ceremony checkpoint

- Added migration `0009_human_webauthn` with authenticator public material/counters
  and immutable, two-minute, one-use PostgreSQL challenges. The verified WebAuthn
  adapter binds account/authorization version, ceremony, RP ID, exact Origin,
  credential ID, signature, user presence/verification and sign counter.
- Local analyst first-factor enrollment requires an active session, CSRF and fresh
  password. It revokes all sessions and increments authorization version. Admin
  bootstrap is denied. Password-plus-assertion login issues no session at the
  password step; a valid challenge is consumed on success or failed verification.
  Browser login and enrollment controls were added to the React console.
- PostgreSQL/FastAPI tests use generated software authenticator credentials and
  cover successful enrollment/login, replay, bad signature/origin, malformed
  enrollment, concurrent assertions, counter reuse and account disablement.
  Database-role regression required API SELECT of credential presence to deny
  password-only login; no factor/challenge writes were granted. Production human
  auth remains disabled.
- Added ADR-026 and updated the security/development runbooks. Locked `webauthn`
  3.0.1 and its dependencies; updated locked pip-audit found no known
  vulnerabilities. The final full PostgreSQL/ML regression had 540 passed,
  zero skipped, 92% combined coverage and two upstream warnings. Ruff/format,
  strict mypy (123 source
  files), Alembic upgrade/check, offline source/wheel builds, Compose
  configuration, frontend ESLint, seven Vitest tests and TypeScript/Vite build
  passed. Docker daemon socket is absent.
- Physical-browser ceremony, second-factor lifecycle, admin approval, verified
  two-operator recovery, challenge archival, restricted-role MFA writes,
  deployed four-role/TLS topology and independent assessment remain open. The
  local CLI's asserted operator UUID is not verified human identity. No model,
  predictive metric or production eligibility changed.

## 2026-09-27 — Phase 15 local factor lifecycle and retention checkpoint

- Migration `0010_factor_lifecycle` binds WebAuthn challenges to the originating
  session family for local factor changes. Analysts can add a backup key only
  after a current session, fresh password and a verified assertion from an
  existing key. Removing a key requires a different active key; removing the
  last key is denied. Every successful change advances account authorization
  version, revokes sessions and appends audit in one PostgreSQL transaction.
  Admin factor changes remain denied. The subsequently additive
  `0011_factor_removal_retention` records removal targets and pruning guards,
  preserving the already-applied 0010 revision on the local demo database.
- The local disposable public-schema database had applied a development version
  of 0010 that already contained the later removal/retention objects. Before
  setting its revision to 0011, inspected the two columns, expiry index,
  ceremony constraint, foreign key and delete/guard triggers plus the pruning
  function. They matched 0011; `alembic stamp 0011_factor_removal_retention`
  changed only its version marker, and `alembic check` passed. New databases
  migrate normally through 0009 → 0010 → 0011; the full migration test covers
  that path and downgrade on a disposable schema. No production data was used.
- Expired raw challenge rows can be deleted after one further day. A trigger
  rejects early DELETE and all TRUNCATE; each new challenge prunes at most 100
  old rows. Immutable audit events retain ceremony references. This is lazy
  retention and idle deployments may retain expired rows until maintenance.
- The console lists the current account's key metadata and offers first/additional
  enrollment and different-key removal. No private authenticator key is stored.
  Added ADR-027 and revised runbooks and security boundaries. Production human
  auth remains fail-closed, and the restricted production API role still lacks
  challenge/factor writes.
- PostgreSQL/FastAPI tests cover additional-factor proof, two usable keys,
  different-key removal, last-key refusal, replay, cross-session binding,
  retention trigger/pruning, simulated audit failure rollback and concurrent
  completion. Existing migrations and real-role regression passed. The latest
  final full suite: 546 passed, zero skipped, 91% combined coverage with two
  unchanged upstream warnings. The focused 11-test WebAuthn suite passed.
  Ruff/format,
  strict mypy (123 source files), Alembic upgrade/check, Python builds,
  Compose configuration, frontend ESLint, nine Vitest tests and TypeScript/Vite
  build passed. Dependencies/lockfile unchanged; prior clean audit remains.
- Supervised remote bootstrap, authenticated admin approval, verified
  two-operator recovery, physical-browser key ceremony, deployed four-role
  TLS topology and independent security review remain open. No predictive
  metric, model eligibility or profile-admission policy changed.

## 2026-09-27 — Phase 15 recovery trust-boundary policy checkpoint

- Added ADR-028 and a framework-free, non-executing recovery policy. A bounded
  case binds a frozen subject and authorization version, purpose, external proof
  reference/digest and at most 15-minute proof lifetime. Exactly two distinct
  active admin approval claims must bind to that case/proof/purpose, carry
  independent session, challenge and credential identifiers, and be at most
  five minutes old. Unit tests cover absent/extra/same-actor claims, stale or
  pre-proof assertions, changed case/purpose/proof, active/stale subject and
  expired proof. The policy takes claims; it does not authenticate their source.
- No endpoint, CLI, database write path, migration or grant invokes the policy.
  Institutional proof verification, real operator WebAuthn authentication,
  supervised admin bootstrap, immutable PostgreSQL approvals, account freeze/
  recovery execution and independent notification are still unimplemented.
  Production human auth remains fail-closed. A claimed operator UUID or case
  number is not accepted as verified identity.
- Full suite on disposable PostgreSQL: 565 passed, zero skipped, 91% combined
  backend/ML coverage, two unchanged upstream deprecation warnings. Ruff,
  format, strict mypy (124 source files) and offline source/wheel build passed.
  No schema, frontend, dependency, model or predictive metric changed. The
  previous Alembic, Compose, frontend and locked dependency checks remain the
  last measurement for those unchanged parts. Docker runtime and independent
  security assessment remain unavailable.

## 2026-09-27 — Phase 15 approval-claim hardening checkpoint

- Bound each approval to an exact action digest as well as case, subject,
  purpose and proof. Approval claims no longer carry trusted role/active flags;
  the pure policy requires current operator account snapshots, enabled admin
  roles and matching authorization versions. Distinct actors, session families,
  challenges and credentials remain required. Added denial tests for changed
  action, demoted/disabled/expired operators, stale authorization versions and
  duplicate current accounts.
- Full disposable-PostgreSQL regression: 567 passed, zero skipped, 91% combined
  coverage, same two upstream warnings. Ruff, format and strict mypy (124 source
  files) passed. No migration, runtime grant, API, CLI, frontend, dependency or
  model change. Docker engine socket is still absent. Production human auth
  remains disabled; no proof verifier, notification channel or recovery executor
  exists. Canonical action serialization and institutional process remain to be
  specified before connecting approvals to writes.

## 2026-09-27 — Phase 16 deterministic transaction-facts fixture checkpoint

- With no institutional proof issuer/notification process or independently
  authenticated remote admins available, retained Phase 15 remote recovery as
  an external release gate. Production human auth still fails closed. No
  approval or reset route was added, and no asserted CLI UUID was promoted to
  verified identity.
- Added pure `demo-scenarios-v1` fixture with stable UUIDv5 IDs, fixed UTC anchor,
  four synthetic customers and 62 KZT transactions. Its five authored stories
  match the project specification, with shared B/C customer history. CLI dry-run
  reports manifest SHA-256
  `4645220dd30cfabb12e8a22688a45035d81e352fe2ef5998f6f16a33019f26c8`.
  `--apply` requires a local Unix-socket `*_test` database and rejects production.
  It uses existing customer/transaction use cases, retaining audit, outbox and
  durable idempotency. The actor UUID is explicitly a synthetic fixture identity.
- PostgreSQL integration applied the plan only in a disposable migrated test
  schema, then replayed all 62 transactions without duplicate audit/outbox rows.
  It verified no profile or evaluation rows were created for fixture IDs. The
  working public demo database was not seeded. Stories are authored intent, not
  actual analyst verdicts or measured detector outcomes. ADR-029 and the
  development/README instructions document this boundary. Added a local
  five-story guide for optional manually authorized review, pinned profile
  versions and explicit insufficient-evidence handling; it has not been run as
  a claimed behavioral-validation study.
- Full PostgreSQL/ML suite: 573 passed, zero skipped, 91% combined coverage,
  two unchanged upstream deprecation warnings. Ruff/format, strict mypy (128
  source files), Alembic upgrade/check, offline source/wheel build, frontend
  ESLint/nine Vitest tests/build and Compose configuration with a placeholder
  password passed. New modules are present in the wheel. Docker runtime and
  remote CI remain unverified; no dependencies, trained model, production
  eligibility or predictive metric changed.

## 2026-09-27 — Phase 16 read-only five-story evidence ledger checkpoint

- Added `--progress` to the disposable local demo CLI. It checks exact fixture
  transaction facts and reads retained evaluations, captured profile versions,
  cases, feedback, learning decisions and immutable profile revisions in one
  PostgreSQL repeatable-read, read-only transaction. It reuses the Unix-socket
  `*_test` and non-production guard; no verdict or admission is generated.
  An ID collision with different facts reports CONFLICT and suppresses
  evaluation attribution; its PostgreSQL regression test passed.
- Expanded the five-story guide with conditional evidence criteria for A–E,
  including pinned B/C versions, recorded exceptional-amount quarantine and
  revision medians, and ordered D learning. Event-time-compatible revisions do
  not prove they existed at the original decision. ADR-030 records the boundary.
- PostgreSQL tests verified fixture replay, read-only reporting, actual API
  evaluation/case records without feedback, and customer isolation. A proposed
  test that scripted analyst feedback was rejected by automatic approval review;
  it was removed before execution. No synthetic verdict or claimed outcome was
  persisted by this checkpoint. A read-only CLI smoke on the working test DB
  reported 62 ABSENT fixture facts; the public demo schema remains unseeded.
- Full suite: 574 passed, zero skipped, 91% combined coverage, with two unchanged
  upstream deprecation warnings. Ruff/format, strict mypy (129 files), offline
  source/wheel build, frontend ESLint/9 Vitest tests/build passed. Dependencies
  and migrations unchanged. Docker runtime and remote CI remain unverified.
- Next: only with actual independent authorized local review inputs, perform
  bootstrap and case learning through existing APIs, preserve captured versions,
  then inspect B/C baseline preservation and D gradual adaptation. Otherwise
  keep those stories as guided steps, not demonstrated outcomes. Phase 15 remote
  security and production behavioral validation remain open.

## 2026-09-27 — Phase 16 guided local walkthrough checkpoint

- Read all requested checkpoint/specification/demo/security records before
  changing the local demo. Read-only inspection of the working disposable test
  DB found 62 ABSENT fixture facts and four absent KZT profiles; no actual
  reviewer evidence was available to justify bootstrap or learning.
- Added `--walkthrough`: a concise A–E presenter view over the existing guarded,
  read-only PostgreSQL evidence report. It lists 14 candidate UUIDs, stored risk
  status and captured profile version, case/feedback/learning counts, current
  profile version, event-time-compatible revisions with an availability warning,
  story-specific evidence requirements and the next manual step. It checks the
  manifest hash and cannot create a verdict or admission. ADR-031 and the demo
  guide explain that B/C preservation and D adaptation remain unverified.
- PostgreSQL integration covers unseeded/matching/conflicting fixture facts,
  manifest mismatch, authorized evaluation plus open case with no feedback,
  and honest INSUFFICIENT_EVIDENCE display. No scripted analyst verdict was
  submitted. A live read-only walkthrough smoke showed all stories pending.
- Full regression: 574 passed, zero skipped, 91% combined backend/ML coverage,
  two unchanged upstream deprecation warnings. The final 7 focused tests passed
  after wording changes. Ruff/format, strict mypy (130 source files), offline
  source/wheel build and wheel inclusion of the new module passed. Dependencies,
  schema and frontend were unchanged. Docker runtime/remote CI remain unverified.
- Next: only real independent authorized local reviews can establish baseline
  and gradual-adaptation evidence. Preserve the original captured versions and
  inspect immutable revisions before claiming B/C or D behavior. Phase 15 remote
  human security and production behavioral validation remain open.

## 2026-09-27 — Phase 16 staged disposable intake checkpoint

- Kept the fixed 62-fact `demo-scenarios-v1` manifest and hash unchanged. Added
  pure stages: 48 earlier background facts, A/B/C, D1–D5 and E1–E6. The
  `--apply-stage` CLI uses the existing guarded `*_test` Unix-socket PostgreSQL
  target, audited/idempotent enrollment and submission services, and original
  manifest-based idempotency keys. An advisory transaction lock serializes
  fixture CLI writes; it does not lock arbitrary API writers.
- Read-only repeatable-read prerequisite checks refuse new B/C/D/E candidate
  facts without a verified prior KZT profile. C waits for a retained B
  evaluation and separate B learning decision; later D steps wait for an
  authorized ACCEPT admission of the previous step; later E steps wait for a
  previous retained evaluation. Exact stage replay is idempotent. Existing bulk
  `--apply` remains a facts-only shortcut without these presentation gates.
  Neither path generates analyst verdicts, admissions or risk evaluations.
- Isolated migrated-schema PostgreSQL tests inserted/replayed BASELINE and A,
  proved B/C/D1/E1 stop without verified profile evidence and found no
  profiles/evaluations. The working public-schema demo database was not seeded.
  Positive review-dependent paths remain untested without actual independent
  authorized reviewer inputs; no behavioral outcome is claimed. ADR-032 and
  the demo guide document that staged insertion is only a local sequence, not
  reconstructed bank arrival or label availability.
- Full disposable-PostgreSQL regression: 576 passed, zero skipped, 90% combined
  backend/ML coverage; two unchanged upstream warnings. Ruff/format, strict
  mypy (131 source files), existing migration tests and offline source/wheel
  build passed. Confirmed the new modules are in the wheel and the manifest
  SHA-256 remains fixed. Frontend, schema and dependencies did not change;
  frontend lint/nine tests/build last passed at the previous checkpoint.
  Docker runtime and remote CI remain unverified. Phase 15 remote security and
  production behavioral validation are still open.

## 2026-09-27 — Phase 16 read-only stage preflight checkpoint

- Added `--check-stage STAGE` to the guarded disposable demo CLI. It runs the
  same PostgreSQL read-only prerequisite check used before staged writes and
  reports READY, BLOCKED with the missing-evidence reason, CONFLICT for an
  incompatible stable fixture ID, or REPLAYABLE for exact existing facts.
  `--apply-stage` rechecks under its advisory lock; preflight is not a
  reservation, proof of review, or historical-availability guarantee.
- Isolated migrated-schema PostgreSQL tests cover baseline/A readiness and
  replay, B/C/D/E blocking without a verified prior profile, and conflict
  reporting for altered fixture facts. No analyst verdict or trusted admission
  was scripted. A live read-only check on the working disposable test DB
  reported B BLOCKED because background facts are absent; no seed was applied.
- Full regression: 577 passed, zero skipped, 90% combined backend/ML coverage,
  two unchanged upstream deprecation warnings. Ruff/format, strict mypy (131
  source files), offline source/wheel build and migration tests passed. Frontend,
  schema and dependencies did not change; frontend checks last passed at the
  prior checkpoint. The five-story behavioral claims still require actual
  authorized independent reviewer inputs. Phase 15 remote security and
  production behavioral validation remain open.

## 2026-09-27 — Phase 16 fixture-bootstrap provenance guard

- Audited the staged demo path and found that a verified KZT profile built from
  unrelated customer transactions could previously unlock B/C/D/E, even though
  the demonstration claims a baseline from this fixture's earlier transfers.
  Tightened the read-only stage prerequisite: the first immutable profile
  revision must link to an accepted BOOTSTRAP; at least five matching fixture
  baseline IDs must occur in both version-one admitted observations and that
  decision's evidence; the evidence must name two distinct recorded reviewers.
  This checks retained workflow data, not external legitimacy or the human
  identity behind a stored reviewer ID.
- C now specifically waits for B's separately retained exceptional-amount
  QUARANTINE learning decision with no profile-version advance, rather than any
  case-learning decision. That preserves the intended B/C baseline narrative as
  a prerequisite while leaving actual reviewer conclusions unasserted.
- Pure tests cover matching/missing/unrelated bootstrap trace IDs and distinct
  reviewer-ID structure without persisting scripted verdicts. Full disposable
  PostgreSQL suite: 578 passed, zero skipped, 90% combined backend/ML coverage;
  two unchanged upstream warnings. After the final C-guard edit, 11 focused
  PostgreSQL/unit tests and global Ruff/format/strict mypy (131 source files)
  passed. Offline package build passed before the final C edit and was rebuilt
  afterward. No schema, dependency or frontend changes. Positive reviewer-
  dependent demo paths remain unexercised; the working public demo database was
  not seeded. Phase 15 remote security and production behavioral validation
  remain open.

## 2026-09-27 — Phase 16 evidence availability audit

- Re-read the requested project specification, local demo guide, ADR-029–032,
  development instructions and deployment gates. The staged fixture, preflight,
  read-only ledger and presenter walkthrough are already implemented. Completing
  B/C baseline preservation or D gradual adaptation still needs independently
  authorized local analyst decisions and a separate admin learning action.
- Ran only the guarded read-only `--progress` command against the working
  disposable PostgreSQL test database. It reported all 62 fixture transaction
  facts ABSENT, zero retained evaluations and no KZT profile for the four
  fixture customers. There was no reviewer evidence to inspect. No fixture
  transaction, analyst verdict, case, profile or learning decision was written.
- No source, schema, dependency or frontend code changed in this audit.
  Previous validation remains 578 full-suite tests passed and 11 focused tests
  after the final C-stage guard edit. Updated the checkpoint and next-session
  instructions to avoid repeating engineering work as a substitute for real
  reviewer evidence. Phase 16 remains open, as do Phase 15 remote security and
  production behavioral validation.

## 2026-09-27 — Repeated Phase 16 continuation without new evidence

- The attached continuation repeated the prior Phase 16 checkpoint and supplied
  no independently authorized analyst review, admin learning decision, changed
  scope or permission to seed the working disposable database. The preceding
  read-only audit still establishes the latest observed state: 62 ABSENT facts,
  zero evaluations and four absent profiles. No new database query or test was
  needed to restate that same checkpoint.
- Made no source, schema, dependency, frontend or database change. Left B/C
  baseline preservation and D gradual adaptation as guided, NOT DEMONSTRATED.
  Updated the continuation prompt to identify the required external reviewer
  input instead of directing another pass of staged-CLI engineering.
## 2026-09-28 — Phase 16 local demo baseline and analyst setup

- With the user's step-by-step authorization, applied only the guarded BASELINE
  stage to the disposable Unix-socket `fraudlens_test` PostgreSQL database.
  Read-only replay/preflight reported the 48 background facts as matching and
  the 14 candidate facts as absent. No profile, evaluation, case, feedback or
  learning decision was generated.
- Started local-only Uvicorn and Vite with development human auth and
  experimental routes enabled; both HTTP endpoints responded. The two friends
  separately provisioned `analyst-one` and `analyst-two`, choosing their own
  passwords privately in Terminal. Read-only SQL verified both accounts are
  active analysts scoped to the BC and D fixture customers. No password or
  password hash was read. Asked the first friend to test console sign-in.
- These accounts and synthetic facts are setup, not analyst verdicts or proof
  of legitimacy. B/C baseline preservation and D gradual adaptation remain
  NOT DEMONSTRATED. No source, migration or dependency change was made; prior
  regression results remain the latest full validation. Phase 15 remote human
  security and production behavioral validation remain open.

- After the user pointed out that the analysts had no case to review, used a
  temporary in-process, expiring machine admin credential through the existing
  authenticated FastAPI routes to create 10 rules-only experimental evaluations
  with explicitly absent profiles and 10 empty cases on early BC/D background
  transfers in the disposable local test database. The token was not printed
  or persisted. Read-only SQL verified 10 scoped cases and zero feedback rows.
  This prepares visible review work without asserting any verdict or admission.

- The user reported `analyst-two` could not submit a verdict on the displayed
  cases. Read-only SQL showed `analyst-one` had entered LEGITIMATE terminal
  feedback on all 10 original cases; `analyst-two` only closed one already
  reviewed case. Terminal feedback is one-use, so closure cannot count as a
  second review. Used the same temporary authenticated local API setup to
  create two more rules-only, absent-profile evaluations and empty OPEN cases
  for untouched BC/D baseline transactions. Verified their zero feedback and
  transition counts, and verified no BC/D profile or learning decision exists.
  The immutable earlier reviews were not changed. The second analyst confirmed
  these two cases show OPEN in the console. Their future synthetic judgments
  are not field labels.

- `analyst-two` then entered NEEDS_INVESTIGATION feedback on both new cases,
  explaining that the available facts do not prove fraud or legitimacy. The
  user observed that merchant/building/location data is absent and that a
  small amount alone could mislead a reviewer. Confirmed the transaction
  entity contains no such merchant or location field. Kept the earlier
  LEGITIMATE histories intact and made no profile-learning or bootstrap write.
  Clarified the demo guide so unresolved cases remain pending rather than
  being promoted to trusted history. No source, schema or dependency change;
  prior regression checks remain the latest full validation.

- For an honest next demo step, checked stage A read-only (READY), added only
  its 25,000 KZT synthetic transaction via guarded staged intake, and created
  one authenticated experimental rules-only evaluation with an explicitly
  absent profile. It returned INSUFFICIENT_EVIDENCE; amount, new-recipient and
  unusual-time rules lacked trusted baseline inputs. Read-only progress showed
  49 MATCH / 13 ABSENT, no profile revisions, and B preflight BLOCKED for no
  verified prior KZT profile. No A case/verdict/learning write was made. The
  current analyst accounts are BC/D-scoped, so A is visible via the local
  read-only walkthrough or authorized admin view, not their worklists.

- The user pasted the five-story walkthrough. It correctly reported 49 MATCH,
  13 ABSENT and story A's INSUFFICIENT_EVIDENCE evaluation, but its generic
  "apply the transaction-facts fixture" hint for absent B/C/D/E contradicted
  guarded stage prerequisites. Changed the presenter text to name the exact
  `--check-stage` for each absent candidate and to apply only if READY. A
  focused PostgreSQL renderer regression passed (1 test); Ruff, format and
  mypy passed; the live read-only walkthrough showed the corrected hints.
  No further fixture, case, feedback, profile or learning write was made.

## 2026-09-28 — Evaluation visibility, missing payment context and CI repair

- Investigated the user's transaction and GitHub screenshots. The synthetic
  baseline rows are raw immutable intake; no assessment is automatically
  created. Experimental rules-only evaluation is separate, and ML-only/hybrid
  additionally require a reviewed native bundle. Replayed the saved synthetic
  XGBoost context offline successfully (uncalibrated score 0.8466238975524902);
  this verifies the adapter, not field performance. The local API has no model
  bundle configured and the model remains production-ineligible.
- Added console text that NOT EVALUATED is not a low-risk verdict and that the
  transaction record lacks sender/receiver names, merchant/ИП identity, purpose
  and verified payment location. Inspected Kazakhstan's official registry
  search: it can verify an identified business but does not identify the payee
  of a synthetic transaction. No real business was attached to the fixture.
- GitHub Actions backend run 36374656050 failed four demo tests because the
  service URL was TCP and the disposable demo guard requires a Unix socket.
  The workflow now proxies its disposable PostgreSQL service to an owner-only
  local socket for pytest. The first local full run also exposed an order-
  dependent demo test in the shared schema; moved the two demo seeding/report
  tests to isolated migrated schemas. All six focused PostgreSQL tests passed.
- Final local suite: 578 passed, zero skipped, 90% backend/ML coverage on
  PostgreSQL 17.10. Ruff, format, strict mypy (131 source files), frontend
  ESLint/nine Vitest tests/build and git diff whitespace check passed. Two
  upstream deprecation warnings remain. No schema/dependency change, profile
  admission, scripted review or new predictive metric. Remote CI verification
  remains pending at this checkpoint.
- Committed the changes locally on branch
  `codex/fix-demo-ci-and-evaluation-context` (initial commit `f5b15ef`).
  Automatic approval review rejected the attempted GitHub push as consequential
  source-code egress without explicit user authorization. No alternate upload
  was attempted until the user explicitly approved it. Then pushed the branch,
  opened PR https://github.com/nuchaaa/FraudLens/pull/1 and observed both backend
  and frontend checks pass on the push and PR runs (36378777231, 36378805856).
  The PR remains open and unmerged.

## 2026-09-28 — Read-only Phase 16 continuation audit

- Re-read the current checkpoint, specification, development/demo guide,
  deployment gates and ADR-029–032. No new transaction-linked merchant/payee
  facts or independently verified legitimacy evidence was supplied.
- Ran the guarded read-only `--progress` and `--check-stage B` commands against
  the disposable PostgreSQL socket. The ledger remains 49 MATCH / 13 ABSENT,
  with 13 experimental evaluations, 12 cases, 10 LEGITIMATE and 2
  NEEDS_INVESTIGATION feedback entries, no learning decisions and no profile
  revisions. B is still BLOCKED for lack of a verified prior KZT profile.
  The audit made no database writes, reviewer claims or profile admission.
- Confirmed current PR #1 backend and frontend checks pass on push/PR runs
  36379336513 and 36379339075. Corrected stale "unseeded" wording in the
  demo guide and updated the checkpoint/continuation prompt. B/C baseline
  preservation and D adaptation remain NOT DEMONSTRATED; Phase 15 remote
  release and production behavioral validation remain open.

## 2026-09-28 — Explicit local admin evaluation and case flow

- Added an admin-only console action for an unevaluated transaction: the admin must explicitly assert an absent admitted profile or enter a pinned pre-decision revision before requesting rules-only evaluation. The form retains its idempotency key on retry and displays the persisted experimental result. The administrator may separately open a review case; neither action enters a verdict or admits profile history. Human analysts cannot submit evaluations from the console.
- Reused existing backend API contracts, human-session CSRF, idempotency and authorization. A PostgreSQL integration test verifies a human admin can create and replay the evaluation while an analyst gets 403. Frontend tests cover admin request data, CSRF/idempotency headers, case creation and analyst UI restriction.
- Local validation on disposable PostgreSQL 17.10: 579 tests passed, zero skipped, 90% combined backend/ML coverage; two existing upstream Starlette/AnyIO warnings. Ruff, format, strict mypy (131 source files), frontend ESLint, 11 Vitest tests and Vite build passed. Initial sandboxed pytest could not access the PostgreSQL Unix socket; the successful full run used approved socket access. No migration, dependency, model configuration, reviewer verdict or profile admission changed.
- The staged B/C/D demonstration remains blocked by lack of independently verified transaction-linked evidence. Production human authentication and behavioral validation remain open.
- Committed locally as `aa0649a` on `codex/fix-demo-ci-and-evaluation-context`. Automatic approval review rejected the push to `origin` as external source-code egress without trusted authorization for the exact destination and payload. No alternate upload was attempted. PR #1 therefore does not yet contain this console change; explicit user approval is required before pushing it.

## 2026-09-28 — Fictional Phase 16 review-evidence package

- Added `demo-review-evidence-v1`, a deterministic companion entry for all 62
  fixture transactions. Entries contain obviously fictional parties, purposes,
  locations, references and artifact summaries while explicitly declaring
  synthetic-only, real-world-unverified, production-ineligible and verdict-free
  status. Baseline/A/B/D have authored supporting context; C/E deliberately keep
  support unavailable. The package SHA-256 is
  `436c1c24119a12a7df63bf9f6ea4888a19c021b1eec94d4df945e83983687185`.
- Added an offline package command and an authenticated, scope-checked,
  experimental no-store read endpoint. The React transaction drawer displays
  matching context behind a prominent role-play warning and retains the existing
  missing-context disclosure for non-fixture records. The package is not read by
  feature, risk, case or profile-learning code and creates no database writes.
- Accepted ADR-033 and updated the runbook, five-story guide and architecture map.
  The pre-change baseline was 579 Python tests and 11 frontend tests. Final local
  validation passed 582 Python tests with zero skipped and 90% combined coverage
  on PostgreSQL 17.10, Ruff/format, strict mypy over 133 source files, frontend
  ESLint, 12 Vitest tests and Vite build. Two existing upstream warnings remain;
  dependencies and migrations are unchanged.
- No analyst verdict, evaluation, case, learning decision or profile revision was
  generated. Phase 16 remains open until actual analysts independently review new
  BC/D cases and the stored bootstrap/gate outcomes are verified.
- Read-only GitHub inspection confirmed PR #1 was merged at remote head `9857c84`
  with successful backend and frontend checks. The later local console commits and
  this evidence package were not part of that merge. Published them on
  `codex/phase16-demo-evidence` and opened PR #2. Both backend and frontend checks
  passed on its initial head; the PR remains open and unmerged.

## 2026-09-28 — Separate controlled Phase 16 scenario simulator

- Accepted the user's correction that Phase 16 needs deterministic synthetic behavior cases, not an external dataset or model-training claim. Added a database-free simulator using the real pure feature, rules, decision, sequence and profile-gate code. It exports `data/synthetic/{customers,recipients,transactions}.csv` and `scenario_manifest.json` for 10 customers, 2,000 varied prior transactions and 39 A–E candidates. The last 100 prior facts per customer are assumed oracle-approved solely in memory; no analyst verdict, persistent admission or real legitimacy is asserted.
- Observed A LOW/ALLOW/ACCEPT, B MEDIUM/STEP_UP_VERIFICATION/QUARANTINE, C HIGH/HOLD_AND_REVIEW against the preserved 29k KZT median, and 30 D ACCEPTs with the short median rising from 29k to 94,310 KZT. E's low-value sequence produces supplemental matches and profile quarantine when no verdict exists, but risk-v1 still returns LOW/ALLOW. The manifest explicitly records `E_low_value_attack_risk_flags=false`. This is a detector gap, not a passing result or a measured fraud rate. No ML model was trained or configured.
- The original 62-transaction PostgreSQL/analyst walkthrough and its unresolved independent-review requirements remain separate and unchanged. No database writes were made by the simulator.
- Initial complete PostgreSQL test run after adding the simulator: 584 passed, zero skipped, 90% combined coverage; two existing upstream Starlette/AnyIO warnings. The sandbox initially denied the PostgreSQL Unix socket; an approved execution completed the suite. After varying background purposes/recipients, the two focused simulator tests, global Ruff/format, strict mypy (135 source files) and diff whitespace check passed. The final complete PostgreSQL suite was rerun after the fixture edit: 584 passed, zero skipped, 90% combined coverage, with the same two upstream warnings. Frontend and dependencies were untouched.

## 2026-09-28 — Controlled Phase 16 simulator completed

- Added separate fingerprinted `risk-v2-sequence-experimental`. It consumes exact compatible risk-v1 rules-only and sequence-v1 results, raises a MEDIUM/STEP_UP_VERIFICATION review suggestion for a complete matched sequence, and preserves risk-v1 or abstains when evidence is missing. Incompatible evidence fails. It does not alter risk-v1 scores, assert probabilities, execute bank actions or admit profiles.
- Regenerated `controlled-results-v2` manifest (SHA-256 `6d691313369150cf9f6aedafaa23d13d82f14b966b65e5f89c1cbaa95b8aead6`). All A–E controlled checks pass. E retains the historical risk-v1 LOW/ALLOW failure on all six transfers; its first two also remain LOW/ALLOW under v2, then complete sequence matches suggest MEDIUM review. This is deterministic software behavior with authored oracle labels, not a fraud-performance measurement or analyst verdict.
- Added an authenticated admin-only, no-store API report computed in memory and a read-only Scenario lab page with expectations, actual v1/v2 outcomes, reasons and pass/fail checks. No simulator data, evaluation, feedback, or profile admission was written to PostgreSQL. Documented the boundary in ADR-034 and the demo guides. The separate live analyst walkthrough and Phase 15 production security gate remain open.
- Final validation on disposable PostgreSQL 17.10: 587 Python tests passed, zero skipped, 90% combined coverage; Ruff/format, strict mypy across 136 source files, Alembic upgrade/check, frontend ESLint, 14 Vitest tests and Vite build passed. Two upstream Starlette/AnyIO warnings remain. The first sandboxed full run could not access the PostgreSQL socket; the approved rerun passed. No migration or dependency changed. Pushed commit `11bb17b` to existing PR #2; both backend and both frontend GitHub checks passed on that head. Docker runtime was not verified.

## 2026-09-28 — Independent synthetic sequence-policy falsification

- Reviewed the frozen Phase 16 result, research protocol and local dataset suitability assessment. ULB lacks behavioral identities/provenance and PaySim terms/provenance remain unverified; neither supports an honest risk-v2 calibration here. No external data, verified labels or predictive rates were invented.
- Added a separate seven-case, database-free challenge set under `ml/src/evaluation/sequence_challenge.py`, with an immutable-output CLI and frozen report. It found plausible benign batch reviews and an authored attack spaced outside the 24-hour window that remains LOW/ALLOW. Observable-identical benign/attack new-payee cases receive the same result. The report is a falsification aid, not a random sample or threshold selection set. Report SHA-256: `1d3f5e876d8f0678fe353cadf5d72000bf8318a0dddce1b5c3366ec2bdd98ab2`.
- Tightened risk-v2 compatibility to require the exact reviewed default sequence-policy fingerprint; a self-consistent custom threshold policy now fails rather than silently changing the review floor. risk-v1 remains unchanged. Regenerated the controlled Phase 16 manifest; all five checks still pass. New manifest SHA-256: `6b383983bc71874e86eaa45bd8c7062b74c00421742b28926bda1c059841f9e2`.
- Added a reproducibility and negative-findings guide, updated ADR-034/architecture map and the handoff. No PostgreSQL business rows, analyst verdicts, profile admissions, model training or production policy changed. The live analyst walkthrough and Phase 15 security gate remain open.
- Final disposable PostgreSQL regression: 590 passed, zero skipped, 90% combined backend/ML coverage. Ruff/format and strict mypy (137 source files) passed. Two unchanged upstream deprecation warnings remain. No frontend, migration, dependency, Docker-runtime or remote-deployment change was made.

## 2026-09-28 — Roadmap handoff correction

- Corrected a repeated handoff loop after the user pointed it out. The original specification defines Phase 16 as deterministic synthetic data for five scenarios; that engineering deliverable is complete. The later live analyst walkthrough is a separately tracked extension blocked on independent reviewer evidence, not a reason to repeat Phase 16 or prevent Phase 17.
- Rewrote NEXT_SESSION_PROMPT.md around a concrete Phase 17 offline comparison of four profiling strategies on the same frozen chronological synthetic streams. It explicitly parks the live walkthrough, forbids tuning on the A–E and seven challenge examples, and requires the next handoff to advance to a different task. Clarified the old ADR-033 closure wording; no detector, schema or frontend behavior changed.

## 2026-09-28 — Phase 17 frozen four-strategy profile comparison

- Started isolated branch `codex/phase17-profile-experiment` from the still-open Phase 16 PR #2 head. Wrote `docs/research/phase17-profile-comparison-v1-protocol.md` before interpreting results. Added a new offline versioned stream with four customers, 80 oracle-assumed baseline observations, 21 candidates and distinct event, arrival and feedback clocks. Canonical source SHA-256: `fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`. No random source, database or human verdict was used.
- Compared mean/static, median-MAD/static, naive-adaptive mean and gated-adaptive median on the identical stream. Each candidate was excluded from its own pre-decision snapshot; only feedback available before a decision could affect the gate. C arrived before B's simulated legitimate feedback. At C, the naive mean reference was 408,714.285714… KZT after immediate admission of B's 8M payment, compared with 29,150 KZT before B; the gated median remained 29,000 KZT. Twelve D events were accepted after available simulated feedback, moving the gated short median from 30,000 to 79,999.5 KZT. E's six unverified events were admitted by naive adaptation and none by the gate. Gate actions: 13 ACCEPT, one QUARANTINE and one REJECT_FROM_PROFILE.
- Frozen report SHA-256: `940d74a09a591016ab93d3180c03097deb3016c2369fa4d85fb97f1f5dc3bda8`. The report contains all strategy/candidate rows and availability data. Tests cover deterministic byte replay, candidate exclusion, feedback at an exact decision boundary, source tampering, future baseline contamination and arrival ordering. The four combinations confound statistic and admission policy; one authored stream cannot establish causal or external effectiveness, calibration or prediction quality. No thresholds were selected.
- Final validation on disposable PostgreSQL 17.10: 594 Python tests passed, zero skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy across 138 source files and offline source/wheel build passed. Two existing upstream Starlette/AnyIO deprecations remain. No frontend, dependency or migration changed. The optional live analyst walkthrough and Phase 15 remote security stay parked/open.
- Published code commit `6c29c7f` on `codex/phase17-profile-experiment` and opened draft stacked PR #3 against the still-open Phase 16 branch. Both backend and both frontend GitHub checks passed on that code head. The PR is for review; neither branch was merged.

## 2026-09-28 — Phase 17 six-cell factorial and sensitivity probes

- Confirmed stacked PR #3 remains open against PR #2, with prior remote backend/frontend checks green. Kept the first Phase 17 source and report untouched; their SHA-256 values remain `fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e` and `940d74a09a591016ab93d3180c03097deb3016c2369fa4d85fb97f1f5dc3bda8`.
- Wrote `docs/research/phase17-profile-factorial-v1-protocol.md` before running the new comparison. Added a separate six-cell offline runner crossing mean or median/MAD with static, naive and gated update policies. Each statistic pair shares admitted IDs. The new report is SHA-256 `4ce0a58640c3850f556de8d6776fa1a7bfb1a2b57e83abb40d9ef1bd25860b58`; it records all 126 cell/candidate rows and three separately hashed sensitivity variants.
- On this authored stream, the naive mean before C reached 408,714.285714… KZT after admitting B's 8M payment, but its paired naive median stayed at 29,000 KZT. The gated mean/median references stayed at 29,150/29,000 KZT. Static D kept 20 long-window observations, while naive/gated ended at 32 after assumed feedback; unverified E stayed out of the gate but entered naive profiles. These are descriptive profile values, not predictive metrics.
- At D2's exact arrival, delayed D1 feedback was unavailable and the gated pre-count was 20 instead of 21. False simulated LEGITIMATE confirmations after E's sequence caused six additional gate accepts and E final count 26, exposing the trusted-confirmation dependency. B arriving after C returned `UNSUPPORTED_REQUIRES_REPLAY`; no historical correction or invented numeric outcome was produced. All candidate exclusion, hash guards and byte-for-byte report replay are tested.
- Final disposable PostgreSQL 17.10 suite: 599 passed, zero skipped, 90% combined backend/ML coverage; two unchanged upstream Starlette/AnyIO warnings. Ruff/format, strict mypy (139 source files) and offline source/wheel build passed. No frontend, migration, dependency, production database or live analyst state changed.
- The next handoff is a distinct append-only retraction/replay research fixture for late arrivals and revoked confirmations. The optional live analyst walkthrough and Phase 15 remote security gate remain separate and parked/open.

## 2026-09-28 — Phase 17 offline retraction and replay fixture

- Confirmed draft PR #3 remained open on `codex/phase17-profile-experiment` against PR #2, with a clean starting worktree. Wrote `docs/research/phase17-retraction-replay-v1-protocol.md` before interpreting a new fixture. The source generator uses two synthetic customers, five assumed approved baseline observations each, stable UUIDv5 IDs and distinct event, arrival, feedback, revocation and processing clocks. Canonical source SHA-256: `a47cf3b27e4556da4fa71554f6057570a7135c7ad56be71b01219ee1064a74dc`. Committed readable source file SHA-256: `158a4c2e10af3ab37ff789f460018f73d6f032a08941364f8c165eded749975d`.
- Added a pure offline runner that retains each original point-in-time gate outcome and profile snapshot. L2 was originally admitted; later-arriving, earlier-event-time L1 could not be applied by the unchanged gate and was recorded `REQUIRES_HISTORICAL_REPLAY`. An explicit corrected view replays L1 then L2 in event order and holds seven observations, while both original six-observation views remain intact. R1 was originally accepted before a simulated confirmation revocation; a later corrected view excludes it and returns to five baseline observations without asserting fraud. Each view has source/cutoff/provenance and supersession IDs.
- Correction request IDs replay the same view on identical scope/cutoff and reject changed bodies. Tests cover byte-for-byte report/source replay, source tampering, strict feedback and revocation boundary, processing order, customer isolation, original-view preservation and duplicate correction. Frozen report SHA-256: `cca72cb96342a02754e26a8f2388faee66445ec76776cc802c6b73c57239683b`.
- Final disposable PostgreSQL 17.10 regression: 604 Python tests passed, zero skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy across 140 source files and offline source/wheel builds passed. Two unchanged Starlette/AnyIO warnings remain. No PostgreSQL business row, live admission, frontend, migration, dependency, model or production risk policy changed.
- The next task is a read-only behavioral-dataset readiness auditor with explicit provenance/availability failures, not another replay or threshold-tuning run. The optional live analyst walkthrough and Phase 15 remote security remain separate open tracks.

## 2026-09-29 — Phase 17 manifest-level behavioral dataset readiness

- Confirmed Phase 17 draft PR #3 remained open on the clean `codex/phase17-profile-experiment` branch against PR #2; all prior backend/frontend checks were green. Read the existing ULB metadata/manifest and research boundaries. Wrote `docs/research/phase17-dataset-readiness-v1-contract.md` before auditing the frozen cases.
- Added the read-only `ml/src/datasets/readiness.py` CLI and four small JSON manifests. The auditor checks source/version/hash syntax, documented license/research permission/privacy/retention references, fourteen behavior-v1 identity/clock/admission capabilities, minute-level declared precision and an ordered UTC/customer-disjoint split plan. Missing, explicitly absent and unknown declarations receive distinct machine-readable outcomes. JSON parsing rejects duplicate keys, nonfinite literals and files above 1 MiB; output paths are create-only. PASS verifies a declaration/reference exists, not that the external evidence or rows are authentic.
- Frozen report SHA-256: `24741c4c30671b0c38e2b2136186f6281e7507b4265460cb18a6eb55ca10182e`. A fictional complete manifest yields only `READY_FOR_ROW_AUDIT` while remaining behavioral-validation-ineligible. Missing arrival/decision clocks and unknown label availability block their respective fixtures. The known ULB v3 manifest, transcribed from committed metadata and the original protocol, is BLOCKED by six explicit failures and ten unknowns for behavior-v1. It remains a separate ulb-pca-v1 retrospective benchmark. No ULB rows, held-out scores, private data or model fitting were used.
- Tests cover deterministic byte replay, input/source immutability, missing/absent/unknown codes, invalid governance evidence/hash/precision/splits, ULB metadata consistency, malformed JSON, duplicate keys and create-only CLI behavior. Final disposable PostgreSQL 17.10 regression: 609 passed, zero skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy across 141 source files and offline source/wheel builds passed; two existing upstream Starlette/AnyIO warnings remain. Frontend, migrations and dependencies were unchanged.
- The next task is a prospective validation protocol and acquisition/independent-review gates, not another synthetic detector run or manifest audit. No suitable real behavioral validation source is currently established in this repository. The optional analyst walkthrough and Phase 15 remote security remain separate open tracks.

## 2026-09-29 — Phase 17 prospective behavioral validation protocol

- Confirmed clean `codex/phase17-profile-experiment` branch and draft PR #3 OPEN against `codex/phase16-demo-evidence`. Wrote and froze `docs/research/phase17-prospective-behavioral-validation-v1.md`; exact SHA-256 `501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2`. The registration README explicitly records `PROTOCOL_ONLY / DATA_NOT_ACQUIRED`.
- Predeclared owner/legal/privacy authority, source and trusted-admission lineage, strict event/arrival/decision/feedback/revocation point-in-time rules, row-level rejection, chronological and customer-disjoint splits, label-maturation cutoffs, validation-only model/threshold selection, untouched final testing, review burden, uncertainty, immutable evidence package, independent sign-offs and stop conditions. Dataset-specific split boundaries, review budget and support parameters remain unassigned until a signed pre-outcome addendum for an eligible source exists.
- No real behavioral source, owner permission, signed addendum, verified label, model fit, calibrated threshold or predictive metric was created. ULB v3 remains PCA-only/behaviorally ineligible. No business data, database row, frontend, migration, dependency or production policy changed. Optional live analyst walkthrough and Phase 15 security release gate remain separate open tracks.
- Documentation validation: the frozen SHA-256 was recomputed and matched the registration README; all three new relative links resolve; `git diff --check` passed; the focused pre-existing dataset-readiness suite passed (5 tests). No application code, schema, frontend or dependency changed, so the last full PostgreSQL regression remains 609 passing tests from the previous checkpoint. Remote PR checks are to be read after publication; no new predictive measurement was attempted.

## 2026-09-29 — Phase 17 fictional row-level acceptance rehearsal

- Confirmed `codex/phase17-profile-experiment` was clean at start; stacked draft PR #3 and its Phase 16 base PR #2 were OPEN. Rechecked the frozen prospective protocol SHA-256 `501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2` and wrote `docs/research/phase17-fictional-row-acceptance-v1-plan.md` before generating the new fixture/report.
- Added bounded, synthetic-only, read-only `ml/src/datasets/row_acceptance.py` with a create-only CLI. It checks transaction IDs, finite amount, UTC chronology, arrival before decision, stable declared identity/cohort, decision-time split, strict same-customer/currency prior history, candidate/window boundaries and simulated feedback/admission/revocation availability. Rejections and UNKNOWN provenance have stable codes. Original and later corrected views have distinct linked IDs; later source bytes cannot rename an unchanged original known context. No PostgreSQL or model path is used.
- Froze new tiny source/report under `ml/experiments/phase17-fictional-row-acceptance-v1`. Source SHA-256: `1c0e1ea8e1c5652a938e7cdbeaf766d788d1312e8fca783f818f292968b34b2f`; report SHA-256: `2b67f5fa0ae149bbd3014d0821e1a1d34e1220a8eb5c35154aee401cc06d7358`. Original candidate C has raw H1/H3/H4 and simulated trusted H1/H4; later correction sees H2/H3 and removes H4 after its simulated revocation. Intentional duplicate, naive timestamp and arrival-after-decision rows make the overall report BLOCKED. All assumed confirmations are fictional; no verified label or source authority is asserted.
- Eight new focused tests cover replay/source immutability, exact cutoffs, self/boundary exclusion, duplicate/conflicting rows, customer/currency isolation, held-out overlap, alias conflict, missing provenance, invalid clocks and create-only CLI. Final full suite on disposable PostgreSQL 17.10: **617 passed, zero skipped, 90% combined backend/ML coverage**, with two existing Starlette/AnyIO warnings. Ruff, format and strict mypy (142 source files) passed. The first sandboxed full run could not reach the owner-only Unix socket; the approved rerun passed. No frontend, migration, dependency, live profile, model or production policy changed.
- No independently permitted behavioral source, signed addendum, real trusted-admission lineage, model fit or predictive metric exists. The next concrete task is a blank data-owner evidence/sign-off packet; do not fill it with invented authority or source-dependent parameters. The optional live analyst walkthrough and Phase 15 remote release gate remain separate.

## 2026-09-29 — Phase 17 blank data-owner evidence and sign-off packet

- Confirmed clean `codex/phase17-profile-experiment` at start and verified PR #3 remains open, stacked on open PR #2. Re-read the frozen prospective protocol, fictional row plan/report, readiness contract and development boundary. Left all frozen protocols, sources and reports unchanged.
- Added `docs/research/phase17-owner-packet-v1/` with a not-sent evidence request, a versioned source-specific addendum template, and an independent gate-by-gate disposition form. These are explicitly `TEMPLATE_ONLY`, unsigned, source-neutral and non-authorizing. Source fields, authority, permissions, dates, counts, labels, review budgets and every signature remain `UNSET`. Reviewer responsibilities are named for data ownership/stewardship, legal/privacy, chronology/identity, labels/admissions, methodology, operational review capacity and final-test custody.
- Recorded the required acquisition order and hard stops: verify written authority, privacy/custody and transfer controls before any row transfer; verify source/hash, extraction, identity and all availability clocks before row analysis; predeclare split/maturation/support/review-budget and preserve untouched-test custody before outcome inspection or training. No source owner was contacted; no private data was received or opened. Predictive validation remains OPEN/BLOCKED BEFORE TRAINING. ULB remains behavior-v1-ineligible.
- Updated `PROJECT_STATUS.md` and `NEXT_SESSION_PROMPT.md`: the next action is conditional review of user-supplied owner evidence at Gate 0; if none is supplied, stop without another synthetic checkpoint. Phase 15 security and the parked live analyst walkthrough remain distinct.
- Documentation-only validation: checked packet links and required placeholder/non-approval markers, recomputed frozen prospective protocol and fictional harness hashes, and ran `git diff --check`. No application code, database, frontend, migration or dependency changed; no full suite was run. PR #3 publication/check status must be re-read after any push.
