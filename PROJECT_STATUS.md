# FraudLens project status

Current checkpoint: **Phase 17 evidence/sign-off packet prepared; real data acquisition is blocked.** The blank, unsigned [source-owner packet v1](docs/research/phase17-owner-packet-v1/README.md) includes an evidence request, source-specific addendum template and independent disposition form. It contains no source-specific approval, permission or signature and authorizes no contact, transfer, row access or analysis. The fictional row harness remains unchanged: source SHA-256 `1c0e1ea8e1c5652a938e7cdbeaf766d788d1312e8fca783f818f292968b34b2f`; report SHA-256 `2b67f5fa0ae149bbd3014d0821e1a1d34e1220a8eb5c35154aee401cc06d7358`. Its `BLOCKED` status is intentional. The prospective protocol remains frozen at SHA-256 `501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2`; no independently permitted behavioral source or signed addendum exists, so predictive validation is OPEN and no training may begin. Phase 16's original objective is complete; the optional analyst walkthrough and Phase 15 remote security are separate open tracks.
Next work: **external acquisition gate, not another synthetic checkpoint.** If the user obtains a source-owner response, review its written authority and supporting evidence against packet Gate 0 before any data transfer or row access. If no evidence is supplied, stop with predictive validation OPEN; do not create more synthetic data, train, or contact an owner. The parked analyst walkthrough and production security gates stay separate.
This is a research/portfolio checkpoint, not a deployed fraud product. Profile reads
do not establish legitimacy, score risk or admit transactions.

## Completed capabilities

- [x] Phase 17 data-owner evidence/sign-off packet prepared as blank templates at
  `docs/research/phase17-owner-packet-v1/`. It names concrete owner artifacts,
  independent verifier roles, gate order, signature requirements, and hard
  stops for missing authority, privacy/custody, chronology, identity, labels,
  admissions, splits, review capacity and final-test controls. All source and
  reviewer-specific fields are `UNSET`; each form is explicitly unsigned and
  grants no permission or approval. No source owner was contacted and no data
  was received. Real behavioral validation remains OPEN/BLOCKED before training.

- [x] Phase 17 fictional row acceptance checkpoint: predeclared
  `docs/research/phase17-fictional-row-acceptance-v1-plan.md` before freezing
  the new source/report under `ml/experiments/phase17-fictional-row-acceptance-v1`.
  `ml/src/datasets/row_acceptance.py` is a bounded synthetic-only, create-only,
  read-only CLI. It emits reason-coded row/identity/split and point-in-time
  context outcomes, with a distinct corrected view linked to the original.
  Original C has raw H1/H3/H4 and trusted H1/H4; later knowledge adds H2/H3
  to trusted and removes revoked H4 without rewriting the original. Deliberate
  duplicate, naive-time and arrival-after-decision rows leave overall status
  BLOCKED. Source/report SHA-256 values are
  `1c0e1ea8e1c5652a938e7cdbeaf766d788d1312e8fca783f818f292968b34b2f`
  and `2b67f5fa0ae149bbd3014d0821e1a1d34e1220a8eb5c35154aee401cc06d7358`.
  Final disposable PostgreSQL 17.10 regression: 617 tests passed, zero
  skipped, 90% combined backend/ML coverage; Ruff/format and strict mypy
  (142 source files) passed. Two unchanged upstream Starlette/AnyIO warnings.
  No backend business logic, real rows, model, frontend, migration or
  dependency changed. Remote CI status is tracked on draft PR #3.

- [x] Phase 17 prospective validation registration: froze
  `docs/research/phase17-prospective-behavioral-validation-v1.md` before any
  independently permitted behavioral data acquisition. SHA-256:
  `501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2`.
  The registration README records `PROTOCOL_ONLY / DATA_NOT_ACQUIRED`. The
  protocol specifies owner and independent privacy/legal authority, stable
  pseudonyms and separate event/arrival/decision/feedback/revocation/admission clocks, row-level leakage rejection, immutable
  context/correction provenance, chronological and customer-disjoint testing,
  label maturation, validation-only selection, workload/uncertainty reporting,
  independent reviewers and fail-closed stop conditions. No sample, labels,
  model, threshold or performance estimate was created. PR #3 remains open
  against the Phase 16 branch; local validation details are in SESSION_LOG.md.

