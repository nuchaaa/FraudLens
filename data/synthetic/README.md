# Controlled Phase 16 scenario simulator

Regenerate these deterministic files from the repository root:

```sh
.venv/bin/python -m backend.adapters.demo.simulator --output data/synthetic
```

The four generated files contain 10 fictional customers, 2,000 prior KZT
transactions (200 each), and 39 candidate transactions across scenarios A–E.
The prior transactions rotate among fictional household, grocery and utility
purposes and known recipients. To intentionally regenerate a changed version,
add `--replace`; the default refuses to overwrite differing files.
`scenario_manifest.json` records both authored expectations and outcomes computed
by FraudLens's **real pure feature, rules, decision, sequence, and profile-gate
code**. The CSV's `authored_label` is a controlled simulation oracle, not a
bank-confirmed fraud outcome or a human analyst verdict.

To exercise the behavior engine without manufacturing database review records,
the simulator assumes that the last 100 normal prior transactions per customer
were approved by an oracle. That profile exists only in memory. The other 100
prior transactions provide raw activity history. The simulator does not write
PostgreSQL, create cases, train a model, or run ML inference. It is a controlled
software behavior check, not an estimate of real-world fraud performance.

The five stories are:

| Story | Authored expectation | Observed experimental result |
| --- | --- | --- |
| A | Ordinary transfer: LOW, ALLOW, ACCEPT | LOW, ALLOW, ACCEPT |
| B | 8M KZT legitimate outlier: review, QUARANTINE | MEDIUM, STEP_UP_VERIFICATION, QUARANTINE |
| C | 500k KZT after B: suspicious against unchanged baseline | HIGH, HOLD_AND_REVIEW; baseline median remains 29k KZT |
| D | Gradual legitimate change | 30 ACCEPTs; short-window median rises from 29k to 94,310 KZT |
| E | Repeated low-value poisoning: flag and prevent admission | The first two transfers remain LOW/ALLOW. From the third transfer, a complete sequence match raises experimental risk-v2 to MEDIUM/STEP_UP_VERIFICATION. The gate quarantines all six without a verified verdict; **risk-v1 remains LOW/ALLOW**. |

E remains an observed risk-v1 gap. The separate versioned
`risk-v2-sequence-experimental` policy adds a review floor for a complete,
compatible sequence match. Missing or incompatible sequence evidence cannot
silently raise risk; incomplete evidence retains risk-v1 or abstains. It does
not change risk-v1's numeric score, issue a bank action, or imply calibration.
The manifest retains the legacy v1 failure separately from six passing A–E
controlled checks. Re-run with `--replace` after a deliberate simulator change.

In the local admin console, **Scenario lab** reads an authenticated, no-store
report computed entirely in memory. It shows the authored oracle expectation,
observed risk-v1 and risk-v2 suggestions, gate outcome, reasons and pass/fail
checks for every candidate. It does not read or write PostgreSQL, infer a human
analyst verdict, or run the offline ML model.

This offline dataset is separate from `demo-scenarios-v1`, its 62 immutable
transaction IDs, the local analyst database, and the fictional review packet.
It cannot replace authorized human feedback in the live learning workflow.
