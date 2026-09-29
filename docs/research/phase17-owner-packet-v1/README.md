# Phase 17 source-owner packet v1

**TEMPLATE ONLY — NOT A DATA-USE AGREEMENT, PERMISSION, APPROVAL, OR SIGN-OFF.**

This source-neutral packet prepares a future review of a behavioral dataset under
the frozen [prospective validation protocol](../phase17-prospective-behavioral-validation-v1.md).
It does not identify a data owner or source, authorize contact, authorize access,
authorize transfer, or permit analysis. No source-specific evidence or signatures
are currently present. Every field that depends on a source or a reviewer remains
`UNSET` until supplied and independently checked.

The packet contains:

- [Evidence request](data-owner-evidence-request.md): requested artifacts, their
  owners, and the order in which they may be reviewed.
- [Source-specific addendum template](source-specific-addendum-template.md):
  versioned fields to be completed and hashed before examining outcomes.
- [Independent disposition form](independent-disposition-form.md): an unsigned
  gate-by-gate review record that cannot itself grant data rights.

## Required sequence

1. The project owner identifies a prospective source and authorized contact
   route. This repository does not contact anyone on the project's behalf.
2. A data owner independently confirms authority and supplies the requested
   governance evidence. Until that evidence is received and reviewed, do not
   receive, copy, open, hash, or ingest private rows.
3. The designated reviewers evaluate their own gates and record evidence
   references and signed decisions. A project author cannot substitute for an
   independent reviewer.
4. Only after permission, privacy, custody and transfer controls are approved
   may the owner and project operator agree on a controlled transfer. Row-level
   chronology and identity checks then precede split freeze or outcome inspection.
5. The source-specific addendum is versioned and hashed before any label or
   outcome inspection. Any material change requires a new version and preserves
   the prior artifact and its disposition.

## Current acquisition disposition

`source_id=UNSET`; `source_owner=UNSET`; `source_bytes_received=false`;
`written_permission_verified=false`; `source_specific_addendum_signed=false`;
`independent_disposition=UNSET`. The repository contains no independently
permitted behavioral source. The known ULB PCA benchmark remains ineligible for
behavior-v1 and its frozen final test must not be reused. Predictive validation
is therefore **OPEN / BLOCKED BEFORE TRAINING**.

This packet is a checklist, not legal advice or evidence that a source owner,
reviewer, signature, right, control, label, split, sample size, budget, or date
exists. `DOCUMENTED` in a future form means only that a reference was supplied;
reviewers must verify the evidence behind it.
