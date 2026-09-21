# ADR-013: External retrospective benchmark without behavioral promotion

Status: accepted for Phase 7, 2026-09-20.

## Decision and evidence

Public Kaggle API metadata resolves ULB dataset licensing and version, even though
the browser-rendered card was unreadable. Import anonymized version 3 under its listed
ODbL/DbCL terms for a separate retrospective benchmark. Preserve attribution, source
URL/version, download and CSV SHA256, and metadata evidence. A future changed upstream
file must fail the content pin until independently reviewed. Fetch/outputs are create-only
and bounded; extraction reads only creditcard.csv into a fixed path.

The actual CSV schema is Time, V1…V28, Amount, Class. It supplies no account, recipient,
device or currency field, arrival clock, label-availability clock or reviewed profile
history. Upstream PCA fitting scope is unknown. Accordingly it cannot support behavior-v1,
customer-disjoint testing, trusted bootstrap or a deployment-availability replay.

Introduce `ulb-pca-v1` (V1…V28, Amount) as a separate ordered feature contract in the offline
ML package, using the existing finite FeatureVector value object. Rules-v1 rejects it.
Use the same small extractor when preparing rows and for any future benchmark replay.
Do not fabricate missing behavioral fields or mix nominal amounts across inferred currencies.
Time partitions source rows only; Class never enters feature extraction or deduplication.

## Frozen evaluation

`docs/research/ulb-benchmark-protocol.md` was written before data import/training.
Its content hash is retained in the report. Fixed boundaries are 86,400 and 129,600
elapsed seconds. Deduplicate identical model feature tuples in chronological order,
keeping their first source occurrence independent of labels. This excludes later duplicate
features across partitions and changes the evaluated population to first-seen tuples.
Preserve source row numbers and exclusion counts. Malformed input or one-class partitions
fail explicitly; never move boundaries after seeing the labels.

Reuse existing fixed LR/RF/XGBoost configurations, seed 17, validation average-precision
selection and validation F1 grid threshold. Only the selected model sees the final test;
no refitting. Shared code is reused without changing prior synthetic experiments.
Full final metrics and validation comparisons are recorded; model and row-level artifacts
remain outside Git. Source/lock/code/model hashes support local reproduction. A successful
report is written last; incomplete directories are not completed experiments.

## Interpretation and remaining work

This is measured discrimination on an external anonymized dataset under a retrospective
protocol. Final fraud labels are known in the released file, but their historical availability
is not supplied. The upstream PCA may have used information beyond our training partition;
we cannot audit that. Thus do not claim end-to-end leakage-free deployment performance,
calibration, causal effectiveness, cross-bank generalization or safe-profile adaptation.

All reports set production_eligible=false and behavioral_compatible=false. A benchmark
winner is not a validated production behavior model. No serving model, HTTP prediction,
assessment write or admission workflow is introduced. A later Phase 8 experimental
adapter must retain explicit model/feature scope and synthetic/benchmark restrictions;
production requires evidence of suitable feature and label availability in the target setting.