- [x] Phase 17 fourth research checkpoint: predeclared
  `docs/research/phase17-dataset-readiness-v1-contract.md` and implemented a
  manifest-only auditor at `ml/src/datasets/readiness.py`. Four frozen small
  manifests cover fictional declared completeness, missing chronology,
  unknown label availability and committed ULB v3 metadata. The report SHA-256
  is `24741c4c30671b0c38e2b2136186f6281e7507b4265460cb18a6eb55ca10182e`.
  Fictional completeness permits only later row audit; the other three are
  BLOCKED with stable machine-readable failure/unknown codes. ULB has six
  explicit absent requirements and ten unestablished ones. Every result has
  `behavioral_validation_eligible=false` and `production_eligible=false`.
  No raw/private source rows, model, risk policy, database, frontend,
  migration or dependency changed; no field metrics were created. Final
  disposable PostgreSQL 17.10 regression: 609 Python tests passed, zero
  skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy (141
  source files) and offline source/wheel build passed. Two existing upstream
  Starlette/AnyIO warnings remain. Draft stacked PR #3 remains open.

- [x] Phase 17 third research fixture: predeclared
  `docs/research/phase17-retraction-replay-v1-protocol.md` and frozen
  `ml/experiments/phase17-profile-retraction-v1/{source,report}.json`.
  Canonical source SHA-256:
  `a47cf3b27e4556da4fa71554f6057570a7135c7ad56be71b01219ee1064a74dc`;
  report SHA-256:
  `cca72cb96342a02754e26a8f2388faee66445ec76776cc802c6b73c57239683b`.
  The runner uses the unchanged pure gate for original applies and chronological
  corrected projections, preserving original profiles and their knowledge
  cutoffs. It records explicit historical-replay need, revoked-confirmation
  exclusion, supersession links and duplicate correction attempts. No live
  profile, database, risk policy, model, frontend, migration or dependency
  changed. All results remain synthetic-only and production-ineligible. Final
  disposable PostgreSQL 17.10 regression: 604 Python tests passed, zero
  skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy (140
  source files) and offline source/wheel build passed; two existing upstream
  Starlette/AnyIO deprecations remain. Draft stacked PR #3 remains open.

- [x] Phase 17 second research experiment: predeclared
  `docs/research/phase17-profile-factorial-v1-protocol.md` before computing a
  versioned six-cell report, with canonical source SHA-256 unchanged at
  `fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`.
  Report SHA-256:
  `4ce0a58640c3850f556de8d6776fa1a7bfb1a2b57e83abb40d9ef1bd25860b58`.
  Statistic pairs share exact admitted IDs. Naive mean shifts after B but
  naive median remains 29k even with B admitted. The sensitivity report
  records exact feedback-boundary withholding, six E admissions under
  intentionally false confirmations, and an explicit unsupported out-of-order
  case. No existing policy, database row, frontend, migration or dependency
  changed. All results remain synthetic-only and production-ineligible. Final
  disposable PostgreSQL 17.10 regression: 599 Python tests passed, zero
  skipped, 90% combined backend/ML coverage. Ruff/format, strict mypy (139
  source files) and offline source/wheel build passed. Two existing upstream
  Starlette/AnyIO warnings remain. PR #3 is open against PR #2; remote checks
  for this checkpoint are tracked on the PR.

- [x] Phase 17 first research experiment: frozen
  `profile-comparison-stream-v1` source SHA-256
  `fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`
  drives mean/static, median-MAD/static, naive-adaptive mean and gated-adaptive
  median profiles on the same chronological events. The protocol was written
  before results were interpreted; simulated feedback is released only after
  its availability time and the candidate is excluded from its own snapshot.
  The pure domain `ProfileUpdateGate` decides gated admissions; no PostgreSQL
  write, analyst identity, trained ML model or risk threshold selection occurs.
  The committed report SHA-256 is
  `940d74a09a591016ab93d3180c03097deb3016c2369fa4d85fb97f1f5dc3bda8`.
  It records all 84 pre-decision strategy/candidate rows, final profile states,
  13 ACCEPT, one QUARANTINE and one REJECT_FROM_PROFILE gate outcomes, and six
  unverified E candidates with no gate admission. Static short-window history
  becomes unavailable at the final cutoff; the report does not encode this as
  low risk. Chronology, delayed-feedback boundary, hash tamper rejection and
  byte-for-byte replay are tested. Validation: 594 Python tests passed, zero
  skipped, 90% combined backend/ML coverage on disposable PostgreSQL 17.10;
  Ruff/format, strict mypy (138 source files) and offline source/wheel build
  passed. Two existing upstream deprecations remain. No migration, dependency
  or frontend changed. Draft stacked PR #3
  (`codex/phase17-profile-experiment` against the Phase 16 branch) is open;
  both backend and both frontend GitHub checks passed on code head `6c29c7f`.

