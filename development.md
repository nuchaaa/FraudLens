# Development and PostgreSQL tests

From the repository root, install full development/test dependencies with `uv sync --locked --group ml`.
Backend-only use can omit the ML group. macOS ML tests require `brew install libomp`.
The original workspace also has `../../work/bootstrap/bin/uv`; set
`UV_CACHE_DIR=../../work/uv-cache` when using that copy. Existing `.venv/bin`
executables work without a globally installed uv command.

## Current local test cluster

PostgreSQL 17.10 is installed at `/opt/homebrew/opt/postgresql@17/bin`.
The disposable cluster created for this task is at `../../work/fraudlens-postgres/data`
relative to the repository. It has database `fraudlens_test` and uses the current
macOS user's database role. It listens on a Unix socket, with no TCP listener.

If stopped, restart the existing cluster from the repository root:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl \
  -D ../../work/fraudlens-postgres/data \
  -l ../../work/fraudlens-postgres/server.log \
  -o "-h '' -k /private/tmp -p 55439 -c unix_socket_permissions=0700" -w start
```

Do not reinitialize the existing data directory. The socket uses local trust
authentication for synthetic tests only. The 0700 socket mode restricts access to
the operating-system owner. A sandboxed agent may need execution approval for
PostgreSQL shared memory and socket access; a normal local terminal does not.

```sh
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

