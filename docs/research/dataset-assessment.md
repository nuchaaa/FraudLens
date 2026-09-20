# Phase 7 dataset suitability — 2026-09-20

No external dataset has been approved or imported. This checkpoint exercises the
experiment pipeline with original authored synthetic facts. It cannot select a
production fraud model or validate the adaptive-profile research hypothesis.

| Candidate | Evidence inspected | Missing evidence / decision |
| --- | --- | --- |
| ULB/Worldline credit-card dataset | TensorFlow's official example shows anonymized V columns, Time, Amount and Class | Does not establish customer/recipient/device identities, currency, historical label availability or trusted profile provenance needed by behavior-v1. Dataset license was not verified from its dynamically rendered Kaggle page. Do not invent these fields; a separate benchmark feature contract would be needed. |
| PaySim | Original author's repository describes a synthetic mobile-money simulator and links its dataset | Repository GPL-3.0 concerns code, not automatic approval of downloaded dataset terms. Kaggle dataset card was not readable in this session. Currency, arrival times, label availability, device resolution and profile provenance remain unverified. Do not assume simulator fraud labels are real bank ground truth. |
| FraudLens synthetic-behavior-v1 | Generator source, deterministic seed, source hashes, event/arrival/label clocks, explicit synthetic KZT/customer/recipient/device IDs | Selected only for an engineering demonstration. Entirely authored assumptions; not representative of bank behavior. No externally copied data or dataset license dependency. |

Sources inspected: [TensorFlow's dataset example](https://www.tensorflow.org/tutorials/structured_data/imbalanced_data),
[ULB dataset landing page](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud),
[PaySim author's repository](https://github.com/EdgarLopezPhD/PaySim),
[PaySim dataset landing page](https://www.kaggle.com/datasets/ealaxi/paysim1).
The unreadable pages are pointers for a future review, not evidence of confirmed terms.

## External data acceptance requirements

Record exact source/version, access date, content hash, permitted uses and redistribution
terms; distinguish dataset license from software license. Inspect actual schema and units.
Verify event chronology, account/recipient continuity, currency, label definition and
when labels became available. Document missingness and delayed arrivals. Missing device
or currency cannot be encoded as a false known value. Preserve source precision: do not
invent minute-level velocity from coarse time buckets. Trusted bootstrap requires separate
available-before-prediction evidence; final fraud labels cannot retrospectively admit
transactions to profiles. Freeze train/validation/test periods before inspecting outcomes.

An external dataset may support a narrower nonbehavioral benchmark, but that needs its
own ordered feature version and honest comparison boundaries. No download, provenance,
production baseline or external validation is claimed at this checkpoint.
