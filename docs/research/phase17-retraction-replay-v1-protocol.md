# Phase 17 retraction/replay v1 — predeclared offline protocol

Status: frozen **before** executing or interpreting this fixture's report.
This is a new `profile-retraction-stream-v1` source, separate from both frozen
Phase 17 comparisons and every Phase 16 detector case. It has no database,
production gate integration, authenticated analyst, risk score or model.
The frozen canonical source SHA-256 is
`a47cf3b27e4556da4fa71554f6057570a7135c7ad56be71b01219ee1064a74dc`.

## Source and clocks

Use fixed UTC anchor 2026-11-01 09:00 and stable UUIDv5 identifiers. Two
synthetic customers each start with five distinct, assumed approved KZT
observations dated before the anchor. The assumption is not analyst evidence.

For customer `late`, event L1 occurs at anchor +1 hour but arrives at +4 hours;
its simulated LEGITIMATE feedback becomes available at +4 hours 10 minutes.
Event L2 occurs at +2 hours, arrives at +2 hours 1 minute and receives
simulated LEGITIMATE feedback at +2 hours 10 minutes. Process L2 at +2 hours
20 minutes, then L1 at +4 hours 20 minutes. Request a corrected view at +5
hours. This is a late **arrival**, not a changed original event timestamp.

For customer `revoked`, event R1 occurs at +1 hour, arrives at +1 hour 1
minute, receives simulated LEGITIMATE feedback at +1 hour 10 minutes and is
processed at +1 hour 20 minutes. A separate retraction fact becomes available
at +3 hours; request a corrected view at +3 hours 10 minutes. Retraction
means the confirmation is no longer trusted; it does **not** assert fraud.

Each event records event time, arrival time, feedback availability and optional
revocation availability. Every process step records its own processing time.
Correction requests pin a knowledge cutoff no later than processing time.
Only facts with arrival and feedback strictly **before** the cutoff may enter
a corrected view. A revocation strictly before the cutoff removes that
confirmation. Equality remains unavailable at the cutoff. These clocks are
authored simulation data, not reconstructed database commit times.

## Projection and preservation rules

Run original APPLY steps in processing order through the unchanged pure
`ProfileUpdateGate`. Retain each original outcome and full admitted-ID snapshot.
The current gate must reject historical L1 after L2; record that as
`REQUIRES_HISTORICAL_REPLAY`, not as a made-up gate decision. R1 can be
accepted at its original processing time because its later revocation was
unknown then. Do not mutate either original record.

An explicit CORRECT step constructs a **new** versioned view from the fixed
baseline and all customer-scoped, eligible facts known at its pinned cutoff.
Sort candidate events by `(event_at, transaction_id)` and apply the unchanged
gate. The corrected view references the previous view it supersedes, the
source hash, cutoff, included/excluded event IDs and reason codes. It is an
offline projection, not a retroactive claim about what an earlier decision
could know. No corrected view is written to a live profile.

Correction request IDs are scoped to an exact customer and cutoff. A duplicate
with the same body returns the same view ID and appends a replay-attempt record
without creating another view; changing the body under the same ID fails.
All source rows and view records remain append-only in the report. Customer
isolation, strict chronology, source hash, deterministic byte replay,
correction ordering and original-view preservation are test requirements.

Predeclared expected mechanisms: L2 is originally admitted; L1's original
apply cannot advance the profile; a later corrected view can replay L1 then
L2. R1 is originally admitted; after retraction its corrected view excludes
R1 without calling it confirmed fraud. The retained original R1 view still
shows what was believed at its earlier processing time. Duplicate corrections
must not create another view.

## Boundaries

The fixture cannot establish whether a real confirmation is compromised,
whether an unobserved event exists, when real evidence became available,
whether a correction is authorized, or whether bank actions can be undone.
It does not repair the production persistence/UoW workflow. There is no
fraud-performance metric, risk-v2 threshold selection or model promotion.
