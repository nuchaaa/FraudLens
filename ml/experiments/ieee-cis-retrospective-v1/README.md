# IEEE-CIS limited retrospective benchmark v1

**Offline, noncommercial research only. `production_eligible=false`,
`behavioral_compatible=false`, `calibrated=false`.** This is a separate
five-field tabular classification benchmark, not a FraudLens behavior-v1
profile evaluation. See the [frozen protocol](../../../docs/research/ieee-cis-retrospective-v1-protocol.md)
and [competition notice](../../../docs/research/ieee-cis-NOTICE.md).

The user reported obtaining the official competition files from a Kaggle
account that accepted its rules. The two labeled training-file hashes were
verified before parsing. The full local report and artifacts are in the
ignored `work/ieee-cis-retrospective-v1-run1/` directory; its exact aggregate
`report.json` is committed here with SHA-256
`98a1e6b85c8f4f8b3d181d86e345dc7fb5357f6b7934f5b37b8de2edab49f004`.
No raw CSV, row IDs, individual predictions, fitted category vocabulary or
model bytes are committed. The four local artifact hashes in the report were
verified against the local files. The source CSVs remain in the user's
Downloads directory.

The labeled transaction release contains 590,540 rows; 144,233 had a matching
optional identity row. The fixed time-offset rule yielded 354,324 training
rows (11,988 positives), 118,108 validation rows (4,611 positives) and
118,108 later test rows (4,064 positives). `TransactionDT` offsets are not
calendar timestamps. Only `TransactionAmt`, `ProductCD`, `card4`, `card6` and
`DeviceType` entered the model; training-only one-hot encoding produced 19
columns. The competition's unlabeled test files were not used.

| Fixed candidate | Validation average precision | Validation F1 at its validation-selected threshold |
| --- | ---: | ---: |
| Logistic Regression | 0.123716 | 0.212986 |
| Random Forest | 0.130069 | 0.224733 |
| XGBoost | 0.144761 | 0.234844 |

XGBoost won the predeclared validation average-precision comparison. Its
validation F1 grid selected threshold `0.70`; the final test was evaluated
once at that threshold. On the later test partition: average precision
`0.133940`, precision `0.174947`, recall `0.322343`, F1 `0.226801`, FPR
`0.054172`, with 1,310 TP, 6,178 FP, 2,754 FN and 107,866 TN. The 4,064
positive labels were 3.44% of test rows. These are measured retrospective
numbers for a deliberately limited feature set, not a calibrated probability,
field detection rate or operational review recommendation.

The source does not document original calendar times, first arrivals,
decision/feedback/label availability, trusted profile admissions, stable
customer and recipient identities, or currency. No customer-disjoint test or
safe adaptive-profile claim is possible. The source's upstream processing
remains opaque. Do not tune the feature set, model or threshold against this
already opened final test or promote its fitted model into the API. Real
behavioral validation remains OPEN at the independent data-owner gate.

Reproduction from the repository root, with source access under the accepted
competition rules and a **new ignored output directory**:

```sh
.venv/bin/python -m ml.src.training.ieee_cis_benchmark \
  --source /Users/nurasilkirgizbek/Downloads/ieee-fraud-detection \
  --output work/ieee-cis-retrospective-v1-another-run
```

Such a rerun is a software reproducibility check, not a new untouched-test
evaluation or permission to retune. Do not distribute the source or local
model artifacts.
