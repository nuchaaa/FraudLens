# ADR-030: Read-only demo evidence ledger

Status: accepted as a Phase 16 checkpoint, 2026-09-27. The five-story review
and profile-learning demonstrations remain conditional on real authorized inputs.

## Context

The deterministic transaction seed is reproducible, but authored story names
must not be promoted into analyst labels or trusted profile admissions. A presenter
needs to see whether a proposed step was actually evaluated, reviewed and passed
through the separate learning gate without guessing from the transaction worklist.

## Decision

`python -m backend.adapters.demo --progress` requires the same local Unix-socket
`*_test` database and non-production environment as the seed. It uses one
PostgreSQL repeatable-read, read-only transaction. For each fixed fixture ID it
checks persisted transaction facts, reports evaluation IDs and captured profile
versions, case state and feedback, stored learning decisions, and versioned
profile counts/medians/admitted fixture IDs. `ABSENT` and `CONFLICT` are explicit;
the command performs no database writes. The fixture manifest hash accompanies
the report. No status is derived from a scenario's narrative text.

The guide lists evidence required for each story. A prior profile revision whose
`as_of` precedes a candidate is only event-time compatible: it does not prove the
revision was available when the original decision was made. The original
evaluation's captured version is the relevant retained evidence. A recorded
learning decision is distinct from feedback, and a quarantined exceptional
purchase does not become an admitted observation. Medians come from immutable
revision reconstruction, not a mutable live summary alone.

## Consequences

Presenters can replay the seed and inspect progress without generating fake
review outcomes. A complete B/C or D claim remains unavailable until independent
local reviewers supply genuine case evidence and an admin separately authorizes
learning. The ledger does not certify real-world legitimacy, reviewer identity
outside the local auth boundary, historical arrival time or predictive quality.
The source event timestamps were all imported at demo time. This checkpoint
does not clear Phase 15 remote security or production behavioral-validation gates.
