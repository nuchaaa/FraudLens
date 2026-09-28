# Phase 17 profiling comparison v1 — frozen offline protocol

Status: predeclared synthetic mechanism experiment. This protocol is frozen
before interpreting the generated report. It is not an ML training protocol,
fraud-detection benchmark, threshold-selection set or field validation.

## Question and source

On one identical synthetic stream, how do static and adaptive amount profiles
respond to an exceptional legitimate payment, a later suspicious transfer,
confirmed gradual change and unverified repeated transfers?

The source generator version is `profile-comparison-stream-v1`, implemented in
`ml/src/evaluation/profile_comparison.py`. It uses stable UUIDv5 IDs, fixed UTC
timestamps, KZT only and no random-number generator. Four synthetic customers
start with 20 oracle-approved observations each: 22k, 31k, 28k, 35k, 26k,
33k and 29k KZT repeated by index, dated 40 through 21 days before the anchor
of 2026-10-01 09:00 UTC. These assumed approvals are **not** analyst verdicts
or verified bank history. The script records the canonical stream SHA-256 in
the report; any source change requires a new generator version and report.
The frozen canonical source SHA-256 for this checkpoint is
`fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`.

The new candidate stream is:

| Customer/story | Event facts | Arrival | Authored feedback availability |
| --- | --- | --- | --- |
| A ordinary | 25k KZT at anchor | event +2 minutes | LEGITIMATE at event +1 hour |
| BC outlier | 8M KZT at anchor +1 day | event +5 minutes | LEGITIMATE at event +3 days |
| BC later suspicious | 500k KZT at anchor +2 days | event +1 minute | CONFIRMED_FRAUD at event +7 days |
| D gradual | 12 known-recipient transfers from 45k to 115k KZT, two days apart from anchor +1 day | event +3 minutes | LEGITIMATE at event +6 hours |
| E unverified sequence | six 25k KZT new-recipient transfers, 10 minutes apart from anchor +1 day | event +1 minute | none |

Feedback is a simulated oracle release, independent of the four strategies and
never inserted into PostgreSQL. In particular, BC's 500k decision precedes
availability of the 8M payment's legitimacy assertion. E never receives a
verdict. The authored fraud/legitimate intents are scenario descriptions, not
measured ground truth or threshold-derived labels.

## Strategies and clock rules

All four strategies see the same arrivals in `(arrival_at, transaction_id)`
order and the same baseline. Every candidate is evaluated **before** its own
admission. Profile observations require both prior event time and prior
availability; feedback released exactly at a decision instant is unavailable
until after that decision. No strategy can see future candidate facts or labels.
Use a 180-day observation window and record pre-decision count, mean, median,
MAD and amount/reference ratio for each strategy and candidate.

1. `mean_static`: initial baseline only; reference is arithmetic mean.
2. `median_mad_static`: same initial baseline only; reference is median and
   MAD is reported, not used as an invented probability.
3. `naive_adaptive`: reference is arithmetic mean; admit **every** arrived
   candidate after its decision, regardless of verdict. This intentionally
   demonstrates contamination risk and is not a recommended policy.
4. `gated_adaptive`: reference is robust median; after a simulated verdict
   becomes available, apply the existing pure `ProfileUpdateGate` with its
   unchanged experimental defaults. No feedback means no admission. The
   gate's `ACCEPT`, `QUARANTINE` and `REJECT_FROM_PROFILE` outcomes are recorded.

Each strategy receives only its own prior admissions. This is a comparison of
four *combinations* of statistic and update policy; it does not independently
identify the causal effect of either factor. Neither rules, ML nor risk-v2 runs.
If late feedback would require applying an event older than a later admitted
profile head, fail rather than silently rewrite history; such correction is
outside this first fixture.

## Predeclared diagnostics

Report the pre-decision BC 500k reference and amount/reference ratio; the
post-feedback profile shift after the 8M payment; the pre-first versus
post-last D mean/median and accepted count; E's admitted count and final
mean/median shift; and counts of gate actions. Compare values across the four
strategies without treating any profile reference as a fraud score. The main
software hypotheses are: naive mean admits the 8M amount and changes BC's
reference before C; the gated profile does not admit an exceptional confirmed
payment; the gated profile gradually changes after available legitimate D
feedback; and E remains unadmitted by the gate without feedback.

No model is trained and no train/validation/test split or predictive metric is
claimed. A later external study needs accepted point-in-time data, verified
labels with availability times, frozen chronological/held-out-customer splits
and separate calibration. Do not choose thresholds from this authored stream.