- [x] Completed controlled Phase 16 simulator: `data/synthetic` contains deterministic
  `customers.csv`, `recipients.csv`, `transactions.csv` and
  `scenario_manifest.json`. It creates 200 prior transactions for each of 10
  customers, with three ordinary fictional purposes/known recipients, then
  39 authored A–E candidates. The simulator assumes the last 100 prior facts
  are oracle-approved **only in memory** to exercise production pure behavior
  code. No PostgreSQL row, analyst verdict, genuine legitimacy claim or model
  training is created. A gives LOW/ALLOW/ACCEPT; B gives
  MEDIUM/STEP_UP_VERIFICATION/QUARANTINE; C stays HIGH/HOLD_AND_REVIEW against
  the unchanged 29k KZT median; 30 D admissions raise the short median from
  29k to 94,310 KZT. E's six small transfers are quarantined when no verdict
  exists. risk-v1 still returns LOW/ALLOW; the distinct risk-v2 policy raises
  a MEDIUM review suggestion after a complete sequence match, starting at
  transfer three. All A–E controlled checks pass; the legacy gap remains
  recorded. The original 62-row database demo is unchanged.
- [x] Versioned `risk-v2-sequence-experimental` consumes matching, fingerprinted
  risk-v1/sequence-v1 evidence. It rejects incompatible evidence, never turns
  missing input into a match, preserves risk-v1 when no complete signal exists,
  and neither changes its score nor claims calibration. `Scenario lab` is an
  admin-only read-only page backed by an in-memory no-store endpoint. It shows
  authored expectations separately from outcomes and explicitly disclaims
  analyst verdicts, model inference and database writes. ADR-034 documents the
  policy. Generated manifest SHA-256:
  `6b383983bc71874e86eaa45bd8c7062b74c00421742b28926bda1c059841f9e2`.
  Final disposable-PostgreSQL validation for the next checkpoint: 590 Python
  tests passed, zero skipped, 90% combined coverage. Ruff/format and strict
  mypy (137 source files) passed. The previous Alembic upgrade/check and
  frontend ESLint, 14 Vitest tests and build passed; they were unchanged.
  Two existing upstream deprecation warnings remain. No migration or dependency
  changed. Both backend and both frontend GitHub checks passed on PR #2
  head `11bb17b`; Docker runtime remains unverified.

- [x] Independent `sequence-challenge-v1` falsification audit uses seven new
  authored cases separate from the A–E generator. Its deterministic offline
  report SHA-256 is
  `1d3f5e876d8f0678fe353cadf5d72000bf8318a0dddce1b5c3366ec2bdd98ab2`.
  A benign known-payee batch and an identical-observation benign/attack
  new-payee pair all receive MEDIUM review suggestions; an authored attack
  spaced 25 hours apart remains LOW/ALLOW. Missing verified baseline abstains.
  These are selected synthetic counterexamples, not independent verified labels
  or rates. No thresholds were tuned. risk-v2 now requires the exact default
  sequence-v1 policy fingerprint, rejecting self-consistent unreviewed threshold
  changes. See `ml/experiments/sequence-challenge-v1/README.md`.

- [x] Phase 16 first checkpoint: versioned `demo-scenarios-v1` fixture with four
  synthetic customers and 62 deterministic KZT transaction facts spanning the
  five specified stories; B/C share a customer and prior history. Local CLI
  previews the full manifest and SHA-256 without a database. Explicit `--apply`
  requires a Unix-socket `*_test` PostgreSQL database and refuses production.
  Existing enrollment/submission services retain audit, outbox and idempotency;
  exact rerun creates no duplicate transaction/audit/outbox rows.