Stop this cluster when no longer needed:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D ../../work/fraudlens-postgres/data -m fast -w stop
```

## Another machine or CI

Use PostgreSQL 17 with a dedicated database whose name ends in `_test`. Set
`TEST_DATABASE_URL` with the `postgresql+psycopg` driver. The test role needs schema
creation rights because the suite creates a unique temporary schema, applies real
Alembic migrations, tests an upgrade/downgrade, then drops only that test schema.
The migration smoke test also upgrades the supplied test database's default schema.
Without `TEST_DATABASE_URL`, database tests explicitly skip; that is not database
verification. Never use a production or shared business database for these tests.

CI provisions PostgreSQL as a service. Local Docker remains optional for database
testing and has not yet been runtime-verified in this workspace.

## Current application

```sh
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1
```

`/health/live` is public process liveness. Business routes require PostgreSQL and
configured credentials. Experimental writes are disabled by default; accepted
transactions remain RECEIVED and do not update profiles.

## Authenticated synthetic API

Configure `FRAUDLENS_DATABASE_URL` and apply migrations before sending requests.
`FRAUDLENS_API_PRINCIPALS` is a JSON array of entries with `principal_id`,
`token_sha256`, `roles`, `customer_ids` and `expires_at`. An empty registry denies all
business requests. The app refuses malformed configuration. Settings redact the
registry, and only token digests belong in configuration; never commit raw tokens.

For a local synthetic demonstration, generate a one-hour admin credential in your
own terminal (the token is printed once; keep it private):

```sh
.venv/bin/python - <<'PY'
import hashlib, json, secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4
token = secrets.token_urlsafe(32)
entry = {
    "principal_id": str(uuid4()),
    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
    "roles": ["admin"],
    "customer_ids": [],
    "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
}
print("Bearer token:", token)
print("FRAUDLENS_API_PRINCIPALS='" + json.dumps([entry]) + "'")
PY
```

Put the printed configuration assignment in your ignored `.env`, or export its value
in the server terminal, then start Uvicorn as shown above. The server reads the
registry on startup. Use `/docs` → Authorize to enter the bearer token. Production
mode disables docs; local development mode enables them.

First call `POST /api/v1/customers` with a generated synthetic UUID:

```json
{"customer_id":"00000000-0000-4000-8000-000000000001","timezone":"Asia/Almaty"}
```

Then call `POST /api/v1/transactions`, setting `Idempotency-Key: demo-transfer-1`:

```json
{
  "transaction_id": "00000000-0000-4000-8000-000000000002",
  "customer_id": "00000000-0000-4000-8000-000000000001",
  "recipient_id": "00000000-0000-4000-8000-000000000003",
  "amount": "30000.00",
  "currency": "KZT",
  "timestamp": "2026-09-20T12:00:00+05:00",
  "channel": "MOBILE",
  "device_id": "synthetic-demo-device"
}
```

Use fresh IDs for a new demonstration. Repeat the same transaction request/key to
see the original 201 body with `Idempotency-Replayed: true`. Change an amount under
that key to see 409. Retrieve the transaction using the response Location. Customer
enrollment is not idempotent replay: a duplicate customer ID returns 409.

For a producer credential, generate another random token/digest and principal,
use `roles: ["service"]`, and put only permitted customer UUIDs in `customer_ids`.
For read-only access, use `roles: ["analyst"]` and the same explicit customer scope.
Both roles are denied customer enrollment. Only admins have unrestricted customer
access. Enrolling a customer creates no trusted behavioral observations.

Rotate by replacing the digest while retaining the principal UUID and restarting
every API process. This keeps its durable idempotency namespace. Remove an entry,
reduce its scope or let it expire to deny future requests, including replay; restart
is required for configuration changes. Never reuse principal UUIDs for new identities.
Credentials are service keys, not user passwords; local human login is documented in Phase 15 below.

HTTP behavior: missing/invalid/expired token → 401, denied submission → 403,
missing or inaccessible transaction → 404, changed key body or duplicate ID → 409,
oversized body → 413, invalid fields/key → 422, unavailable storage → 503. Maximum
business body size is 16 KiB; keys contain 1–200 printable ASCII characters without
spaces. Responses and errors use no-store caching; validation errors omit input
values. Money must be a string, not a floating-point JSON number.

Use only synthetic data and localhost for this demo. Remote deployment needs TLS,
edge time/rate limits, restricted database roles and a security review. Outbox rows
are durable; the local worker runs only when explicitly invoked below. See [ADR-008](docs/adr/ADR-008-transaction-api-and-service-credentials.md)
for authorization, atomicity and the planned immutable transaction lifecycle.

## Customer behavior reads

Apply `alembic upgrade head` before using the Phase 4 route. The migration captures
existing profile heads without inventing older revisions. It does not enroll history.

Using an authorized service/analyst token or admin credential, call:

```text
GET /api/v1/customers/{customer_id}/profiles/KZT
```

An enrolled customer without a KZT profile receives 200 with `UNINITIALIZED`, null
version/amount statistics and zero counts. Customer scope is checked before storage;
unknown or inaccessible customers return the same 404. USD and KZT never share amounts.
The API contains no profile write endpoint. Populated histories currently come from
controlled repository fixtures; public transaction intake never establishes trust.

To repeat a read, pass its returned version and exact cutoff as query parameters:

```text
GET /api/v1/customers/{customer_id}/profiles/KZT?version=1&as_of=2026-09-20T07:00:00Z
```

The example requires that version to actually exist and its revision head to be no
later than the cutoff. `as_of` without a version, naive dates and future cutoffs return
422; unknown versions return 404; a cutoff before the selected revision returns 409.
Use query-parameter encoding (especially for timezone offsets containing `+`).

Statistics include only admitted observations strictly before the cutoff; observations
at the window's lower boundary are excluded too. A pinned revision excludes observations
admitted in later versions even when their transaction timestamps are old. For historical
research, use a version actually captured before the original decision; selecting a
version today is not proof that its history was available then.

Short/long amount statistics are Decimal strings. Empty statistics are null. The
response includes explicit cold/insufficient history, local hour counts, typical hours,
known recipients, observation frequency and policy version. All are descriptive;
`SUFFICIENT_HISTORY` is not a trust or risk verdict. See
[ADR-009](docs/adr/ADR-009-profile-reads-and-history.md) for exact policy and limitations.

## Phase 5 feature capture and offline replay

Configure the database and expiring `FRAUDLENS_API_PRINCIPALS` as above. Capture prompts
for the bearer token (or reads `FRAUDLENS_FEATURE_TOKEN`); never put a raw token in command
arguments. Use an existing synthetic transaction UUID in the authorized customer scope.

```sh
.venv/bin/python -m backend.adapters.features capture \
  --transaction-id 00000000-0000-4000-8000-000000000002 \
  --without-profile --output /private/tmp/fraudlens-feature-context.json
