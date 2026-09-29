# Independent source disposition v1

> **UNSIGNED TEMPLATE — NOT AN APPROVAL.** This file is not signed, has no
> source-specific evidence attached, and cannot authorize contact, data transfer,
> row access, analysis, training, threshold selection, or publication.

Disposition ID: `UNSET`  
Source ID / owner: `UNSET`  
Addendum version and exact SHA-256: `UNSET`  
Evidence packet version and restricted location: `UNSET`  
Disposition status: `TEMPLATE_ONLY`  
Date/time (UTC): `UNSET`

Allowed status values after review: `UNSET`, `BLOCKED`, `APPROVED_FOR_NEXT_GATE`,
`REJECTED`, `WITHDRAWN`. `APPROVED_FOR_NEXT_GATE` must name exactly one next
gate and does not approve later gates. It never substitutes for the owner's
permission instrument. A blank or partially signed form is `UNSET`/`BLOCKED`,
never approval.

## Evidence inventory

List exact artifact ID/version/hash, restricted location, issuer, scope and
verification performed. Do not copy private records or secret identity mappings
into this form or the repository.

| Artifact | Version/hash | Issuer/authority | Scope checked | Independent verification result |
| --- | --- | --- | --- | --- |
| Written use authority and consent/legal basis | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Privacy/security/custody/retention controls | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Source hash, extraction and chain of custody | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Field dictionary, units and identity continuity | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Event/arrival/decision/feedback/revocation/admission lineage | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Outcome adjudication and label maturation | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Split feasibility, support and review-capacity evidence | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Untouched-test custody and stop/withdrawal procedure | `UNSET` | `UNSET` | `UNSET` | `UNSET` |

## Gate-by-gate disposition

For every gate, state evidence, decision, limitations and the only next action
permitted. Missing, contradictory, unverifiable or withdrawn evidence means
`BLOCKED` or `REJECTED`.

| Gate | Reviewer role | Evidence refs and verification | Decision | Limitations / stop criteria | Next gate explicitly permitted |
| --- | --- | --- | --- | --- | --- |
| G0 — authority, privacy, custody and transfer scope | Independent legal/privacy reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G1 — source, extraction, identity and clock semantics | Independent chronology/identity reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G1 — outcome, feedback, revocation and admission lineage | Independent label/admission reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G2 — row acceptance and point-in-time reconstruction | Independent chronology reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G2 — chronological/customer-disjoint splits and support | Independent methodology reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G2 — review-capacity budget and operational constraints | Accountable operational owner plus independent methodology reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| G3 — analysis freeze and untouched final-test custody | Independent methodology reviewer and separate test custodian | `UNSET` | `UNSET` | `UNSET` | `UNSET` |

## Required independent attestations

Each reviewer must be named and their authority, independence and conflict
disclosure checked. Record a cryptographic signature or institutional approval
reference over this form's exact hash; typed names alone are not signatures.

| Role | Person / authority evidence | Independence and conflict check | Decision | UTC timestamp | Signature over exact form hash |
| --- | --- | --- | --- | --- | --- |
| Data owner/controller authorized signatory | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Data steward | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Independent legal/privacy reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Independent chronology/identity reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Independent label/admission reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Independent methodology reviewer | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |
| Independent final-test custodian | `UNSET` | `UNSET` | `UNSET` | `UNSET` | `UNSET` |

## Final status and non-authorization

- Overall status: `TEMPLATE_ONLY`
- Authorized next gate, if any: `UNSET`
- Conditions and expiry/review trigger: `UNSET`
- Withdrawn/changed authority handling: `UNSET`
- Exact disposition-form SHA-256: `UNSET`
- Signatures verified by / method: `UNSET`

No row-level data may be transferred or opened until Gate 0 is independently
approved and the data owner separately authorizes the specific transfer under
verified controls. No training or outcome inspection may begin until all
pre-outcome gates are independently approved and the source-specific addendum
has been signed and hashed. This form cannot override a source owner's limits,
withdrawn authority, institutional policy, or security stop.