- [ ] Optional live analyst walkthrough: fixture stories are authored intent, not verified labels or measured risk.
  It creates no trusted profiles, admissions, evaluations, cases or feedback.
  `docs/demo/README.md` now gives a manual authorized review path and explicit
  missing-evidence cautions; executing that path and validating resulting safe
  admissions remain a separate deferred demonstration, not a prerequisite for Phase 17.
- [x] Phase 16 second checkpoint: `--progress` reads fixture fact matches, retained
  evaluations and captured profile versions, case/feedback state, learning decisions,
  and immutable profile revision counts/medians/admitted IDs in one repeatable-read,
  read-only PostgreSQL transaction. It uses the same local `*_test`/Unix-socket and
  non-production guard as `--apply`; mismatched fixture facts suppress evidence
  attribution. No verdict or admission is generated. ADR-030
  and the five-story guide specify what would constitute recorded evidence for each
  story and where historical availability remains unproven. At that checkpoint,
  before later local seeding, `--progress` reported 62 ABSENT facts.
- [x] Phase 16 third checkpoint: `--walkthrough` renders the same guarded,
  read-only PostgreSQL snapshot as a concise A–E presenter guide. It names the
  14 candidate transfers, recorded experimental risk status/captured version,
  case/feedback/learning counts, current profile version, event-time-compatible
  revisions with an availability warning, and the next manual step. It checks
  manifest identity and never infers a verdict, admission, B/C baseline
  preservation or D adaptation. ADR-031 and the demo guide document this.
  Its initial read-only smoke showed 62 ABSENT fixture facts and no profile
  revisions. Later local staging added BASELINE and A as detailed below.
- [x] Phase 16 fourth checkpoint: `--apply-stage` partitions the unchanged
  manifest into BASELINE, A, B, C, D1–D5 and E1–E6. It uses the existing
  audited/idempotent transaction service and the same Unix-socket `*_test`
  guard. New candidate stages require matching prior facts; B/C/D/E require a
  verified prior KZT profile, C requires a retained B evaluation and separate
  learning decision, later D steps require prior ACCEPT evidence, and later E
  steps require a prior evaluation. Missing evidence stops the stage; no review,
  admission or evaluation is generated. Exact replay is idempotent but does not
  prove original stage chronology. Bulk `--apply` remains facts-only. ADR-032
  records that this local sequence does not reconstruct bank arrival time.
- [x] Phase 16 read-only preflight extension: `--check-stage STAGE` runs the same
  disposable-database prerequisite checks without writing and reports READY,
  BLOCKED with a specific reason, CONFLICT, or REPLAYABLE. Apply rechecks under
  the fixture lock; the preview is not a reservation or proof of human review.
  An actual read-only check of B on the working test DB reported BLOCKED for
  absent baseline facts. PostgreSQL tests cover state transitions and conflicts.
- [x] Phase 16 provenance hardening: new B/C/D/E stages additionally require
  the first immutable profile revision to point to an accepted BOOTSTRAP whose
  admitted observations and stored learning evidence include at least five
  matching fixture baseline transactions and two distinct recorded reviewers.
  A verified profile built from unrelated data cannot unlock the staged story.
  C additionally requires B's separate exceptional-amount QUARANTINE decision
  with no profile version advance. These checks inspect retained workflow
  records; they do not independently verify people or external legitimacy.
