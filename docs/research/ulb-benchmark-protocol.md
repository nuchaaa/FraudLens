# ULB retrospective benchmark protocol v1

Frozen before dataset import/model evaluation on 2026-09-20.

## Scope

Source: Machine Learning Group ULB / Worldline credit-card fraud dataset, Kaggle
`mlg-ulb/creditcardfraud`, dataset ID 310, version 3. Public metadata lists
Database: Open Database, Contents: Database Contents. Record exact source bytes,
content hashes, retrieval metadata and notices. Raw rows/models stay outside Git.

This is an anonymized historical classification benchmark, NOT a behavior-v1 model,
not customer personalization and not a realistic point-in-time deployment replay.
Customer/recipient/device identities, currency, arrivals and label-availability times
are not supplied. Upstream PCA fitting scope is unknown. Do not fabricate these facts.

## Fixed feature and sample contract

`ulb-pca-v1`: ordered V1…V28 followed by Amount, float values from source, no inferred
units or currency. Time is used only to partition/sequence rows, not a model input.
Class is the target only. Do not create profiles or synthesize UUID-based identities.
Row identity is CSV line number. No behavior-v1 rules run on these inputs.

Require exact header, finite numerics, nonnegative Time/Amount and binary Class.
Reject missing/extra fields, invalid values, wrong pinned content hash or unsupported
metadata. Stable chronological ordering by Time then source row. Retain only the first
occurrence of an identical feature tuple (V1…V28, Amount) across the ordered stream,
independent of Class. Later feature duplicates are excluded without inspecting their
labels, including across partitions. Record exclusion counts. This deliberately measures
first-seen feature tuples, not every transaction in the release.

## Fixed temporal partitions and selection

Training: Time < 86400 seconds (first day).
Validation: 86400 <= Time < 129600 (next 12 hours).
Test: Time >= 129600 (remaining observations in the release).
Equal timestamps never straddle boundaries. No shuffled row split, no downsampling.
Labels are final retrospective labels; their availability at these boundaries is unknown.
All partitions must contain both classes; fail rather than adjust boundaries from outcomes.
No held-out-customer evaluation is possible without customer identities.

One preregistered seed: 17. Reuse the existing fixed model configurations from ADR-012:
Logistic Regression with training-only StandardScaler and balanced weights; Random
Forest 120 trees/depth6/minleaf5/balanced; XGBoost 120/depth3/rate0.05 with train-derived
positive weight, CPU single worker. No hyperparameter search or early stopping.
Select highest validation average precision; lexical name tie-break. Select threshold
using validation F1 on 0.05…0.95 grid with higher-threshold tie-break. Do not refit.
Evaluate only the selected model on test once; report all validation candidates.

Report precision/recall/F1, ROC-AUC, average precision (not trapezoidal PR area), FPR,
confusion counts, sample size and prevalence. Save model, split source-row IDs, test
scores, exact configuration, code/lock/package versions and hashes. Outputs are create-only.
No confidence intervals, probability calibration or general real-world claims. A single
seed is an initial external benchmark, not a robustness study. Do not promote its model
into behavioral inference or automatically admit any transaction into profiles.

If corrections are required, record them explicitly with a new protocol version before
new evaluation; do not overwrite completed reports or tune against the final test.
