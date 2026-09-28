# ADR-029: Disposable synthetic demo transaction seed

Status: accepted as the first Phase 16 checkpoint, 2026-09-27. This creates
transaction *facts* only; it is not a completed behavioral-profile demonstration.

## Context

The console has no reproducible data for the five stories in the project
specification. Hand-entering IDs and timestamps makes live demonstrations hard to
repeat. Importing authored "legitimate" or "fraud" labels as analyst feedback or
trusted profile history would misrepresent evidence and bypass Phase 12 review.

## Decision

`demo-scenarios-v1` fixes one UTC anchor, four synthetic customers, stable UUIDv5
identifiers and 62 KZT transaction facts. The five authored stories are: a
normal-looking transfer (A); an 8M vehicle payment (B); a 500k new-recipient
transfer after that payment for the same customer (C); five days of gradually
larger transfers (D); and a six-transfer 50k–500k escalation (E). Twelve prior
normal-looking transfers per customer make the chronology visible. B and C share
one baseline, marked `BC` in the manifest. Stories are **narrative intent**, not
verified labels or measured detector outcomes.

The manifest and its SHA-256 are deterministic. The local CLI previews it without
a database. `--apply` requires an explicit `TEST_DATABASE_URL` pointing to a
Unix-socket PostgreSQL database named `*_test` and refuses production mode. It
calls existing customer-enrollment and transaction-submission use cases, retaining
their audit, outbox, scoped idempotency and uniqueness behavior. A deterministic
synthetic admin actor UUID is shown in the manifest; it represents the local
fixture, not an authenticated human. Reapplying the same plan replays transaction
responses and does not duplicate audit or outbox rows. Customer creation/audit
timestamps are actual execution times, so only the planned customer IDs and
transaction facts, not the entire database byte stream, are deterministic.
All event-time facts are inserted during the demo run. Their past timestamps do
not reconstruct when a bank would have known them; captures made after seeding
must not be presented as historical point-in-time evaluations.

The loader never creates profiles, admissions, evaluations, cases, feedback or
fraud verdicts. In particular, the B/C story cannot yet show preservation of an
admitted baseline, and D cannot yet prove safe adaptation. A later checkpoint
must exercise authorized review and profile-learning workflows with explicit
independent actors before showing those outcomes. No score or alert is claimed
for the present fixture.

## Verification and limits

PostgreSQL integration checks first application, exact replay, audit/outbox
counts and absence of profile/evaluation rows for the fixture IDs. Safety tests
reject TCP, non-`*_test` databases and production mode. The CLI was dry-run only
against the working directory; integration tests applied the plan inside a
disposable migrated test schema. The seed must never be pointed at real banking
data or used as evidence of predictive performance.
