# Phase 17 behavioral dataset readiness audit v1

The [contract](../../../docs/research/phase17-dataset-readiness-v1-contract.md)
was written before running this report. The auditor reads only small JSON
manifests. It does not read source rows, verify evidence references, train a
model or change a database. Reproduce to a **new** file:

```sh
.venv/bin/python -m ml.src.datasets.readiness \
  --manifest ml/experiments/phase17-dataset-readiness-v1/manifests/synthetic-complete.json \
  --manifest ml/experiments/phase17-dataset-readiness-v1/manifests/synthetic-missing-chronology.json \
  --manifest ml/experiments/phase17-dataset-readiness-v1/manifests/synthetic-unknown-label-time.json \
  --manifest ml/experiments/phase17-dataset-readiness-v1/manifests/ulb-known.json \
  --output /private/tmp/new-readiness-audit.json
```

| Frozen manifest | Result | Named gaps |
| --- | --- | --- |
| `synthetic-complete.json` | `READY_FOR_ROW_AUDIT` | None declared; **actual data/evidence unverified** |
| `synthetic-missing-chronology.json` | `BLOCKED` | Arrival and decision times explicitly absent |
| `synthetic-unknown-label-time.json` | `BLOCKED` | Label-availability time not established |
| `ulb-known.json` | `BLOCKED` | Six explicit failures and ten unknowns; see report |

The complete case is fictional, manifest-only and has no inspected transaction
rows. `READY_FOR_ROW_AUDIT` is permission to perform further verification,
**not** eligibility to train, validate behavioral fraud detection or deploy.
Every audit has `behavioral_validation_eligible=false` and
`production_eligible=false`.

The ULB manifest copies only committed v3 metadata, source CSV SHA-256 and
the Time/Amount/Class schema documented in the earlier benchmark protocol.
It records the listed license notice, but research permission for the proposed
behavioral use and privacy/retention plans remain unestablished here. Customer,
recipient, currency, device and absolute event timestamp are absent; arrival,
decision, label availability and trusted admission provenance are unknown.
The existing `ulb-pca-v1` retrospective result remains separate. No ULB rows
or held-out final-test scores were used by this audit.

Manifest file SHA-256 values, in report order:

- `synthetic-complete.json`: `22fab2fe943ac78b23e456e7be5c728a239e17e76e7b68053a0ea9b49600e3cf`
- `synthetic-missing-chronology.json`: `0c1aed27976ae20434af88a72276c5c59a0fccb177edb98b3a49784ca698374c`
- `synthetic-unknown-label-time.json`: `3b56aff59860fda4fcb3b7710e8e7a31ecadf96c89032d289f517cb4a5e0d00c`
- `ulb-known.json`: `ff44f48f4245a9500b4f131f5ca1a867a164df5bb34e0017ff35f3595f010e5d`

Frozen report SHA-256:
`24741c4c30671b0c38e2b2136186f6281e7507b4265460cb18a6eb55ca10182e`.
