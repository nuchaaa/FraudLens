# Research protocol — no experimental results yet

Question: How can adaptive behavioral fraud detection learn legitimate changes
without allowing anomalous or fraudulent transactions to poison the customer's
behavioral profile?

## Comparisons

A. Arithmetic-mean baseline with static history.
B. Median/MAD robust baseline with static history.
C. Naive adaptive baseline admitting every transaction.
D. Safe adaptive baseline admitting transactions through a profile-update gate.

Keep underlying event streams, train/validation/test boundaries and decision
operating points comparable. Separate the effects of profile statistics, update
policy, deterministic rules and the ML model. Compare rules-only, ML-only and
hybrid strategies independently.

## Scenarios

1. Normal ₸20k–₸50k activity followed by a ₸25k known-recipient purchase.
2. A legitimate ₸8M vehicle purchase with delayed verification.
3. A fraudulent ₸500k new-recipient transfer after the vehicle purchase.
4. Confirmed gradual drift from ₸30k toward ₸100k+.
5. An escalating ₸50k / ₸70k / ₸100k / ₸150k / ₸250k / ₸500k poisoning sequence.

Include both unverified poisoning and mislabeled/compromised confirmations. The
current domain gate handles the former; it does **not** prove resistance to the
latter. Simulate delayed feedback, cold start, missing history, currency changes,
zero MAD, event-time disorder and profile update races.

## Leakage prevention

Generate or replay features chronologically using only transactions and feedback
available before the prediction timestamp. Preserve when each label became known.
The candidate transaction must not enter its own profile snapshot. Never derive
global medians from future data. Fit scalers, imputers, resampling and model
parameters on training data only. Apply SMOTE only inside training folds if used;
start with class weights to reduce extra assumptions.

Use earlier data for training, a later validation period for model and threshold
selection, and the latest untouched period for final evaluation. Also evaluate
held-out customers to distinguish personalization from generalization. Synthetic
labels must not simply restate the same inference thresholds, which would make
performance circular and uninformative.

## Measurements

Detection: precision, recall, F1, ROC-AUC, PR-AUC, FPR and confusion counts at
predeclared operating points. Report class prevalence and seed variability.

Profiling: baseline displacement after an outlier, time to adapt to sustained
legitimate drift, contamination rate, quarantined legitimate fraction and analyst
review burden. Include bootstrap confidence intervals where justified.

Reproducibility: save seeds, generator version, dataset hash, feature version,
model artifact hash, split boundaries, label availability assumptions, policy
configuration and package lockfile. No current test assertions are predictive
performance claims. There are no model metrics or research results in this session.
