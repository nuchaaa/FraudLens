# Independent sequence-policy challenge v1

This is an offline **falsification exercise**, separate from the Phase 16 A–E
generator. Reproduce it from the repository root:

```sh
.venv/bin/python -m ml.src.evaluation.sequence_challenge
```

The frozen [report](report.json) has SHA-256
`1d3f5e876d8f0678fe353cadf5d72000bf8318a0dddce1b5c3366ec2bdd98ab2`.
The script writes a new path only with `--output`; it refuses overwrite. It
uses the pure feature, risk-v1, sequence-v1 and risk-v2 code, and never accesses
PostgreSQL or loads an ML model. Each 30k KZT baseline and its assumed approval
are authored for this exercise; no analyst or bank verified them.

| Case | Authored intent | Observed risk-v2 suggestion | Finding |
| --- | --- | --- | --- |
| Single known-payee transfer | Benign | LOW/ALLOW | No sequence match. |
| Four known-payee household transfers in 30 minutes | Benign | MEDIUM/STEP_UP_VERIFICATION | Potential unnecessary review from cumulative low-value signal. |
| Four new-payee transfers in 30 minutes | Benign | MEDIUM/STEP_UP_VERIFICATION | Potential unnecessary review. |
| Same observable new-payee pattern | Attack | MEDIUM/STEP_UP_VERIFICATION | Identical available behavior cannot distinguish intent. |
| Four new-payee transfers spaced 25 hours apart | Attack | LOW/ALLOW | The 24-hour sequence window misses this authored attack. |
| One 8M KZT purchase | Benign | MEDIUM/STEP_UP_VERIFICATION | Existing risk-v1 suggestion is retained. |
| Four transfers without a verified profile | Unknown | Abstain | All sequence signals remain unavailable. |

These seven deliberately selected examples are **not** a random sample, a
validation split, verified labels, or a basis for precision, recall, false
positive rate, threshold selection or calibration. They expose two design
limits: review burden for plausible benign batches and evasion by spacing
transfers beyond the authored window. No thresholds were adjusted using these
cases. `risk-v2-sequence-experimental` remains production-ineligible.

The reviewed risk-v2 policy now pins the exact default sequence-v1 policy
fingerprint. A self-consistent but differently parameterized sequence policy is
rejected instead of silently changing the review floor. The policy fingerprint
and regenerated Phase 16 manifest changed; risk-v1 remains untouched.

Before considering an operating point, obtain a versioned source with stable
customer/recipient identity and currency, event and arrival clocks, transaction
facts known before each decision, independently verified labels with availability
times, and actual trusted-profile admission provenance. Freeze chronological
train/validation/test and held-out-customer partitions. Select thresholds on
validation only and report review volume, false positives and misses on the
untouched test period. The currently assessed ULB dataset lacks these behavioral
fields; PaySim remains a synthetic source with unresolved terms/provenance.