- [ ] Optional live behavioral walkthrough remains pending external reviewer input.
  `demo-review-evidence-v1` now provides a separate deterministic companion
  entry for every fixture transaction. It uses obviously fictional names,
  purposes, locations and artifact references and is pinned by SHA-256
  `436c1c24119a12a7df63bf9f6ea4888a19c021b1eec94d4df945e83983687185`.
  Every record says synthetic-only, not real-world verified, production-ineligible
  and verdict-free. C/E deliberately have unavailable support. Authenticated,
  scope-checked users can read one entry through an experimental no-store endpoint;
  the console renders a strong role-play warning. The package does not change
  transaction facts, scoring, cases or profiles. ADR-033 records the boundary.
  The local console now lets a human admin explicitly run rules-only evaluation
  on an unevaluated transaction with an absent-profile assertion or a pinned
  pre-decision revision, then optionally open a separate review case. The
  backend continues to enforce scope, CSRF, idempotency and opt-in experimental
  writes; an analyst cannot submit an evaluation. Neither UI action creates a
  verdict or learning decision, and the ML bundle remains unconfigured locally.
  This is a usability improvement, not evidence that B/C/D have been demonstrated.
  On 2026-09-28 the user authorized step-by-step local setup. The guarded
  `--apply-stage BASELINE` command inserted 48 synthetic transaction facts and
  four customers into the working `fraudlens_test` database; read-only progress
  initially showed 48 MATCH and 14 ABSENT. A temporary local test-only machine admin
  credential was used through the authenticated API to create 10 experimental
  rules-only, absent-profile evaluations and 10 cases: five early BC and five
  early D baseline transfers. `analyst-one` subsequently entered LEGITIMATE
  feedback on all 10; `analyst-two` closed one already-reviewed case, which
  does not count as independent feedback. Two further untouched BC/D baseline
  transfers received absent-profile evaluations and empty OPEN cases for
  `analyst-two`. That analyst independently entered NEEDS_INVESTIGATION feedback
  on both, citing insufficient proof. Small amounts are not legitimacy evidence;
  transaction facts have no merchant, building or location to verify. Read-only
  SQL found no BC/D profile or learning decision. B/C/D outcomes remain
  NOT DEMONSTRATED.
  Story A passed read-only stage preflight and its single synthetic 25,000 KZT
  transfer was added through guarded staged intake. An authenticated rules-only
  evaluation with explicitly absent profile returned INSUFFICIENT_EVIDENCE:
  amount, new-recipient and unusual-time rules lacked baseline inputs. Read-only
  walkthrough showed 49 MATCH / 13 ABSENT; B preflight remains BLOCKED for no
  verified prior KZT profile. The two analyst accounts are scoped to BC/D, not
  A; story A can be shown through the local read-only walkthrough or an
  authorized admin view. No A case, verdict or profile admission was created.
  The presenter walkthrough's formerly generic advice for absent candidates
  now names each exact `--check-stage` and says to apply only when READY; it
  does not suggest bypassing B/C/D/E prerequisites. The focused PostgreSQL
  renderer test, Ruff, format and mypy passed; the live read-only walkthrough
  confirmed the corrected text. No migration or dependency changed.
  The existing `local-admin` account is active. Two friends privately chose
  passwords and provisioned separate active local accounts, `analyst-one` and
  `analyst-two`, each scoped to the BC and D fixture customers; read-only SQL
  verified their account roles, active status and scope without reading secrets.
  Local-only Uvicorn and Vite were started and their HTTP endpoints responded.
  Both accounts have since produced the review events above; no review was
  scripted by the setup process.
- [x] Latest full regression: 582 passed, zero skipped, 90% combined coverage on
  PostgreSQL 17.10; Ruff/format, strict mypy (133 source files), existing Alembic
  migration/schema tests, frontend ESLint/12 Vitest tests and Vite build passed.
  Two upstream deprecation warnings remain. The pre-change baseline was 579
  Python tests and 11 frontend tests. No migration or dependency changed.
  Docker engine and
  remote CI passed on both push and PR runs for the socket-based demo test fix
  in https://github.com/nuchaaa/FraudLens/pull/1 after the user explicitly
  authorized publication. The transaction worklist now explains
  that NOT EVALUATED is absence of a retained assessment, not a low-risk result;
  the detail view displays labeled fixture context when available and otherwise
  discloses missing merchant/payee/name/place facts. The reviewed
  native XGBoost synthetic bundle replayed offline, but the local API has no model
  bundle configured and intake never auto-evaluates. Real registry entries must
  not be attached to fictional transfers as if they were payment evidence.
- [x] Latest read-only Phase 16 evidence audit: 49 fixture facts MATCH, 13 ABSENT;
  13 retained experimental evaluations, 12 cases, 10 LEGITIMATE feedback entries
  and 2 NEEDS_INVESTIGATION entries. No learning decisions or profile revisions
  exist for any of the four demo customers. B stage preflight remains BLOCKED for
  a verified prior KZT profile. No new writes were made during this audit. The
  open PR's backend/frontend checks were confirmed passing on its current head.
