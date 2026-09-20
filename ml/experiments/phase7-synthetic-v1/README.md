# Phase 7 synthetic comparison — measured engineering results

**Synthetic only. No production model selected; no real-world performance claim.**

Each run uses 2,400 authored events across 24 customers. Eligible split sizes: 1,044 train,
324 validation, 360 final-period known-customer test and 120 held-out-customer test.
All model choices use validation only. The table reports the selected model on final tests.

| Seed | Model | Threshold | Test AP | Precision | Recall | F1 | ROC-AUC | FPR | Held-out AP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | xgboost | 0.75 | 0.7313 | 0.6333 | 0.6786 | 0.6552 | 0.9170 | 0.0331 | 0.9349 |
| 29 | xgboost | 0.60 | 0.5757 | 0.7059 | 0.3871 | 0.5000 | 0.8878 | 0.0152 | 0.7301 |
| 43 | xgboost | 0.50 | 0.6427 | 0.6364 | 0.5000 | 0.5600 | 0.8584 | 0.0241 | 0.7387 |

Validation average precision for all candidates:

| Seed | Logistic Regression | Random Forest | XGBoost |
| --- | --- | --- | --- |
| 17 | 0.4754 | 0.6796 | 0.7906 |
| 29 | 0.5595 | 0.4982 | 0.7230 |
| 43 | 0.4400 | 0.5400 | 0.7284 |

Test AP mean: 0.6499; sample standard deviation across three seeds: 0.0781.
This is seed sensitivity, not a confidence interval. Small positive counts limit precision.
Raw JSON reports retain every metric, confusion count, prevalence, parameter and artifact hash.

Full local artifacts: ../../work/phase7/final-seed17 (and 29/43) relative to the repository.
Generated data/models are kept outside Git. Recreate them using the runbook; report hashes
permit checking outputs. Joblib serialization and numerical results may vary across platforms.
All three selected models are experimental and production_eligible=false.

Limitations: authored labels/distributions, static synthetic bootstrap, one currency, no
burst sequence/adaptive gate study, no external dataset, no calibration or confidence intervals.
See docs/research/dataset-assessment.md and ADR-012 before interpreting these numbers.
