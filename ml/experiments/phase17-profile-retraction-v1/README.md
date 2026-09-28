# Phase 17 append-only correction fixture v1

The protocol at `docs/research/phase17-retraction-replay-v1-protocol.md` was
written before executing this report. Source generator:
`ml/src/evaluation/profile_retraction.py`. Its committed `source.json` is a
human-readable rendering; its file SHA-256 is
`158a4c2e10af3ab37ff789f460018f73d6f032a08941364f8c165eded749975d`.
The canonical compact source SHA-256, pinned in the protocol and code, is
`a47cf3b27e4556da4fa71554f6057570a7135c7ad56be71b01219ee1064a74dc`.
The deterministic `report.json` SHA-256 is
`cca72cb96342a02754e26a8f2388faee66445ec76776cc802c6b73c57239683b`.

Reproduce into a **new** path, never overwrite the frozen artifact:

```sh
.venv/bin/python -m ml.src.evaluation.profile_retraction --output /private/tmp/new-replay.json
```

On the authored late-arrival customer, L2 was accepted at its original
processing time and the profile held six observations. L1 then arrived with
an earlier event time. The unchanged gate refused to apply it to the L2-headed
profile, and that original six-observation view remains in the report. The
later explicitly requested offline corrected view replays L1 then L2 in event
order and holds seven observations. It **does not** claim either event was
available at the earlier L2 decision.

On the separate revoked-confirmation customer, the originally accepted R1
view holds six observations. A retraction became available later. The
corrected offline view excludes R1 and holds the five assumed baseline
observations; it does not mark R1 fraudulent. Both original and corrected
views have distinct IDs, processing/cutoff times, source hashes and a
supersession link. Two repeated correction requests return their original
view IDs and create no extra view. Changing scope or cutoff under a reused
request ID fails. Tests also cover exact availability boundaries, source
tampering, out-of-order processing and customer isolation.

Every baseline approval and confirmation is a simulated oracle assumption,
not an authenticated analyst verdict. These are two constructed software
mechanisms, not fraud-detection metrics or evidence that a production
correction can safely run. The runner cannot recover unobserved facts, actual
commit/availability time, compromised-operator identity, external proof, or
bank actions already taken. It writes no PostgreSQL rows or live profiles.
