# ADR-032: Staged disposable demo intake

Status: accepted as a Phase 16 engineering checkpoint, 2026-09-27. Actual
behavioral outcomes still require independent authorized local reviews.

## Context

Bulk insertion of all 62 authored facts is useful for a quick worklist, but it
places later transfers in the database before a presenter captures an earlier
decision. Strict event-time feature cutoffs exclude those later timestamps, yet
bulk insertion does not reproduce original knowledge or arrival chronology. A
guided demonstration needs pauses for a real review and profile-learning gate
without the fixture scripting analyst verdicts.

## Decision

The existing `demo-scenarios-v1` manifest and SHA-256 remain unchanged. A pure
stage partition has `BASELINE` (48 earlier raw transfers), A, B, C, five D
steps and six E steps. `--apply-stage STAGE` requires the same local Unix-socket
`*_test` database and non-production environment as bulk `--apply`. Both paths
serialize fixture writes with a PostgreSQL advisory transaction lock and use
the original manifest-based idempotency keys and existing customer/transaction
services. A retry replays exact facts; a partial baseline stage can be retried.

For a *new* candidate insertion, matching same-customer baseline facts must
already exist and later same-customer fixture facts must not. Baseline backfill
is refused after a profile or candidate. A may remain cold. B, C, D and E need
a verified earlier KZT profile whose first immutable revision came from an
accepted BOOTSTRAP with at least five of that customer's admitted fixture
baseline transactions and two distinct recorded reviewers. A verified profile
built from unrelated transactions is insufficient for this staged story. The
trace check reads the stored workflow; it does not independently authenticate
the historical reviewer or establish external legitimacy. C also needs a
retained B evaluation and a separate exceptional-amount QUARANTINE case-learning
decision that did not advance the profile. Each D step after
D1 needs a retained previous evaluation and a separately authorized ACCEPT
admission. Each E step after E1
needs a retained previous evaluation. Stored facts are read in a PostgreSQL
repeatable-read, read-only transaction before each stage write. The guard checks
the persisted profile/learning records; it does not infer legitimacy from story
text. An exact existing stage can be replayed but replay is not evidence that
the original insertion followed these gates.

`--check-stage STAGE` exposes the same read-only guard as a preflight report:
`READY`, `BLOCKED` with a prerequisite reason, `CONFLICT` for mismatched facts,
or `REPLAYABLE` for an exact existing stage. It uses the same disposable-database
guard. A preview is not a lock or authorization; the apply path rechecks under
its advisory lock before writes. PostgreSQL tests cover preview transitions and
conflicting fixture IDs without inventing reviewer evidence.

Bulk `--apply` remains an explicitly facts-only shortcut and does not enforce
these presentation gates. Neither mode creates evaluations, cases, reviews,
profile admissions, predictions or measured outcomes. The fixture actor is a
synthetic admin used only by audited/idempotent enrollment and intake.

## Consequences

An isolated migrated PostgreSQL schema tested stage partition, first insert,
exact replay, and refusal of B/C/D/E without a verified profile; it created no
reviews or profiles. Positive review-dependent paths cannot be demonstrated
without actual independently authenticated reviewers. A stage lock serializes
the local fixture CLI, not arbitrary direct API writers, and staged local
insertion still does not reconstruct real bank arrival or label-availability
times. Phase 15 remote security and production behavioral validation remain open.