- [ ] No institutional proof issuer, independent notification process or two
  authenticated remote admins has been provided. Phase 15 remote recovery and
  production human auth remain blocked as external release gates, not simulated.

- [x] Phase 15 foundation: threat model and accepted local ADR-021 human identity/session design.
- [x] Pure human-account scope and session expiry/rotation/revocation policies.
- [x] Explicit Argon2id password adapter, bounded Unicode inputs and secret-safe repr.
- [x] PostgreSQL account, session, consumed-refresh and bounded shared-throttle persistence
  in migration 0008; explicit-commit UoW and atomic account/session audit.
- [x] Audited getpass operator CLI for provision, recovery, disable, enable and policy change.
- [x] Opt-in human login/session/refresh/logout HTTP, current account checks, exact Origin,
  CSRF and revocable HttpOnly cookies; machine bearer access remains separate.
- [x] Console human login with in-memory CSRF, session restoration and serialized refresh;
  pasted service-token screen removed.
- [x] Dedicated-database grant plan separates migrator, API, worker and operator logins;
  production API/worker verify effective privileges and reject owner credentials.
  The local operator CLI is now barred from production and restricted runtime schemas.
- [x] PostgreSQL role test proves scoped workflows and denial of DDL, trigger disabling,
  history mutation, account provisioning, TEMP and cross-role reads.
- [x] Login/operator changes share an advisory account lock; recovery during login
  cannot authenticate the old password without API UPDATE on human accounts.
- [x] Separate HTTPS nginx candidate with explicit host/certificate startup checks,
  sanitized forwarded headers, HSTS/CSP and authored size/rate/concurrency/time limits.
- [x] Native local TLS/Nginx/FastAPI/PostgreSQL smoke verified Host/Origin, Secure
  cookies, 413/429, redirect and header replacement with disposable assets.
- [x] Production FastAPI now rejects human auth until verified MFA/recovery exists;
  password-only local sessions cannot be served in production mode. The local
  operator CLI rejects production mode and restricted dedicated runtime schemas.
- [x] ADR-025 records the fail-closed boundary and proposed WebAuthn/recovery
  ceremonies. ADR-026 records the local subset; verified recovery is absent.
- [x] Migration 0009 adds public-key authenticator material and durable two-minute,
  one-use, account/ceremony/origin/RP/version-bound challenges. Password-plus-assertion
  local login issues no session before signature verification; replay, counter and
  disabled-account paths were tested on PostgreSQL. First-factor enrollment is
  local analyst-only, requires current session plus fresh password, revokes sessions
  and increments authorization version. Console security-key flows use browser API.
- [x] Migrations 0010/0011 add session-bound additional-factor proof and different-key
  removal for local analysts. Fresh password plus existing-key assertion is
  required; the last key cannot be removed. Changes atomically revoke all
  sessions, advance authorization version and append audit. PostgreSQL tests
  cover key separation, session binding, replay, rollback and concurrency.
- [x] Expired challenge rows become deletable after one further day; a trigger
  rejects early deletion and TRUNCATE. A new challenge lazily prunes at most
  100 old rows. Immutable audit references remain; idle stores need maintenance.
- [ ] Admin approval, supervised remote bootstrap, independently verified
  two-operator recovery and physical-browser ceremony remain open.
- [x] ADR-028 and pure recovery policy require a frozen, version-pinned subject,
  bounded proof reference/digest, and two distinct fresh admin approval claims
  bound to the same case, purpose, proof and exact action digest. Current operator
  account snapshots must still be active admins at their approval versions;
  approval-carried role/active flags are not trusted. There is no caller, persistence,
  recovery-specific freeze binding, proof verifier, notification adapter or reset
  path; UUIDs/digests alone are
  not accepted as authentication. Production gate remains closed.
- [ ] Restricted API role has credential-presence SELECT only; it cannot write
  challenges/factors. Production human authentication remains disabled.
- [x] Supplemental `sequence-v1-experimental` evidence detects low-and-slow, gradual
  escalation, repeated-new-recipient and cumulative-exposure patterns on one captured context.
