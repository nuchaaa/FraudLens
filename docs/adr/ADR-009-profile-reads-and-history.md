# ADR-009: version-pinned behavior reads and conservative cold start

Status: accepted for Phase 4, 2026-09-20.

## Context

Median/MAD/p95 and short/long windows already exist. The missing application behavior
is authenticated retrieval with explicit insufficient-history states, currency isolation
and reproducible history cutoffs. The mutable profile head alone cannot reproduce old
timezone/window policies. Filtering transactions by event time alone would also include
backdated observations admitted after a historical prediction.

## Decision

Expose read-only `GET /api/v1/customers/{customer_id}/profiles/{currency}` using the
existing principal/customer scope rules. Unknown or inaccessible customers both return
404. No GET writes profile, audit, snapshot or outbox records. No profile admission or
bootstrap HTTP endpoint is introduced. Existing customer enrollment remains identity
creation only; transaction submission remains unverified intake.

Current reads select the latest committed profile revision and the server's current
UTC cutoff. Every response identifies its selected `version`, `revision_as_of`, `as_of`
and descriptive `read_policy_version`. An explicit `as_of` requires an explicit positive
`version`. Future cutoffs are invalid (422). A cutoff older than a revision's `as_of`
cannot safely use its trimmed history and returns 409; select an earlier captured
revision instead. Unavailable revisions return 404, never a fabricated baseline.

Reproduce a response with its exact `version` and `as_of`. For inference or research
replay, the caller must use a version captured **before that original decision**.
An arbitrary version number or wall-clock event timestamp is not evidence of what was
known historically. This API deliberately does not invent a `knowledge_at` reconstruction
from row timestamps or claim to know commit times. A version selected today must not be
used to backfill historical training features as though it were available then.

Observations must belong to the selected customer/currency and have `admitted_version`
at most the pinned version. Event timestamps satisfy `(as_of - window, as_of)` for reads:
both the lower boundary and the candidate instant are excluded. All simultaneous events
at the candidate instant are excluded conservatively. The existing inclusive domain
window helper remains unchanged; the application removes candidate-instant observations
before computing statistics. Reads later than a revision roll its window forward without
persisting a new version. Revisions ahead of the requested cutoff are rejected explicitly.

## Immutable revision storage

Migration `0004_profile_revisions` adds the fifteenth business table. PostgreSQL captures
profile identity, version, event-time head, timezone and window configuration whenever
the head is inserted/updated. The revision and observations participate in the same
existing explicit-commit UoW. UPDATE, DELETE and TRUNCATE of revisions are rejected.

A deferred admission constraint requires each new observation to reference a revision
created by the same database transaction and to have an event time no later than its
revision head. The internal full transaction ID is an integrity marker, not an identity,
wall-clock timestamp or proof of legitimacy. The row's physical xmin must also match
the current transaction, so restored rows cannot reuse a stored transaction ID. Writes
use the existing top-level UoW, without nested database savepoints. This prevents a later transaction appending
observations under a previously committed version. Readers can capture revision metadata
then hydrate observations without a concurrent writer changing that revision's set.
Existing row locks/version checks still serialize competing writers.

The migration backfills only each existing head. Earlier metadata was not retained;
older revisions cannot be reconstructed honestly. Existing observations/transactions
are preserved. A downgrade removes the new journal/guards, not prior business records;
re-upgrade can again recover only current heads. Do not downgrade a real replay archive.
Database owners can disable triggers; least-privilege runtime grants remain security work.

## Cold start and descriptive statistics

| State | Meaning |
|---|---|
| UNINITIALIZED | Customer exists but no profile exists for this currency; version is null |
| EMPTY | A revision exists but no observations remain within the read window |
| INSUFFICIENT_HISTORY | 1–4 admitted observations in the long window |
| SUFFICIENT_HISTORY | At least 5 admitted observations in the long window |

The five-observation threshold is an **uncalibrated** descriptive policy consistent
with the initial gate hypothesis. It does not establish a valid fraud model or permission
to learn. Empty amount statistics are null, not invented zero medians. Cold/insufficient
history must remain explicit in future features; never manufacture ratios or silently
learn from raw intake to overcome it.

Both windows report existing Decimal amount statistics, admitted observation count,
known recipients, and counts in all 24 customer-local hours. `observations_per_day` is
count divided by the full configured window length (180/30 by default), not raw intake
velocity, a measured exposure rate or a fraud score. Decimal statistics remain strings
over HTTP without rounding away fractional medians/MADs.

Descriptive typical hours require at least two observations and at least 10% of that
window's observations. These uncalibrated defaults are named `profile-read-v1`; counts
are also exposed so consumers need not treat the summary as a learned probability.
Timezone conversion uses the pinned IANA zone, including DST. Category/device behavior,
recipient age and event-time intake velocity require separate data/contracts in Phase 5.

## Trust boundary and future enrollment policy

Current observations assert repository admission; they do not contain complete analyst
or bootstrap evidence. Responses disclose `history_source=repository_admissions` and
`admission_workflow_verified=false`. Admin/service credentials do not turn a received
transaction into a legitimate training example. No new trust claim is introduced by
archiving revisions, and this phase adds no profile mutation API.

Before a trusted bootstrap is implemented, require a reviewed synthetic-history manifest,
independent legitimacy/source evidence, immutable transaction references, curator identity,
recorded review time, policy version and an atomic audit/event trail. Do not use model
predictions as truth. Later ordinary updates need authorized feedback provenance and the
safe gate; exceptional legitimate purchases remain quarantined and fraud is excluded.
Bootstrap, compromised confirmations, low-weight admission, corrections/retractions and
gate orchestration remain Phase 11/12 work. The revision journal is not a replacement
for that evidence or a retroactive correction mechanism.

## Validation and alternatives

PostgreSQL tests cover migration preservation, revision immutability, admission sealing,
rollback, concurrent readers/writers, pinned policy, backdated admissions, currency
isolation, strict boundaries and quarantine baseline preservation. API tests cover
authorization, missing histories and exact Decimal output. Domain tests cover cold states,
frequency qualification and repeated DST hours.

Rejected: recomputing from all received transactions (poisoning), filtering only event
timestamps (future knowledge leakage), silently using current policy for old versions,
inventing historical revision timestamps, or duplicating entire observation histories
in every revision. Existing assessment snapshots remain a separate immutable artifact.

References: [PostgreSQL transaction IDs](https://www.postgresql.org/docs/17/functions-info.html),
[deferred constraint triggers](https://www.postgresql.org/docs/17/sql-createtrigger.html),
[ADR-007](ADR-007-persistence-consistency.md), [ADR-008](ADR-008-transaction-api-and-service-credentials.md).
