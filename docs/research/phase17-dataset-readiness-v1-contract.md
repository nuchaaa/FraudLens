# Phase 17 behavioral dataset readiness v1 — predeclared contract

Status: specified before running the auditor on any fixture. This is a
**read-only manifest assessment**, not a raw-data validator, permission grant,
training gate or production approval. It never reads transaction rows, sends
network requests or changes a source. A complete manifest means only that
row-level and independent evidence review may begin.

## Input and provenance

`behavioral-readiness-manifest-v1` JSON has five sections:

- `dataset`: nonempty `id`, `version`, `source_uri`, `source_sha256` (64 lowercase
  hex characters), and `source_type` (`synthetic`, `public` or `restricted`).
  A manifest's source hash is a claim until source bytes are independently
  verified; the auditor does not open the source.
- `governance`: `license`, `research_permission`, `privacy_handling`, and
  `retention_plan`. Each is `{state, evidence}` with state `DOCUMENTED`,
  `ABSENT` or `UNKNOWN`. `DOCUMENTED` requires a nonempty evidence reference.
  Evidence references are strings, not authenticated approvals; no external
  page or private record is fetched.
- `capabilities`: each required capability below is `{state, field, evidence}`.
  `DOCUMENTED` requires a nonempty source field and evidence reference.
  `ABSENT` asserts no source field; `UNKNOWN` means it was not established.
  Both block behavioral validation. Missing keys are `UNKNOWN`, never pass.
- `time_resolution_seconds`: a positive integer at most 60 for the minute-level
  behavior-v1 questions. Larger, missing or uncertain precision blocks this
  contract; coarse source time must not be expanded into invented velocity.
- `split_plan`: `{state, train_end_utc, validation_end_utc, test_end_utc,
  held_out_customer_count, customer_disjoint, evidence}`. For DOCUMENTED,
  boundaries must be absolute UTC ISO-8601 timestamps with strict ordering;
  the held-out count must be positive and `customer_disjoint` true. This
  checks a *declared plan*, not actual row membership or class support.

Required capabilities: `stable_customer_id`, `stable_recipient_id`,
`currency`, `amount`, `stable_device_id`, `absolute_event_at`, `arrival_at`,
`decision_at`, `label_value`, `label_available_at`, `feedback_provenance`,
`revocation_available_at`, `trusted_admission_provenance`, and
`admission_available_at`. If revocations did not occur, a source still needs
a documented mechanism to distinguish **verified none** from unknown;
an invented all-null column is not evidence. Source identities can be
pseudonymous, but continuity and scope must be documented. Admission
provenance must identify which histories were independently trusted *before*
each candidate; a final retrospective label cannot serve as that proof.

## Deterministic decisions

The auditor emits one ordered check per requirement, each with `PASS`, `FAIL`
or `UNKNOWN`, a stable code, and the evidence reference if provided. Explicit
`ABSENT` becomes FAIL; `UNKNOWN` or missing becomes UNKNOWN. Invalid hash,
unsupported version, contradictory DOCUMENTED item, coarse precision, or
invalid split plan becomes FAIL. Every failure/unknown yields overall `BLOCKED`
with machine-readable `failures` and `unknowns`. If all checks pass, overall
status is `READY_FOR_ROW_AUDIT`, still with
`behavioral_validation_eligible=false` and `production_eligible=false`.
The auditor cannot authenticate license scope, source bytes, privacy controls,
field semantics, exact event/arrival order, label availability per row,
consent or held-out-customer feasibility. Those require separate review.

## Frozen small cases

Create four versioned, fictional manifests before interpretation:

1. `synthetic-complete`: all declarations present, ordered UTC split plan;
   expected `READY_FOR_ROW_AUDIT`, never model-ready.
2. `synthetic-missing-chronology`: identical source but arrival/decision fields
   explicitly absent; expected BLOCKED with named capability failures.
3. `synthetic-unknown-label-time`: label availability UNKNOWN; expected BLOCKED
   with a named unknown and no inferred feedback time.
4. `ulb-known`: transcribe only the already committed ULB v3 metadata/hash,
   Time/Amount/Class schema and explicit gaps from the frozen ULB protocol.
   License evidence is documented, but absent identities/currency and unknown
   arrival/label availability must block behavior-v1. This is not a repeat
   model evaluation or an audit of raw ULB rows.

Commit manifest and report hashes. Test deterministic byte replay, malformed
or duplicate JSON key rejection, missing/absent/unknown distinction, evidence
requirements, split ordering, source hash syntax, ULB provenance consistency,
and no source-file modification. Do not use these cases for risk-v2 threshold
selection or predictive claims.
