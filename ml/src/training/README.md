Offline fixed Logistic Regression, Random Forest and XGBoost comparison: experiment.py.
Validation-only model/threshold selection; see ADR-012 and development.md.

`ulb_benchmark.py` reuses fixed candidate training/selection on separate ulb-pca-v1 inputs.
It records retrospective results only; production_eligible and behavioral_compatible are false.

`ieee_cis_benchmark.py` uses five fixed raw IEEE-CIS fields and a chronological
split of the labeled training release. It fits category columns on train only,
selects on validation, and retains the single final-test record locally. It
does not serve, register or calibrate the selected model; see the separate
IEEE-CIS protocol and experiment README.
