# ADR-012: Offline synthetic comparison and production eligibility

Status: accepted for the Phase 7 synthetic experiment checkpoint, 2026-09-20.

## Scope and source

`ml/src/datasets/synthetic.py` authors stochastic events using a fixed local RNG.
Labels are sampled latent simulation conditions (8% probability), not derived from
FraudLens rule matches. Fraud/normal amount, time, recipient and device distributions
overlap; legitimate extreme purchases are possible. This avoids circular threshold
labels but still only measures the generator's assumptions, not real detection skill.
One event per customer/day cannot assess short-window burst detection.

Each customer has 20 independently authored normal observations available at experiment
start. This is declared synthetic bootstrap, never a production trusted-history workflow.
Profiles remain static; labels never authorize updates. Six of 24 customers are withheld
from fitting/selection, with their own static bootstrap and prior raw activity available
for features. This tests model generalization to customers with history, not cold starts.
Single KZT currency avoids mixing unconverted nominal amounts. No real identifiers exist.

## Temporal preparation

For each event, prediction time is its simulated arrival (0, 2 or 120 minutes later).
Raw history must have arrived strictly earlier and have strictly earlier event time;
same instant and candidate are excluded. Production `extract_features` supplies all 29
behavior-v1 features. Future target labels, arriving two days later, are not feature inputs.
A prepared row records transaction/customer IDs, both clocks, label availability and values.
These synthetic clocks are authored source facts, not claimed database commit timestamps.

Train/validation/test boundaries are day 60/80/100 in a 100-day stream. Train labels
must mature before day 60; validation labels before day 80. Boundary-crossing arrivals
are excluded from adjacent source periods. Test label freeze is day 103. All sets require
both classes; otherwise fail explicitly. A quarter of customers are excluded from training
and validation, then evaluated on the final period separately. Earlier raw transactions
of held-out customers may support their own historical features; no fitted preprocessing
uses their rows. No random row splitting or target-derived profile learning occurs.

## Models and selection

A single fixed configuration per model avoids hidden test tuning:

- Logistic Regression: train-fitted StandardScaler pipeline, balanced weights, 2,000 iterations.
- Random Forest: 120 trees, depth 6, leaf minimum 5, balanced weights, one worker.
- XGBoost: 120 trees, depth 3, learning rate 0.05, histogram CPU training, one worker,
  positive weight calculated only from training prevalence.

Each seed runs all three. Highest validation average precision selects a model; ties
use lexical model name. Threshold is validation F1 maximum on 0.05…0.95 in 0.05 steps;
ties prefer higher thresholds. Neither final-test nor held-out-test values enter selection.
Only the selected model is evaluated on those sets; no retraining after selection.
F1 is a demonstration objective, not a bank-approved cost function. Class-weighted model
scores are uncalibrated and must not be presented as real fraud probabilities.

Metrics include precision, recall, F1, ROC-AUC, average precision (non-interpolated PR-AUC
summary, not trapezoidal area), FPR, confusion counts, prevalence and sample size. Seeds
17/29/43 are all reported; do not choose a favorite seed. A pilot seed17 run checked the
runner before the recorded runs; there was no hyperparameter tuning from its test results.
Seed differences show sensitivity, not confidence intervals or an external validation study.

The pipeline approach follows [scikit-learn leakage guidance](https://scikit-learn.org/1.8/common_pitfalls.html).
Metric definitions follow [scikit-learn evaluation documentation](https://scikit-learn.org/stable/modules/model_evaluation.html).

## Artifacts and operational boundary

Each create-only output directory retains source facts, prepared features, split IDs,
final predictions and selected model, with SHA256 hashes, package/lock versions, code
hashes and experiment configuration in report.json. Failure leaves no complete report;
a directory alone is not a successful experiment. Local joblib model files use pickle:
load only artifacts produced by a trusted local run, never untrusted uploads.

ML dependencies live in the optional `ml` dependency group. API/domain dependencies
remain separate and production wheels still contain backend only. Run experiments from
the source checkout. macOS XGBoost requires OpenMP (libomp); CPU-only experiments do
not require GPUs. CI installs the ML group for tests; its remote execution is unverified.

Every report says synthetic_only=true and production_eligible=false. No model is copied
to a serving registry, no HTTP inference is added, and no RiskAssessment is fabricated.
External dataset/license/availability approval and defensible production model selection
remain open Phase 7 work. Phase 8 may add explicitly experimental inference only with
that limitation preserved. Research comparisons of static/naive/safe adaptation remain
future experiments, as do calibrated thresholds and confidence intervals.