- [x] Sequence evidence requires a verified admitted baseline, retains missing semantics and
  remains outside risk-v1 scoring until a separately validated risk-v2 policy exists.
- [x] Console distinguishes stored INSUFFICIENT EVIDENCE from no evaluation and renders
  nested rule plus matched sequence reasons; older evaluation envelopes remain compatible.
- [x] Locked dependency audit found no known vulnerabilities at the previous
  unchanged-dependency checkpoint. No dependency or lockfile change this turn.
- [ ] Current localhost Compose still uses owner credentials; combined production
  roles/TLS/container topology, load limits, MFA/recovery, Docker/remote CI and
  independent security review remain before remote exposure.
- Human authentication is disabled by default and must be explicitly enabled locally.

- [x] Phase 14: responsive React 19/TypeScript/Vite local analyst console with six sections.
- [x] Exact scoped PostgreSQL summary and keyset-paginated transaction/evaluation/case worklist.
- [x] Retained explanations, profile reads and explicit-confirmation versioned case review.
- [x] Initial in-memory-only pasted credential checkpoint, subsequently replaced by Phase 15 login.
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

## Verification — 2026-09-20–27

- [x] Latest full run: **578 passed,
  0 skipped, 2 upstream warnings; 90% combined backend/ML coverage.**
- [x] Actual PostgreSQL 17.10, including prior-phase regressions.
- [x] Migration upgrade/downgrade/metadata tests and upgrade with populated legacy profile data.
- [x] Concurrent reader pins its version before another writer commits; old versions exclude
  backdated later admissions and retain their original timezone/window policy.
- [x] Ruff lint/format and strict mypy pass (131 backend/ML source files).
- [x] Frontend ESLint, 9 Vitest tests and TypeScript production build pass;
  frontend dependencies are unchanged.
- [x] Browser visual inspection passed for the responsive connection screen; no external assets.
- [x] Updated Phase 15 locked dependency audit: no known vulnerabilities,
  including the ML/dev groups and new `webauthn==3.0.1` dependency.
- [x] Source/wheel builds and Compose configuration pass.
- [x] Native disposable database upgraded; head is `0011_factor_removal_retention`,
  with 29 non-Alembic tables.
- [x] Separate fresh disposable role-test database migrated and removed, with four real
  login roles and a production-mode FastAPI/restricted-database HTTP check.
- [x] Homebrew nginx 1.31.4 rendered-configuration syntax check and local self-signed
  TLS smoke with a separate disposable PostgreSQL database. Verified HTTPS frontend,
  Host 421, Origin 403, `__Host-` Secure/HttpOnly cookies, session, 413, 429 and 308.
  An echo upstream confirmed forged forwarded identity/IP/protocol headers are replaced.
  Temporary certificate, cookies, processes and database were removed.
- [x] Production-edge shell startup rejected malformed host and missing certificate;
  the image itself could not run because Docker Desktop is not launchable here.
- [x] Actual worker CLI subprocess recorded/acknowledged an event and reported status in a disposable schema.
- [x] Actual local Uvicorn/PostgreSQL smoke passed: cold start, populated pinned profile,
  median/MAD/p95, authentication and cutoff validation, plus prior intake smoke checks.
  Temporary HTTP server and smoke schema were cleaned up.
- [ ] Docker image execution remains unverified; Docker Desktop installation has no
  launchable executable and the engine socket is absent.
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
See development.md for restart/stop, local human provisioning and service credential setup.
Business endpoints fail closed without a configured machine principal or enabled, current
human session. No actual API token is committed or left configured. Run
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 after setup.
Sandboxed PostgreSQL access may need approved execution outside the sandbox.
Tests require a disposable *_test database and use a generated schema; the migration
smoke also upgrades its default schema. Never substitute SQLite.

## Important files

- backend/app/demo/{scenarios,stages}.py: deterministic five-story transaction
  manifest and unchanged-fact stage partition.
- backend/adapters/demo/{__main__,progress,walkthrough}.py: guarded bulk/staged
  local seed, read-only evidence inventory and human-readable presenter guide.
- tests/{unit/test_demo_scenarios,integration/test_demo_seed}.py;
  docs/demo/README.md and ADR-029/030/031/032: fixture, evidence, guide and stage contracts.

