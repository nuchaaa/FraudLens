# Phase 7 dataset suitability — 2026-09-20

ULB version 3 and the user-supplied IEEE-CIS competition release have separate
retrospective benchmarks. ULB license/version are verified through public API
metadata; the IEEE-CIS user reports accepting the official noncommercial
competition rules. Both sources are hash-pinned locally. Neither establishes
behavior-v1 provenance or supports production baseline selection. The earlier
synthetic checkpoint and all its limitations remain intact.

| Candidate | Evidence inspected | Missing evidence / decision |
| --- | --- | --- |
| ULB/Worldline credit-card dataset | TensorFlow's official example shows anonymized V columns, Time, Amount and Class | Does not establish customer/recipient/device identities, currency, historical label availability or trusted profile provenance needed by behavior-v1. Kaggle API now verifies the listed ODbL/DbCL license and version 3. Imported as separate ulb-pca-v1; no missing fields are invented. Arrival/label availability and upstream PCA scope remain unknown. |
| IEEE-CIS Fraud Detection | Official competition data page documents labeled transaction and optional identity files joined by `TransactionID`; user reports accepting the Kaggle rules, which permit noncommercial research and restrict redistribution. Exact local training CSV hashes are pinned in the [separate protocol](ieee-cis-retrospective-v1-protocol.md). | A limited five-field retrospective benchmark is measured separately. `TransactionDT` is a relative offset; stable customer/recipient/currency identities, first arrival, original decision, label availability and trusted admissions are not established. It cannot validate behavior-v1 or justify production use. Raw files, row IDs and model remain local. |
| PaySim | Original author's repository describes a synthetic mobile-money simulator and links its dataset | Repository GPL-3.0 concerns code, not automatic approval of downloaded dataset terms. Kaggle dataset card was not readable in this session. Currency, arrival times, label availability, device resolution and profile provenance remain unverified. Do not assume simulator fraud labels are real bank ground truth. |
| FraudLens synthetic-behavior-v1 | Generator source, deterministic seed, source hashes, event/arrival/label clocks, explicit synthetic KZT/customer/recipient/device IDs | Selected only for an engineering demonstration. Entirely authored assumptions; not representative of bank behavior. No externally copied data or dataset license dependency. |

Sources inspected: [TensorFlow's dataset example](https://www.tensorflow.org/tutorials/structured_data/imbalanced_data),
[ULB dataset landing page](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud),
[PaySim author's repository](https://github.com/EdgarLopezPhD/PaySim),
[PaySim dataset landing page](https://www.kaggle.com/datasets/ealaxi/paysim1).
ULB license evidence is now captured in ulb-source-metadata.json from the public Kaggle API.
PaySim terms remain unverified; its unreadable page is only a pointer for future review.

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
own ordered feature version and honest comparison boundaries. The ULB source manifest, notice and frozen protocol now document that narrower benchmark.
No production baseline or behavioral external validation is claimed.

## Phase 17 manifest-level readiness check

The versioned [behavioral readiness contract](phase17-dataset-readiness-v1-contract.md)
now turns these gaps into explicit PASS/FAIL/UNKNOWN checks on a small source
manifest. The frozen `ulb-known.json` audit is `BLOCKED`: six requirements are
explicitly absent and ten are unestablished, including arrival, label
availability and trusted admission provenance. Its source hash and version
come from the already committed ULB v3 metadata; no raw rows or final-test
scores are reprocessed. A fictional complete manifest is only
`READY_FOR_ROW_AUDIT`, never eligible for behavioral validation. The auditor
cannot authenticate legal permission, inspect row chronology or verify
point-in-time evidence; those remain separate prerequisites.

The [prospective behavioral validation protocol](phase17-prospective-behavioral-validation-v1.md)
predeclares how a future independently permitted source would cross those
gates, including original-decision replay, label maturation, chronological and
customer holdouts, and an untouched final test. It is registered without a
source-specific addendum or any real behavioral dataset; predictive validation
remains open. The ULB PCA benchmark and fictional complete manifest do not
qualify under that protocol.