.venv/bin/python -m backend.adapters.features replay /private/tmp/fraudlens-feature-context.json
```

If a profile exists, replace `--without-profile` with `--profile-version 1` using the
actual pre-decision revision. Capture refuses to overwrite an existing file. Replay
needs neither credentials nor database access and prints the same 29 ordered features.
This computes inputs only, not fraud predictions. New captures may see late arrivals;
retain original artifacts to reproduce prior inputs. Files contain transaction facts;
keep them outside version control and restrict access appropriately. See ADR-010 for
limits and provenance. Synthetic demo timestamps must not be in the future.

## Phase 6 rule replay

After capturing a context using the Phase 5 command, evaluate the saved facts:

```sh
.venv/bin/python -m backend.adapters.rules /private/tmp/fraudlens-feature-context.json
.venv/bin/python -m backend.adapters.rules /private/tmp/fraudlens-feature-context.json \
  --amount-median-ratio 12 --prior-transfers-5-min 6
```

This local read-only command needs no credentials or database. It prints all five rule
outcomes, evidence, missing indicators and the exact policy fingerprint. Thresholds are
experimental; matches are reasons, not probabilities, verdicts or automatic actions.
A rule with unavailable input is NOT_EVALUATED. See ADR-011 for the complete contract.

## Phase 7 synthetic experiment

Run from the source checkout (ML code is deliberately excluded from the backend wheel):

```sh
uv sync --locked --group ml
# macOS only, if OpenMP is missing: brew install libomp
.venv/bin/python -m ml.src.training.experiment --output work/experiments/seed17 --seed 17
.venv/bin/python -m ml.src.training.experiment --output work/experiments/seed29 --seed 29
.venv/bin/python -m ml.src.training.experiment --output work/experiments/seed43 --seed 43
.venv/bin/pytest --cov=backend --cov=ml.src
.venv/bin/mypy
```

Output directories must not already exist. Source facts, prepared features, split IDs,
model, final predictions and hashes are saved with report.json. Load joblib files only
from trusted local runs. The reports explicitly prohibit production promotion.

Original-workspace recorded runs live at ../../work/phase7/final-seed17 (and 29/43).
Summary reports are in ml/experiments/phase7-synthetic-v1. The generator is fixed and
uses only authored facts; external dataset validation and a production model choice
remain unfinished. See ADR-012 and docs/research/dataset-assessment.md.

When using uv to run tests/types, pass `--group ml` so uv does not remove the optional
ML dependencies. CI now installs/tests this group, but remote CI is still unverified.

## Phase 7 external retrospective benchmark

ULB version 3 has a separate `ulb-pca-v1` feature contract. Its model is incompatible
with behavior-v1/customer profiles and is never loaded into business endpoints.
The source/license notice is docs/research/ulb-NOTICE.md; the frozen protocol is
ulb-benchmark-protocol.md. Use the optional ML group as above.

```sh
# Download public anonymized data to a new ignored local directory; network required.
.venv/bin/python -m ml.src.datasets.ulb --output work/ulb-v3
# All training and evaluation below is offline.
.venv/bin/python -m ml.src.training.ulb_benchmark \
  --source work/ulb-v3/creditcard.csv --output work/ulb-benchmark-v1
```

Existing workspace download: ../../work/phase7/ulb-v3/creditcard.csv.
Recorded successful run: ../../work/phase7/ulb-benchmark-v1-run2.
The first run stopped during CSV parsing before any training/evaluation; its directory
has no completed report. Quoted numeric parsing is now covered by a regression test.
Do not overwrite successful runs or tune on their test metrics. Summary reports are
under ml/experiments/ulb-retrospective-v1; raw rows, split indices and model stay local.

The pinned SHA256 check rejects changed source bytes. Label availability, arrivals,
customer identity and upstream PCA fitting scope remain unknown. This is retrospective
benchmark evidence only; it does not authorize deployment or behavioral-profile learning.

## Phase 8 experimental native inference

Use the optional ML group and libomp as above. Export only an existing reviewed local run:

```sh
.venv/bin/python -m ml.src.training.export_model \
  --run ../../work/phase7/final-seed17 --seed 17 --output work/experimental-seed17
```

The command prints its trusted manifest digest. Keep that value independently; do not
replace it with a checksum calculated from an untrusted incoming bundle. Native replay
loads no pickle, database or credentials. Use a saved behavior-v1 context within the
experimental KZT/UTC/180-day/30-day scope. Existing non-UTC profiles are rejected.

The verified workspace export and replay fixture can be run now:

```sh
.venv/bin/python -m backend.adapters.ml \
  --bundle ../../work/phase8/seed17 \
  --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903 \
  --context ../../work/phase8/first-context.json
