# Behavioral data-owner evidence request v1

**BLANK REQUEST TEMPLATE — NOT SENT. It requests evidence for review; it is not
permission to provide, receive, or process records.**

Prospective source: `UNSET`  
Data owner/controller: `UNSET`  
Authorized contact and authority reference: `UNSET`  
Proposed research purpose: `UNSET`  
Request status: `TEMPLATE_ONLY`

Do not attach row-level data, direct identifiers, credentials, keys, or personal
information to an email, chat, issue, or repository. Do not transfer any private
data until the owner has confirmed authority and the designated reviewers have
approved the applicable permission, privacy, security, and custody gates in
writing. A public dataset license alone is not permission to process private
records. This template has not been sent and authorizes no outreach.

## Requested owner-supplied evidence

For each item, the owner should provide a restricted evidence reference, issuing
authority, scope, effective period, verification method, and any limitation. Mark
missing or unknown facts `UNSET`; do not infer them. The assigned reviewer must
record `UNSET` until the artifact has been independently checked.

| ID | Required artifact or attestation | Supplied reference | Responsible verifier |
| --- | --- | --- | --- |
| G0-1 | Written data-use authority naming owner/controller, permitted purpose, lawful basis or consent authority, fields, accessors, processing location, onward-transfer and publication limits, effective dates, retention/deletion obligations, and incident procedure | `UNSET` | Independent legal/privacy reviewer |
| G0-2 | Evidence that the signatory can grant the stated rights; applicable institutional approval and any required consent/waiver evidence | `UNSET` | Independent legal/privacy reviewer |
| G0-3 | Privacy impact, minimization, sensitive-data assessment, permitted publication level, and approved incident/escalation path | `UNSET` | Independent privacy reviewer |
| G0-4 | Pseudonymization plan executed by the owner; stable pseudonym generation, key custody separated from exported data, access log, encryption, approved location and named least-privilege users | `UNSET` | Independent security/privacy reviewer |
| G0-5 | Retention schedule, deletion mechanism and deletion evidence owner; explicit prohibition or scope for onward sharing and public release | `UNSET` | Data steward and independent privacy reviewer |
| G1-1 | Exact source/version identifier, byte-level source hash, extraction query/code/version, export time, extraction actor/process and chain-of-custody record | `UNSET` | Data steward; independently checked by chronology reviewer |
| G1-2 | Field dictionary, types, units, currency semantics, timezone, clock precision, null/absence meanings, identifier rotation/merge/reassignment rules | `UNSET` | Data steward and independent chronology reviewer |
| G1-3 | Stable transaction and pseudonymous customer identity lineage; recipient/device identities where supported; mapping ownership, continuity, rotation, merge and ambiguity handling | `UNSET` | Independent identity/chronology reviewer |
| G1-4 | Separate event, first durable arrival/ingestion, original decision, feedback creation and availability, revocation/correction availability, and admission decision/availability clocks; source-system meaning and reconstruction/rounding history for each | `UNSET` | Independent chronology reviewer |
| G1-5 | Outcome and label policy: definition, evidence source, adjudicator/process independence, label creation and availability clocks, maturation rule, censoring, correction/revocation lineage, and documented meaning of absent labels | `UNSET` | Independent label reviewer |
| G1-6 | Trusted-profile admission ledger: decision/actor authority, evidence basis, policy version, transaction linkage, creation and availability times, supersession/revocation links, and snapshot/profile version available to each original decision | `UNSET` | Independent chronology/label reviewer |
| G2-1 | Row-level validation and rejection plan, stable source row IDs, duplicate-delivery lineage, immutable original context hashes, corrected-view linkage and no-silent-repair procedure | `UNSET` | Independent chronology reviewer |
| G2-2 | Feasibility evidence for chronological and whole-customer-disjoint partitions without identity leakage; owner-controlled pseudonym split procedure and deterministic cohort assignment | `UNSET` | Independent methodology reviewer |
| G2-3 | Proposed observation and decision intervals, label freeze and maturation cutoffs, each supported by source coverage and independently checked before outcomes are examined | `UNSET` | Independent chronology and methodology reviewers |
| G2-4 | Proposed eligible estimand, candidate feature/policy/model versions, minimum support and uncertainty method; explain which claims the source cannot support | `UNSET` | Independent methodology reviewer |
| G2-5 | Review-capacity ceiling and safety constraints, supplied by the accountable operational owner and approved before validation selection | `UNSET` | Operational owner and independent methodology reviewer |
| G3-1 | Untouched final-test custody: named custodian, access restrictions, hash/seal procedure, one-invocation logging, and process preventing selection or tuning on test outcomes | `UNSET` | Independent test custodian and methodology reviewer |
| G3-2 | Reproducible analysis package plan: code commit, dependency lock, seeds, source/extraction/addendum hashes, training/validation trace, artifact hashes, denominators and deletion proof | `UNSET` | Independent methodology reviewer and data steward |
| G3-3 | Stop/withdrawal path for permission withdrawal, privacy/security incident, leakage, clock or identity failure, insufficient maturation/support, or compromised test access | `UNSET` | Data owner, privacy reviewer and methodology reviewer |

## Reviewer roles and evidence boundaries

- **Data owner/controller:** establishes authority and source/extraction facts;
  does not independently approve the project's analysis.
- **Data steward:** attests lineage, extraction and custody, with restricted
  evidence references.
- **Independent legal/privacy reviewer:** verifies use authority, privacy scope,
  transfer, retention and publication controls.
- **Independent chronology/identity reviewer:** verifies clock semantics,
  identity continuity, admission provenance and point-in-time feasibility.
- **Independent label reviewer:** verifies outcome adjudication independence,
  maturity and correction/revocation lineage.
- **Independent methodology reviewer:** verifies estimand, partitions, support,
  review burden, analysis freeze and final-test isolation.
- **Independent final-test custodian:** controls access and records any final
  test invocation.

One person may not self-certify an independent gate they authored or control.
Potential conflicts and reviewer independence must be disclosed in the
disposition form. A missing role or unresolved conflict blocks the gate.

## Stop conditions before any row transfer

Stop before receiving or opening rows if owner authority, legal/privacy approval,
approved purpose and location, minimization, security/custody, retention, or
transfer authorization is missing or contradicted. Stop before analysis if
stable identity, required clocks, trustworthy admission lineage, label
availability, split feasibility, independent review, review-capacity limit, or
untouched-test controls cannot be verified. Do not train or inspect outcome
labels to decide whether a source is suitable. Record the missing evidence in an
unsigned disposition; do not convert absence into a favorable assumption.

No data-owner contact has been made through this packet.
