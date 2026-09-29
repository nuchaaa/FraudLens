# IEEE-CIS retrospective benchmark protocol v1

Status: **predeclared before row-label inspection, feature fitting or model
selection**. This is a separate offline `ieee-cis-tabular-v1` experiment, not
behavior-v1 validation, a production model or a source-specific addendum to the
prospective behavioral protocol. The user reports downloading the official
Kaggle competition files through an account that accepted its rules. This
report is not an independent verification of the account or institutional
authority. See the [source notice](ieee-cis-NOTICE.md).

## Source and permitted scope

Use only the labeled `train_transaction.csv` and `train_identity.csv` files from
[IEEE-CIS Fraud Detection](https://www.kaggle.com/competitions/ieee-fraud-detection/data).
The official page states that `TransactionID` joins them, identity rows are
optional, `isFraud` is the retrospective target, and `TransactionDT` is elapsed
time from an undisclosed reference, not a calendar timestamp. Kaggle lists the
license as subject to [competition rules](https://www.kaggle.com/competitions/ieee-fraud-detection/rules),
which permit noncommercial research and restrict redistribution. Do not commit
raw rows, split IDs, predictions or model bytes. The competition `test_*` files
have no supplied labels and are excluded from fitting, selection and final
evaluation. No leaderboard submission is part of this protocol.

Pin exact local bytes before training:

| File | SHA-256 |
| --- | --- |
| `train_transaction.csv` | `3a5c83ab6b3cc13dcabe5ffa9f522307fd5f7f7b6e6f6a60c32284ca6283d642` |
| `train_identity.csv` | `b63c725d8377be90a995268d97f347c17d456b95db45807adcf9f59cd603c37c` |
| `test_transaction.csv` (excluded) | `2a8e51f1d335a86025d2b7f45beb9b78d0ab1edd726ef531d8b71a8a0065c011` |
| `test_identity.csv` (excluded) | `3e5978cb13ca5e72f52babc4349ae0125e14b87ca8bfabe952ab67bb4ff1e10b` |

These hashes identify local bytes; they do not establish label quality,
historical availability, identity continuity or permission beyond the user's
stated Kaggle acceptance. Keep outputs in an ignored local directory.

## Fixed rows and features

Require unique integer `TransactionID` in each source, an exact-width CSV row,
nonnegative integer `TransactionDT`, finite strictly positive `TransactionAmt`,
and binary `isFraud`. Reject duplicate IDs, malformed rows, invalid values or
a source-hash mismatch; do not silently deduplicate or repair. Left-join the
optional identity file by `TransactionID`, retaining every transaction.
Missing identity and blank category fields are an explicit `__MISSING__`
category. Reject an identity ID absent from the transaction source rather than
guessing its lineage.

The ordered model inputs are `TransactionAmt` and categorical `ProductCD`,
`card4`, `card6`, `DeviceType`. Fit one-hot categories on training rows only;
unknown validation/test categories are ignored. These fields are chosen before
label inspection and contain no inferred customer, recipient, merchant, device
identifier, geography or currency. `TransactionDT` is for splitting only;
`TransactionID` is for joining/validation only; `isFraud` is a target only.
Do not include Vesta-engineered `C`, `D`, `V` or identity `id_*` columns because
their upstream fitting and availability are unverified. The benchmark measures
this limited feature set, not the entire Kaggle leaderboard problem.

## Frozen split and model selection

Sort all labeled transaction rows by `(TransactionDT, TransactionID)`. Before
looking at labels, choose the time value at rank `floor(0.60*n)` as the first
validation offset and the value at rank `floor(0.80*n)` as the first test
offset. Use `time < train_end`, `train_end <= time < validation_end`, and
`time >= validation_end`; equal times never cross partitions. If boundaries
collapse, any partition is empty, or any partition lacks either class, fail
and report a limitation rather than change boundaries after seeing labels.
There is no customer-disjoint split because no independently verified stable
customer key or identity mapping is supplied. Final `isFraud` labels have no
verified availability times, so this is a retrospective, not original-decision,
evaluation.

Use seed 17 and the existing fixed candidates: balanced Logistic Regression
with training-only StandardScaler; Random Forest with 120 trees, depth 6,
minimum leaf 5 and balanced weights; XGBoost with 120 trees, depth 3, rate
0.05 and train-derived positive weight. No search, early stopping, row
resampling or refitting after selection. Fit category encoding on training
rows only. Choose highest validation average precision; lexical model-name
tie-break. Choose the selected model's threshold on validation alone from
0.05 to 0.95 by F1, breaking ties toward a higher threshold. Apply the
selected model and threshold once to the held-out chronological test.

Report source/feature/protocol/code/lock hashes, package versions, split
counts and positives, validation results for every candidate, selected
threshold, final confusion counts, precision, recall, F1, average precision,
ROC-AUC, false-positive rate and prevalence. Preserve local selected model,
split IDs and prediction artifacts with hashes but do not commit them. Keep
outputs create-only. The selected scores are **uncalibrated**; do not call
them probabilities or derive a production review threshold from this run.

## Interpretation and stop rules

This release does not establish true calendar event times, arrival/decision
times, label or feedback availability, trusted admissions, currency, stable
customer/recipient identity, or independent adjudication. It cannot answer
whether safe adaptive profiles resist poisoning, whether a model would have
detected fraud at an original decision, or whether a Kazakhstan bank could
deploy it. Different source conditions require a new protocol and untouched
test data; do not retune on this final test. Keep Phase 17 prospective
behavioral validation OPEN. Do not serve or register a model from this run.
