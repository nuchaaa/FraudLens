# Research protocol — external validation still outstanding

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
performance claims. Phase 7 adds measured synthetic engineering results in
ml/experiments/phase7-synthetic-v1; these do not validate the adaptive-profile hypothesis.

## Current experiment boundary

ADR-012 records the static synthetic experiment and predeclared selection rules.
The first offline A/B/C/D-style **profiling mechanism** comparison is recorded in
[`phase17-profile-comparison-v1-protocol.md`](phase17-profile-comparison-v1-protocol.md)
and its frozen synthetic report. It tests four statistic/update combinations
on one authored chronological stream. The separate
[`phase17-profile-factorial-v1-protocol.md`](phase17-profile-factorial-v1-protocol.md)
crosses the two statistics with three update policies on that unchanged source.
The [`phase17-retraction-replay-v1-protocol.md`](phase17-retraction-replay-v1-protocol.md)
predeclares a new append-only offline correction fixture for late arrivals and
revoked simulated confirmations. None provides external adaptive-profile
validation, authenticated correction authority or calibrated risk. ADR-013
records the separate ULB retrospective benchmark with unknown arrival/label
availability and PCA fitting scope. The read-only
[`phase17-dataset-readiness-v1-contract.md`](phase17-dataset-readiness-v1-contract.md)
audits source manifests for these gaps before any new behavioral validation
can be proposed. A complete manifest still needs row-level and independent
evidence review. The frozen
[`phase17-prospective-behavioral-validation-v1.md`](phase17-prospective-behavioral-validation-v1.md)
now registers the future owner-permission, row-chronology, held-out-customer,
label-availability, validation-selection and independent sign-off gates. Its
source-specific cutoffs and capacity parameters remain unassigned until an
eligible source is independently approved. None establishes a production baseline.

The small [fictional row-acceptance plan](phase17-fictional-row-acceptance-v1-plan.md)
and its frozen source/report rehearse selected original-versus-corrected clock,
identity and split rejection rules without reading any real behavioral rows.
Its intentional `BLOCKED` source is an engineering check, not a dataset audit,
analyst verdict or performance experiment.
