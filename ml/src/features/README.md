# Shared production features

Import `extract_features` and `extract_many` from `backend.app.features.engine`.
Do not implement a second training-only feature path. `FeatureContext` supplies frozen
candidate, revision and raw-history facts; persisted capture artifacts can be read using
`backend.adapters.features.artifacts.read_context`. Feature version `behavior-v1` has
29 ordered finite numeric values. Keep row labels and splits outside this transformation.

Offline dataset preparation must prove chronology and label availability independently.
Recapturing current database history is not historical knowledge reconstruction. See
[ADR-010](../../../docs/adr/ADR-010-feature-context-and-availability.md). No dataset or
trained model is included in this checkpoint.

External ULB benchmark inputs use the separate `ulb.py` / `ulb-pca-v1` extractor:
V1…V28 and Amount. There is no mapping from these anonymized components to behavior-v1.
This code is offline; future benchmark replay must reuse the same contract. Rules-v1
rejects it. Do not invent currency, device, recipient or customer-profile features.
