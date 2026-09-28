# ADR-033: Fictional demo review evidence

Status: accepted as a Phase 16 local-demonstration checkpoint, 2026-09-28.
Independent analyst reviews and behavioral outcomes remain unrecorded.

## Context

The deterministic transaction fixture intentionally contains only bank-like
transaction facts. Reviewers correctly found that UUIDs, amounts and timestamps
do not identify a payer, payee, merchant, purpose or place. Inferring legitimacy
from a small amount would make the safe-profile demonstration misleading. Public
business registries also cannot identify the recipient of a fictional transfer.

Phase 16 needs reviewable role-play context without claiming that authored data
is real evidence, automatically choosing an analyst verdict, or modifying the
immutable transaction contract.

## Decision

`demo-review-evidence-v1` is a separate deterministic companion package for all
62 `demo-scenarios-v1` transaction IDs. It contains obviously fictional display
names, purposes, locations, references and short artifact summaries. Names use
`Demo`, `fictional` and `unregistered` labels; no real person, company, address or
registry identity is asserted. The package SHA-256 is
`436c1c24119a12a7df63bf9f6ea4888a19c021b1eec94d4df945e83983687185`.

Baseline, A, B and D examples have `SUPPORTED` authored role-play context. C and
E deliberately have `UNAVAILABLE` supporting artifacts and unverified fictional
counterparties. Support describes the packet, not the transaction's legitimacy.
Every entry states `synthetic_only=true`, `real_world_verified=false`,
`production_eligible=false` and `verdict_provided=false`.

The package is printable offline with `backend.adapters.demo --evidence-package`.
An authenticated, scope-checked, no-store endpoint exposes a single entry only
when experimental mode is enabled. The local console renders it in a warning
panel. The endpoint performs no database write and is not a source for feature
extraction, risk scoring, case state or profile learning.

## Consequences

Reviewers can see enough fictional context to perform an independent role-play
review, while missing support remains visible for C/E. Their actual decisions
must still be entered through their own authenticated sessions. A stored verdict
does not itself authorize learning; the separate bootstrap/update workflow and
existing provenance gates remain mandatory.

This artifact cannot demonstrate real-world detection performance, identity
verification, historical evidence availability or analyst independence. Phase 16
cannot close until the required reviews and learning decisions are actually
recorded and the five-story outcomes are verified without scripted verdicts.
