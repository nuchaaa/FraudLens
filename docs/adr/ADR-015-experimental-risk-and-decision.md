# ADR-015: Experimental risk composition and suggested decisions

Status: accepted, Phase 9 engineering checkpoint, 2026-09-21.

## Context

Phase 1 already supplies ML-only, rules-only and hybrid strategies plus configurable
DecisionPolicy. Phase 6 rules distinguish matches from unavailable evidence. Phase 8
supplies a verified synthetic model adapter. Compose these components without promoting
synthetic scores, replacing missing evidence with zero, or fabricating persisted metadata.

## Decision

The framework-free evaluate_risk service accepts one immutable captured FeatureContext,
a RiskPolicy and an optional FraudModel port. Existing extraction/rules and the scoped
experimental inference service consume the same captured facts. No live history lookup,
profile admission, case creation, database write or transaction status change occurs.
The report is an ExperimentalRiskResult, not the durable RiskAssessment entity.

Supported modes are rules_only, ml_only and hybrid. Rules-only never calls or requires a
model. Model modes require an explicit model and retain its actual version, feature version
and inference time. Model failures propagate; there is no fallback to rules or zero.
Native-model CLI loading retains the independently trusted manifest pin from ADR-014.
ML scope remains KZT/UTC with 180/30-day profiles. Rules-only has no nominal-amount ML
restriction and follows the captured feature/profile policy. ULB models remain incompatible.

## Versioned experimental policy

risk-v1-experimental fixes the formula, required rules, missingness behavior and reporting.
Weights and thresholds are configurable, carried in full, and included in a canonical
SHA256 fingerprint together with rule order/version and the missingness policy. Behavior
changes require a new risk version. Parameter changes require a new fingerprint.
Decision thresholds reuse decision-v1-experimental and inclusive comparisons.

The authored demonstration weights in rules-v1 order are:

| Rule | Weight |
| --- | ---: |
| AMOUNT_ANOMALY | 0.40 |
| NEW_RECIPIENT | 0.15 |
| HIGH_VELOCITY | 0.25 |
| UNUSUAL_TIME | 0.10 |
| DEVICE_CHANGED | 0.10 |

All five weights must be positive and sum to one within numeric tolerance. The complete
rule score is sum(matched weights) / sum(all weights). It is a heuristic index in [0,1],
not a probability. Amount and velocity receive larger illustrative weights to distinguish
combinations in engineering demonstrations; these choices have no empirical validation.
No benchmark/test metrics were consulted or optimized to choose this policy.

Hybrid score = model_weight * model_score + (1 - model_weight) * rule_score. Default
model_weight=0.5 gives equal illustrative influence. Hybrid requires 0 < weight < 1;
use explicit single-component modes for the endpoints. Single modes reuse the existing
projection strategies; their unused numeric operand repeats the known score internally,
while absent components remain null in reports. No artificial model metadata is created.

Threshold defaults remain 0.35/0.65/0.85: below medium means LOW/ALLOW; then MEDIUM/
STEP_UP_VERIFICATION, HIGH/HOLD_AND_REVIEW, CRITICAL/URGENT_REVIEW. These are suggested
experimental actions, never executed. Every report states production_eligible=false,
calibrated=false, operational_action_executed=false and admission_workflow_verified=false.
Neither a low score nor an ALLOW suggestion establishes legitimacy or learning permission.

## Missing evidence and alternatives

Any NOT_EVALUATED rule makes the rule score unavailable (null), even if other rules match.
Rules-only and hybrid then return INSUFFICIENT_EVIDENCE, null score/level/action, all partial
rule evidence and the ordered unavailable-rule codes. They do not renormalize onto available
rules or issue an automatic hold. Existing cases/actions do not represent abstention, so
null suggestions plus an explicit result status avoid inventing a business action.

ML-only may score inputs with missing-history features, since behavior-v1 has explicit
indicators, but reports every unavailable rule and the null rule score. This does not
validate cold-start predictive performance. Native inference remains synthetic-only.
An operational policy for missing evidence requires a separate reviewed deployment design.

Rejected: treating missing as not matched (false reassurance); renormalizing available
weights (incomparable changing denominators); silently replacing a failed model (different
policy without provenance); presenting weighted scores as calibrated probabilities.

## Replay and boundaries

Reports retain context/transaction/profile revision identity, capture source/time, exact
feature vector, complete rule evidence, policy/fingerprint and actual inference/evaluation
times. CLI also records a canonical captured-payload SHA256 and trusted manifest digest.
Digests identify bytes, not authenticity. Keep the original context and compatible code.
Scores, reasons and policy identity replay; actual inference/evaluation timestamps change.
Evaluation cannot precede capture or inference. Capture time is not database commit time.

The CLI needs no database or service credentials. Rules-only does not import ML libraries.
Model output is named uncalibrated_score in JSON; the older internal FraudPrediction field
remains probability for compatibility. The CLI exits nonzero with a sanitized message for
invalid inputs/policies/artifacts and native model failures; it emits no successful report.

## Durable evaluation design boundary

Do not insert these results into existing RiskAssessment/ModelVersion by fabricating a
profile snapshot, model identity, score or legacy trained_at. Future persistence needs an
append-only evaluation envelope representing scored and insufficient-evidence states,
nullable model provenance for rules-only, unknown legacy training time explicitly, and
actual inference/export/capture clocks separately. Any nullable training-time migration
must be reviewed with registration/eligibility rules, not inferred from filesystem times.

A future authorized evaluation use case must acquire a scoped idempotency lock before
writes and atomically retain original context, vector, complete rule/policy evidence,
model manifest identity, result, audit/outbox and exact response. Replays must return the
stored response and reject changed request bodies. Transactions remain immutable RECEIVED;
use separate append-only evaluation state. Schema changes, authenticated HTTP evaluation,
concurrency/rollback PostgreSQL tests and case/event orchestration are a separate checkpoint.

## Validation

Tests cover the three modes on identical facts, complete and partial rule evidence, cold
starts, weights/fingerprints, inclusive boundaries, stable reason ordering, artifact replay,
model failures, incompatible versions and timestamp ordering. Native bundle CLI tests
verify score parity, unavailable hybrid results, exact replay apart from clocks, corruption
rejection and database independence. No predictive-performance or adaptive-safety claim.