- backend/app/identity/{policy,service,ports}.py: pure policy and identity workflows.
- backend/adapters/database/identity.py; backend/adapters/identity/__main__.py:
  PostgreSQL repository and operator CLI.
- backend/api/auth.py; backend/api/dependencies.py: opt-in browser auth and shared scopes.
- frontend/src/App.tsx, Connect.tsx and api.ts; tests/integration/test_human_auth.py:
  console login and PostgreSQL/HTTP security checks.
- backend/adapters/passwords.py; tests/unit/test_identity_policy.py: Argon2id and policy tests.
- docs/security/threat-model.md; docs/adr/ADR-021-human-identity-and-sessions.md: local design and release gates.
- backend/adapters/database/grants.py; tests/integration/test_database_roles.py:
  dedicated-schema grant plan, production role verification and actual login tests.
- docs/adr/ADR-023-runtime-database-roles.md; docs/security/deployment-gates.md:
  role rationale and remaining remote-deployment requirements.
- frontend/Dockerfile.production, nginx.production.conf.template,
  nginx-api-proxy.conf and start-production.sh: separate candidate HTTPS edge.
- docs/adr/ADR-024-local-https-edge-checkpoint.md and
  docs/security/mfa-and-recovery-requirements.md: local evidence and open human gates.

- backend/app/sequence/engine.py: pure deterministic sequence evidence and uncalibrated policy.
- backend/adapters/sequence/__main__.py: database-free retained-context replay.
- docs/adr/ADR-022-supplemental-sequence-evidence.md; docs/architecture/detector-layers.md.
- tests/unit/test_sequence_engine.py: low-and-slow, boundary, missingness and replay coverage.

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

- sequence-v1-experimental evaluates four candidate-inclusive 24-hour patterns over the
  retained strict prior context: low-value cumulative sequence, gradual escalation,
  repeated new recipient and cumulative exposure. It requires a verified profile workflow,
  at least five admitted observations and raw prior activity; otherwise every signal is
  NOT_EVALUATED. Its thresholds are authored and uncalibrated.
- Sequence evidence is added only to new experimental evaluation envelopes. It does not
  change behavior-v1, rules-v1, the reviewed native model, risk-v1 scores or actions. Older
  exact idempotent responses remain byte-for-byte replayable. Risk-v2 needs a frozen dataset,
  validation-only calibration and false-positive/operator-burden measurement.
- No authoritative IP, location, login/beneficiary lifecycle or cross-customer graph facts
  exist. Device/network/graph/anomaly layers must remain unavailable until versioned sources
  and point-in-time contracts are implemented; identifiers are not evidence of shared control.

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
  bypass triggers. The dedicated-schema runtime grant plan is locally verified, while
  the current Compose owner credential remains a deployment gap.
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
  derived append-only state; no production risk API exists. Local human login is opt-in;
  the console is not approved for remote exposure.
- External outbox destinations/audited redrive, idempotency retention, service-principal
  revocation, edge limits and deployment hardening remain unfinished. Runtime grants
  must be applied and verified in the actual topology.
- Service credentials are configuration snapshots; rotate while retaining principal UUID
  and restart all processes to apply revocation/scope changes. Remote use requires TLS.

## Exact next tasks

1. Prepare a source-specific data-owner evidence request and blank signed
   addendum template from the frozen prospective protocol. Identify which
   independent owner/privacy/chronology/method reviewers must supply which
   documents, source hashes, time semantics, custody terms, cutoffs and stop
   decisions. Leave all source-specific values explicitly UNSET.
2. Keep real behavioral validation gated on owner permission, privacy authority,
   authenticated source/row evidence, a signed addendum and independent
   reviewers. The fictional harness and complete manifest do not verify real
   rows. Do not train, tune risk-v2 or calculate predictive metrics until a
   suitable dataset is obtained and independently checked.
3. Keep the optional live analyst walkthrough parked until independent reviewers
   supply new evidence. Keep Phase 15 remote human auth and deployment closed
   pending institutional recovery, real four-role/TLS topology and security review.
   Never run grants on the public-schema demo or touch production data. Update
   all three checkpoint files before stopping.
