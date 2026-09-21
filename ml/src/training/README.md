Offline fixed Logistic Regression, Random Forest and XGBoost comparison: experiment.py.
Validation-only model/threshold selection; see ADR-012 and development.md.

`ulb_benchmark.py` reuses fixed candidate training/selection on separate ulb-pca-v1 inputs.
It records retrospective results only; production_eligible and behavioral_compatible are false.
