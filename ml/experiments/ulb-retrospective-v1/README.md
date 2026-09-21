# ULB retrospective benchmark v1 — measured results

**External anonymized benchmark only. production_eligible=false; behavioral_compatible=false.**

Contains information from [ULB / Worldline Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud),
available under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) and
[DbCL 1.0](https://opendatacommons.org/licenses/dbcl/1-0/). See
[full source notice](../../../docs/research/ulb-NOTICE.md) and the supplied transformation code.

Version 3 contained 284,807 source rows. The frozen first-feature-occurrence policy excluded
9,144 later identical feature tuples independently of labels. Retained partitions:
140,216 train (272 positives), 46,357 validation (87), 89,090 test (114).

| Validation candidate | Average precision | F1 at chosen threshold | Threshold |
| --- | --- | --- | --- |
| logistic_regression | 0.798459 | 0.413408 | 0.95 |
| random_forest | 0.771210 | 0.792453 | 0.70 |
| xgboost | 0.737815 | 0.761364 | 0.95 |

Logistic Regression won validation average precision under the frozen protocol. Its
F1-selected threshold was 0.95, the top of the predeclared coarse grid. Random Forest
had higher validation F1; model selection was by AP, not F1, and was not changed after
seeing test performance. No production operating point or calibrated probability follows.

| Selected-model final test metric | Value |
| --- | --- |
| precision | 0.274854 |
| recall | 0.824561 |
| f1 | 0.412281 |
| roc_auc | 0.951419 |
| pr_auc_average_precision | 0.733432 |
| fpr | 0.002787 |
| prevalence | 0.001280 |
| tn | 88728 |
| fp | 248 |
| fn | 20 |
| tp | 94 |

This test contains 114 positive labels; the selected point generated 248 false positives
and detected 94 positives. Ranking quality does not establish a usable review workload.
Upstream PCA fitting scope and historical label/arrival availability are unknown. No
customer-disjoint or adaptive-profile conclusion is possible. Single seed 17 only.

The protocol was frozen before import/training. The first attempted run failed while
parsing quoted numeric CSV values before fitting; a regression-tested parser fix preceded
the completed run. No model settings, boundaries or selection criteria were changed.

Full local artifacts: ../../work/phase7/ulb-benchmark-v1-run2 from the repository root.
CSV: ../../work/phase7/ulb-v3/creditcard.csv. report.json retains hashes, model parameters,
package versions and metrics; source rows, split indices, predictions and model are not
committed. Reproduce using development.md and the hash-pinned fetcher. Only load trusted
locally produced joblib files. See ADR-013 for the boundary with future serving work.
