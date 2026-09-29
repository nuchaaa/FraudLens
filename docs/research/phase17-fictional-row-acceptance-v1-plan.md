# Phase 17 fictional row acceptance v1 — predeclared cases

Status: specified before generating the fixture report. This is a small
read-only *software acceptance* harness for the frozen [prospective protocol](phase17-prospective-behavioral-validation-v1.md),
not a new data acquisition, legal approval, independent source-row audit,
model experiment or production readiness test. Only obvious fictional IDs and
oracle-assumed feedback are allowed. The input and output are local JSON;
neither is loaded into PostgreSQL. All results retain
`behavioral_validation_eligible=false` and `production_eligible=false`.

## Input and audit semantics

`fictional-row-source-v1` contains bounded transaction, feedback, admission,
revocation and customer-identity-alias arrays, a UTC decision-time split plan,
and requested original/corrected context views. The source declares
`synthetic_only=true` and `time_resolution_seconds` between 1 and 60. A fixed
protocol SHA-256 binds the harness to the prospective protocol. Every
transaction needs an ID, customer/recipient/device IDs, finite positive Decimal
amount as a string, currency, and absolute UTC event/arrival/decision instants.
The local fixture asserts aliases and simulated review records; their truth and
authority are **not** independently verified. No inferred merchant/location,
identity mapping, label or admission is permitted.

Duplicate transaction IDs block all colliding rows, including identical
deliveries; this fixture has no authenticated delivery key or deduplication
lineage. Conflicting bodies receive a distinct code. Invalid/missing clocks,
`event > decision`, `arrival > decision`, coarse declared precision, and
ambiguous alias cohorts block the affected row or source as specified below.
No row is repaired or silently dropped. A row's split is derived from its
decision instant, not a caller-supplied partition. A held-out canonical
customer appearing in train/validation, or conflicting cohort declarations
for aliases of one canonical customer, blocks that identity. Missing alias
lineage is UNKNOWN/BLOCKED.

For a valid candidate at event `e` and decision `d`, original raw history is
same canonical customer and currency, `event < e`, `arrival < d`, and neither
candidate nor lower-window-boundary event. The 180-day lower boundary is
strict. Trusted history additionally needs a linked simulated LEGITIMATE
feedback available before `d`, an admission available before `d` and after
that feedback, and no revocation available before `d`. An unexplained or
missing review link yields UNKNOWN, never admission. Corrected view uses a
separately declared later knowledge cutoff but keeps candidate event and
historical decision unchanged. It has a distinct ID and original-view link;
it is **not** a reissued original decision or a measure of historical truth.

## Frozen fictional cases and expected outputs

All named instants below are UTC. `C` has event/decision on January 5. The
fixture's `H*` rows are older for one development customer/currency; none are
verified real transactions or analyst verdicts.

| Case | Predeclared acceptance |
| --- | --- |
| `H1` early available feedback/admission | Included in C's original raw and trusted IDs. |
| `H2` event before C, arrival after C | Excluded from original raw/trusted with `LATE_ARRIVAL`; may enter the later corrected view if its linked simulated admission has then become available. |
| `H3` raw row before C, feedback/admission after C | In original raw but not original trusted, with `FEEDBACK_NOT_YET_AVAILABLE`; corrected trusted may include it. |
| `H4` admitted before C, revoked after C | In original raw/trusted. A corrected view after revocation excludes it from trusted with `REVOKED_BY_CUTOFF`, without changing original C. |
| `C` candidate | Excluded from both its own raw/trusted histories with `CANDIDATE_SELF`. Original and corrected context IDs differ and retain a link. |
| A transaction at C's event instant or at its 180-day lower boundary | Excluded with `EVENT_NOT_STRICTLY_PRIOR` or `LOWER_BOUNDARY_EXCLUDED`, respectively. |
| Duplicate ID with changed facts | Every colliding row blocked with `CONFLICTING_TRANSACTION_ID`; no last-write-wins. Identical duplicate is also blocked until authenticated delivery lineage exists. |
| Naive timestamp, coarse source precision, arrival after decision | `TIMESTAMP_NOT_UTC`, source `COARSE_TIME_RESOLUTION`, or `ARRIVAL_AFTER_DECISION`; never synthesize a time. |
| Two aliases of one canonical customer assigned different cohorts | `IDENTITY_COHORT_CONFLICT`; a held-out row in train/validation also gets `HELDOUT_IN_FIT_PERIOD`. Unknown identity mapping is `IDENTITY_LINEAGE_UNKNOWN`. |
| Missing admission/feedback provenance | `ADMISSION_PROVENANCE_UNKNOWN`; excluded from trusted context, no assumed legitimacy. |

Tests must establish byte-for-byte deterministic replay, source-file
immutability, exact reason codes and original-view preservation under a new
corrected cutoff. CLI output is create-only and rejects malformed/duplicate-key
or nonfinite JSON, oversized input and `synthetic_only` other than true. The
report is descriptive context acceptance only: no labels, confusion matrix,
fraud score, profile update, model training or threshold selection.