```

A new export has a new manifest digest because exported_at changes. Use its own trusted
printed digest, not the example above. Outputs are explicitly synthetic and uncalibrated;
there is no automatic decision or API model loading. Model version is derived from the
native artifact hash. trained_at remains unknown; no database ModelVersion is fabricated.
See ADR-014. The retained replay fixture comes from the original synthetic source, not an
assumption about historical database commit times.

## Phase 9 experimental Risk + Decision

Run from the repository root using the same saved context and reviewed native bundle.
Rules-only needs no ML installation; model modes use the optional ML group from Phase 8.

```sh
.venv/bin/python -m backend.adapters.risk \
  --context ../../work/phase8/first-context.json --strategy rules_only
.venv/bin/python -m backend.adapters.risk \
  --context ../../work/phase8/first-context.json --strategy hybrid \
  --bundle ../../work/phase8/seed17 \
  --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903
```

Use `--strategy ml_only` with the same model arguments for ML-only replay. All settings
are visible through `--help`; examples are `--model-weight 0.5`, `--medium 0.35 --high 0.65
--critical 0.85`, and five `--rule-weights` in ADR-015 order. Full policies and fingerprints
accompany outputs. Preserve the original context: present-day recapture can change history.

The first saved Phase 8 context has no prior raw activity: rules-only/hybrid correctly
return INSUFFICIENT_EVIDENCE, null score/action and partial rule evidence. ML-only can emit
an uncalibrated score while disclosing missing evidence. This is not a runtime failure.
Invalid model/policy/artifact inputs instead fail nonzero without a successful report.
All actions are suggestions, production eligibility remains false, and no data is written.
See ADR-015 for formulas, missingness semantics and the future atomic persistence design.

## Phase 10 experimental explanations

Add `--explain` to any Phase 9 replay command. No additional dependency is required.
Native XGBoost supplies exact TreeSHAP attributions in raw model margin/log-odds space.

```sh
.venv/bin/python -m backend.adapters.risk \
  --context ../../work/phase8/first-context.json --strategy hybrid --explain \
  --bundle ../../work/phase8/seed17 \
  --manifest-sha256 52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903
