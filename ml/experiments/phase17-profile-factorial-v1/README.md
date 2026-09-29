# Phase 17 six-cell profile factorial v1

Protocol: `docs/research/phase17-profile-factorial-v1-protocol.md` was written
before calculating this report. Run with
`.venv/bin/python -m ml.src.evaluation.profile_factorial --output NEW.json`.
The CLI refuses to overwrite an existing output. The frozen first Phase 17
source and report remain unchanged.

Canonical source SHA-256:
`fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`.
This report SHA-256:
`4ce0a58640c3850f556de8d6776fa1a7bfb1a2b57e83abb40d9ef1bd25860b58`.
Report version: `profile-factorial-report-v1`. Six cells combine mean or
median/MAD with static, naive or gated updates. Within each policy, both
statistic cells use identical admitted observations.

The pre-C BC reference was 29,150 KZT for static and gated means, but
408,714.285714… KZT for the naive mean after admitting B's 8M payment. The
naive median remained 29,000 KZT with that same B admission. Hence the
first comparison had confounded robust statistic and gate effects; this
factorial shows the median itself resisted this one exceptional value.
For C's 500k amount, amount/reference was 1.223348 against the naive mean
versus 17.241379 against the naive median. These ratios are descriptive,
**not** fraud probabilities or calibrated thresholds.

Static D kept 20 long-window observations; gated and naive ended with 32
after the twelve assumed legitimate feedback releases. The gated long-window
mean rose from 29,150 to 48,218.59375 KZT and median from 29,000 to 33,000.
The final 30-day D short median was 79,999.5 KZT for adaptive policies; the
static short window had no observations by that final instant and is null.
The gate did not admit E's six unverified transfers, whereas naive admission
raised E's count from 20 to 26. These are measured behaviors of this authored
stream, not verified fraud outcomes.

Sensitivity probes used separate canonical source hashes recorded in the
report. Delaying D1 feedback to exactly D2's arrival reduces D2's gated
pre-decision observation count from 21 to 20; later feedback still yields 13
total accepted events. Falsely confirming E's six small transfers as
LEGITIMATE after the sequence increases gate ACCEPT actions from 13 to 19 and
E's final count from 20 to 26. The gate cannot verify the confirmation source;
its exceptional-amount safeguard does not prevent this assumed compromise.
Moving B's arrival after C violates per-customer event order and returns
`UNSUPPORTED_REQUIRES_REPLAY` without a numeric result. Historical correction
cannot be represented safely by this runner.

All baseline approvals and candidate verdicts here are **simulated oracle
assumptions**, never analyst evidence. One KZT-only authored stream cannot
estimate field detection, uncertainty, calibration or production safety. No
risk-v2 threshold was tuned. No database, model artifact or live profile was
changed.
