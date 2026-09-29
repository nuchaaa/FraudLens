# Phase 17 fictional row acceptance v1

The [predeclared cases](../../../docs/research/phase17-fictional-row-acceptance-v1-plan.md)
exercise selected mechanics of the [frozen prospective protocol](../../../docs/research/phase17-prospective-behavioral-validation-v1.md)
on tiny, obviously fictional JSON. The source and report contain no genuine
bank record, analyst verdict, model score or predictive metric. The report's
overall `BLOCKED` status is intentional: the source includes duplicate,
non-UTC and impossible-arrival rows to demonstrate explicit rejection. An
accepted fictional row is not approved real-world data.

Reproduce to a **new** file from the repository root:

```sh
.venv/bin/python -m ml.src.datasets.row_acceptance \
  --source ml/experiments/phase17-fictional-row-acceptance-v1/source.json \
  --output /private/tmp/new-fictional-row-acceptance.json
```

SHA-256 of the exact committed source file:
`1c0e1ea8e1c5652a938e7cdbeaf766d788d1312e8fca783f818f292968b34b2f`.
SHA-256 of the exact committed report file:
`2b67f5fa0ae149bbd3014d0821e1a1d34e1220a8eb5c35154aee401cc06d7358`.
Protocol SHA-256 remains
`501cce195635aa02f7ca4d368a983730b7d611a7461daccbf53a4a3acd3dd8b2`.
The CLI refuses to overwrite an output file and does not write to the source
or PostgreSQL.

At candidate C's original decision, H1/H3/H4 are raw history; only H1/H4
have simulated admissions available. H2's earlier event arrives later, H3's
assumed confirmation is later, C is excluded from itself, and a same-instant
and strict lower-boundary row are excluded. The separate corrected view may
see H2/H3, but excludes H4 after its simulated admission is revoked. It links
to the immutable original view ID; it does not revise C's actual historical
decision. The view ID hashes the candidate, knowledge cutoff and *included*
raw/trusted context rather than future source bytes, so a later irrelevant
row cannot rename the original known context. The report still hashes the
entire source for reproducibility and records retrospective exclusions.

This limited harness does not verify real identity mapping, legal authority,
feedback independence, source completeness, clock provenance, labels,
behavior-v1 feature parity, statistical support, or the source-specific
addendum. It emits no model fit, risk-v2 threshold, or final-test result.
Behavioral validation and production eligibility remain false. The 62-row
analyst walkthrough and Phase 15 deployment gate remain separate.