```

The report includes all feature contributions, the base value, margin, uncalibrated model
score, numerical tolerances, five readable contributions and separate rule evidence.
Contributions sum with the base to the model margin, never the hybrid/rule score. Missing
history placeholders are labelled explicitly; model attributions are not causal evidence.
Rules-only with `--explain` returns rule evidence and a null model explanation.

Actual numerical verification of all 2,400 stored seed17 rows and saved-context replay
are retained at ../../work/phase10/treeshap-seed17/{verification.json,replay.json}.
The committed numerical summary is ml/experiments/phase10-explanations/verification.json.
No retraining, predictive evaluation, case creation or profile learning occurred.

## Phase 11 durable experimental evaluation and review

Apply migration `0005_experimental_reviews`, configure the normal database and service
principals, then explicitly opt in for a local research run:

```sh
export FRAUDLENS_EXPERIMENTAL_ENABLED=true
```

Rules-only evaluation needs no model. ML-only or hybrid additionally require the reviewed
native bundle and its independently pinned manifest digest:

```sh
export FRAUDLENS_EXPERIMENTAL_MODEL_BUNDLE=../../work/phase8/seed17
export FRAUDLENS_EXPERIMENTAL_MANIFEST_SHA256=52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903
```

Authenticated routes are:

- `POST /api/v1/experimental/evaluations` with `Idempotency-Key`
- `GET /api/v1/experimental/evaluations/{evaluation_id}`
- `POST /api/v1/experimental/cases` with `Idempotency-Key`
- `GET /api/v1/experimental/cases/{case_id}`
- `POST /api/v1/experimental/cases/{case_id}/review` with `Idempotency-Key`

Service/admin roles may evaluate transactions within their customer scope. Analyst/admin
roles may create and review cases within scope. Evaluation requests select a transaction,
explicit profile version or explicit absence, and `rules_only`, `ml_only` or `hybrid`.
Model strategies must also supply the configured manifest SHA256; rules-only forbids it.

Successful retries return the exact stored JSON with `Idempotency-Replayed: true`, even
after restart. GET never recomputes current history. Evaluation, audit, outbox event and
stored response commit together; case transition, feedback, audit, outbox and response do
the same. All four new business tables reject UPDATE, DELETE and TRUNCATE.

Every result remains uncalibrated, experimental and production-ineligible. Suggested actions
are not executed. Feedback does not admit observations, update profiles, alter immutable
transactions or train models. Do not enable these routes for remote or production use; local
human authentication is available, but deployment authorization and hardening remain open. The local outbox recorder
executes no operational action. See
ADR-017 for the persistence and trust boundary.

## Phase 12 safe experimental profile learning

The same `FRAUDLENS_EXPERIMENTAL_ENABLED=true` opt-in enables these authenticated routes:

- `POST /api/v1/experimental/profile-learning/bootstrap`
- `POST /api/v1/experimental/profile-learning/case`
- `GET /api/v1/experimental/profile-learning/decisions/{decision_id}`

Writes require an admin credential and `Idempotency-Key`. The admin must differ from the
terminal reviewers. Bootstrap takes 5–100 unique closed legitimate case IDs for the same
customer/currency, requires at least two reviewers, and accepts only evaluations captured
with an explicitly absent profile. It creates version 1 only when no profile exists.

Single-case learning requires `expected_profile_version`. A legitimate ordinary transaction
is admitted only if its evaluation captured that exact verified profile version and the
existing gate accepts it. Exceptional amounts, late reviews, stale evaluation versions,
legacy unverified profiles and insufficient history are recorded as QUARANTINE without a
profile change. Confirmed fraud is recorded as REJECT_FROM_PROFILE.

The exact response, immutable learning decision/evidence, audit, outbox and any profile
revision commit atomically. Profile GET responses now expose `admission_workflow_verified`,
`admission_policy_version` and `learning_decision_id`. Upgraded legacy profiles correctly
remain unverified. A case can support only one learning decision.

This is local experimental functionality. The five-observation/two-reviewer bootstrap and
10x median exclusion are authored, uncalibrated policy. Low-weight admission and corrections
are deliberately unavailable because current append-only observations cannot represent
weights or superseding facts honestly. No transaction status, model or operational action
is changed. See ADR-018.

## Phase 13 local outbox worker

Apply migration `0007_outbox_delivery`. With the database URL configured, an authorized
local database operator can inspect state or run one bounded batch:

```sh
.venv/bin/python -m backend.adapters.events status
.venv/bin/python -m backend.adapters.events run --limit 100
```

The command exits after at most 100 claims (limit 1–1000). It is not a daemon, does not
start with FastAPI, and sends nothing externally. The fixed destination is
`local-recording-v1`; a successful handler writes an immutable consumer receipt.
Do not treat `published` as proof of a notification, fraud action or profile change.
This operator CLI uses database access, not an HTTP service credential; restrict the
database role and host before deployment. No new public endpoint exists.

Defaults: 60-second lease, five total claims, 5-second exponential retry delay capped at
one hour. Run again after the delay to retry. Process termination leaves an expiring lease;
after expiry another run can recover it. Keep policy identical across workers. There is
no heartbeat, forced handler timeout, ordering guarantee or exactly-once external effect.
An empty run can reflect live leases, delayed retries, locks or a bounded exhaustion sweep;
inspect status rather than assuming the backlog is drained.

`status` reports pending/published/dead counts, live/expired leases and up to 100 oldest
dead-letter IDs, attempt counts and fixed error categories. Inspect larger backlogs with
read-only SQL against `outbox_delivery` joined to `outbox_events`. Payloads and exception
messages are intentionally omitted. Failed handlers become `handler_failed`; exhausted
crashed claims become `attempts_exhausted`; unreadable envelopes become `unsupported_envelope`.
Unknown schema versions retry without recording a receipt. Terminal records cannot be
reset or deleted through this implementation. Investigate dead letters; audited redrive
and external destinations need separate design. Do not disable history guards to redrive.

Claims commit before handling, and acknowledgement commits separately. A crash after
receipt commit may redeliver the event; the consumer's composite identity deduplicates it.
The migration backfills queue state for older events without inventing receipts for past
publication. Downgrade deletes operational leases/receipt history: use it only in disposable
tests, never as a restart procedure. See ADR-019 for the consumer contract and limitations.

## Phase 14 analyst console

The console requires the backend, PostgreSQL and an expiring analyst/admin credential from
the “Authenticated synthetic API” section above. Keep the backend terminal running, then:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and sign in with a locally provisioned human account.
Vite proxies `/api` to `127.0.0.1:8000`. Browser access/refresh/CSRF values are
HttpOnly cookies; the CSRF value returned by the session endpoint stays in tab memory.
Customer data clears on logout or session expiry. The console is local only.

Authenticated read models:

- `GET /api/v1/console/summary` returns exact scope-filtered counts and UTC event-time semantics.
- `GET /api/v1/console/worklist?limit=50&cursor=...` returns descending keyset pages joined
  to the latest retained experimental evaluation and case state.

Both routes return `Cache-Control: no-store`. An empty scope returns empty data. Null risk
fields mean no evaluation or insufficient evidence. The console labels every result as
experimental, uncalibrated and production-ineligible and never changes RECEIVED transaction
status. Review buttons call the existing versioned/idempotent API after a confirmation dialog.
Profile learning remains an independent admin workflow and is intentionally absent from UI.

For the production frontend bundle and checks:

```sh
cd frontend
npm run lint
npm test
npm run build
npm audit --audit-level=high
```

`docker compose up --build` now serves the console on `127.0.0.1:5173` through nginx and
the API on `127.0.0.1:8000`. Apply Alembic migrations separately as documented above.
Docker execution remains unverified on this machine because its engine is unavailable.
See ADR-020 for metric semantics and ADR-021 for local human session boundaries.

## Phase 15 local human sessions (completed local checkpoint)

Apply migration `0008_human_identity` before enabling login. With the local PostgreSQL
URL exported as `FRAUDLENS_DATABASE_URL`, provision an account from a terminal:

```sh
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.adapters.identity provision \
  --operator-id 00000000-0000-4000-8000-000000000001 \
  --login local-admin --role admin
