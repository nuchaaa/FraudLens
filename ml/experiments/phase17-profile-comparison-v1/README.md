# Phase 17 four-strategy profiling comparison v1

This is the first **offline synthetic mechanism comparison** under the frozen
[protocol](../../../docs/research/phase17-profile-comparison-v1-protocol.md).
Reproduce the report from the repository root:

```sh
.venv/bin/python -m ml.src.evaluation.profile_comparison
```

The command prints canonical JSON. `--output NEW_PATH` writes only to a new
file. The committed [report](report.json) replays byte-for-byte in tests.

| Frozen artifact | SHA-256 |
| --- | --- |
| Canonical stream source (inside report) | `fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e` |
| `profile_comparison.py` at this checkpoint | `79f1f98ac0134f9d27c17148eba180d8c68ab3f4e4addad733be4542754157b4` |
| `uv.lock` | `203c920ffd360ddfd0428320ccf534f03db5e7f9a7e87929e43b7ce1d2261f6b` |
| Committed JSON report | `940d74a09a591016ab93d3180c03097deb3016c2369fa4d85fb97f1f5dc3bda8` |

The source has four customers, 20 initial oracle-approved observations each,
and 21 candidates: A (1), B (1), C (1), D (12), E (6). All four strategies
evaluate the same candidate and clocks before their own update. At C's
decision, B's simulated legitimate feedback is still unavailable.

| Strategy | BC reference before B | BC reference before C | 500k/reference at C | D short median before first → final | E observations before first → final |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean, static | 29,150 | 29,150 | 17.152659 | 30,000 → unavailable | 20 → 20 |
| Median/MAD, static | 29,000 | 29,000 | 17.241379 | 30,000 → unavailable | 20 → 20 |
| Mean, admit every arrival | 29,150 | 408,714.285714… | 1.223348 | 30,000 → 79,999.5 | 20 → 26 |
| Median, gated after available oracle feedback | 29,000 | 29,000 | 17.241379 | 30,000 → 79,999.5 | 20 → 20 |

The naive mean shifts before C because it admits the 8M payment immediately;
the gated median stays at 29k. The pure gate accepts A and twelve D events,
quarantines the exceptional confirmed B payment, and rejects C after its
simulated fraud feedback becomes available. E has no feedback, so the gated
profile admits none of its six transfers. Static short windows become
unavailable at the final cutoff because their initial observations age out;
that is not an error or a zero-risk signal.

These are **measured values on one authored stream**, not precision, recall,
fraud probabilities, evidence that the authored outcomes were true, or estimates
of bank behavior. Strategy choice mixes statistic and update policy; it does
not isolate their causal effects. The baseline's oracle approval, delayed
feedback and all transaction intents are assumptions. There is no ML model,
threshold search, train/validation/test split or database write. The current
gate does not solve compromised confirmations, historical corrections,
low-weight admission or remote analyst identity. External behavioral validation
and production calibration remain open.
