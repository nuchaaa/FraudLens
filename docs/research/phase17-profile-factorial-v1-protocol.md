# Phase 17 profile factorial v1 — predeclared protocol

Status: frozen before running or interpreting this version's report. This is an
offline software-mechanism comparison on the unchanged `profile-comparison-stream-v1`
source (`fe669407b3265659ea0024ee0e183d86967d6c6ad69ec19464dc649d0264e36e`).
The first Phase 17 source, code, protocol and report remain immutable.

## Factors and controls

Cross statistic (arithmetic mean, median with MAD recorded) with update policy
(static, naive admit-every-arrival, existing conservative gate after oracle
feedback). Six cells see the same 80 assumed baseline observations and 21
candidate arrivals. Within each update policy both statistic cells use the
**same admitted observation IDs**; neither statistic selects admissions. The
gate retains its existing median-based admission criterion and experimental
10× exceptional ratio. Thus the statistic factor changes the reported
reference only, not the gate's admission behavior. This is a controlled
comparison of profile summaries, not an alternative mean-based gate.

At each decision, process only arrivals strictly before or at that decision
in arrival order, release simulated feedback strictly before the decision,
and exclude the candidate and observations with event time at or after the
candidate. Report pre-decision mean, median, MAD, count, admitted IDs and
amount/reference ratio. Use the existing 180-day long and 30-day short
windows. Record final state after releasing remaining feedback. No risk
policy, model, probability or production evaluation runs.

## Predeclared contrasts

Compare the BC reference before B and before C across all six cells, including
the ratio for C. Within each update policy, compare mean against median with
identical admissions. Within each statistic, compare static, naive and gated
updates. Compare D's first-decision and final short-window reference and
accepted count; compare E's initial and final count/reference. The hypotheses
are that the naive mean shifts strongly after B while naive median is less
sensitive, static profiles do not adapt, the gate quarantines B, accepts
feedback-supported gradual D changes and does not admit unverified E facts.
No observed value will be used to tune the gate or risk-v2.

## Sensitivity cases fixed in advance

1. `delayed_feedback`: move D's first feedback availability to **exactly**
   D's second arrival. Strict inequality means D1 is unavailable for D2;
   later decisions may use it if the gate can apply it in order.
2. `compromised_confirmation`: change only E's six simulated verdicts to
   LEGITIMATE, available two hours after each event (after the sequence).
   Keep the authored outcome `AUTHORED_UNVERIFIED`. Measure whether this
   intentionally false confirmation channel admits the small transfers.
   This is a failure-mode probe, not verified analyst evidence.
3. `out_of_order_arrival`: move B's arrival after C's arrival while preserving
   original event and feedback times. The current profile gate has no
   historical correction/replay protocol. Expect explicit rejection and
   record `UNSUPPORTED_REQUIRES_REPLAY`, with no synthetic numerical result.

Every variant has its own canonical source hash; the base source hash must
stay unchanged. Deterministic replay, candidate exclusion, exact feedback
boundary and the fail-closed disorder behavior are tested. A single authored
stream cannot establish statistical uncertainty, field representativeness,
verified fraud detection, probability calibration or safe compromised-human
recovery. Oracle labels are simulation assumptions only.