```

Use a distinct actual local operator UUID for `--operator-id`; it is an asserted audit
identity, not an online identity check. The CLI prompts twice with `getpass` and never
accepts a password argument. An analyst needs one or more `--customer-id UUID` options;
an admin has unrestricted synthetic customer scope and takes no customer IDs. Local
recovery/disable/policy commands use `recover`, `disable`, `enable` or `set-policy` with
`--account-id UUID --operator-id UUID`; recovery requires out-of-band identity checks.

Then start the backend in the same terminal with:

```sh
export FRAUDLENS_HUMAN_AUTH_ENABLED=true
export FRAUDLENS_HUMAN_ORIGIN=http://127.0.0.1:5173
export FRAUDLENS_HUMAN_LOCAL_INSECURE=true
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start `npm run dev` in `frontend/` separately. Local HTTP uses unprefixed non-Secure
cookies. A production environment rejects that mode and requires an explicit HTTPS
origin; this local setup is not approved for remote exposure. Machine intake still
uses separate expiring bearer credentials. Human sessions have five-minute access,
30-minute refresh idle and eight-hour absolute expiry. Concurrent refresh reuse
revokes the family. Business cookie writes require exact Origin and `X-CSRF-Token`.
The browser serializes refreshes in one tab; competing tabs may require login again.

Focused check:

```sh
.venv/bin/pytest tests/unit/test_identity_policy.py tests/integration/test_human_auth.py
```

For a **new dedicated PostgreSQL database/schema**, the four-role grant plan and
role-verification command are documented in
`docs/security/deployment-gates.md` and ADR-023. The integration test creates and
drops its own `*_test` database with real separate logins; it does not alter the
existing public-schema local demo. Production API/worker/operator processes fail
closed if they connect with owner or unexpected credentials. Do not apply those
grants to this existing `fraudlens_test` demo schema.

See `docs/security/threat-model.md` and ADR-021 for remaining remote-deployment
gates: actual TLS/proxy and edge behavior, MFA/recovery assurance and external review.

## Supplemental sequence evidence

New experimental evaluations retain `sequence-v1-experimental` evidence beside risk-v1.
It detects authored 24-hour cumulative low-value, gradual escalation, repeated new-recipient
and total-exposure patterns. It does not change the risk-v1 score or suggested action.
Replay any existing captured context without database access:

```sh
.venv/bin/python -m backend.adapters.sequence /private/tmp/fraudlens-feature-context.json
```

Thresholds are uncalibrated and require a verified profile plus prior raw activity. Older
stored evaluations remain unchanged and contain no sequence field. See ADR-022.
