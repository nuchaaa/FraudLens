# ADR-011: Deterministic rules over captured features

Status: accepted, Phase 6, 2026-09-20.

## Decision

The framework-free rules module evaluates the exact ordered behavior-v1 vector.
`ThresholdSpecification` implements the existing `FraudSpecification.evaluate` port;
its richer `outcome` method preserves missing-data information. `evaluate_context`
uses the existing production extractor, without database queries or new input facts.
No model metadata, assessment, fraud verdict, profile write or action is fabricated.

`rules-v1` fixes rule order, comparisons, availability gates and message templates.
`RulePolicy` holds experimental thresholds and has a canonical SHA256 fingerprint.
Reports retain the full policy and fingerprint, feature/rule versions, input context ID,
transaction ID and selected profile revision. Changing thresholds changes the fingerprint;
changing rule logic/order/messages requires a new rules version. These identifiers do
not authenticate artifacts; retain the original context and compatible code for replay.
The older RuleVersion value object remains the persistence metadata contract.

## Rules in stable order

All comparisons are inclusive >= and all values come from behavior-v1.

| Code | Condition | Availability gate |
| --- | --- | --- |
| AMOUNT_ANOMALY | amount / admitted long median >= 10 | Profile present and baseline sufficient |
| NEW_RECIPIENT | new_recipient = 1 | Profile present and baseline sufficient |
| HIGH_VELOCITY | prior transfers strictly within five minutes >= 5 | Raw activity available |
| UNUSUAL_TIME | unusual_hour = 1 | Profile/baseline and qualified hours available |
| DEVICE_CHANGED | device_changed = 1 | Activity and unambiguous last device available |

10x and five prior transfers are uncalibrated research defaults, configurable through
RulePolicy and the local CLI. Velocity excludes the candidate; with five prior rows,
the candidate would be the sixth transfer. Empty captured raw history produces
NOT_EVALUATED for activity-dependent rules. Missing profile, insufficient observations,
no qualified hours and tied ambiguous devices are likewise explicit NOT_EVALUATED.
These outcomes are not a clean-history verdict. Availability flags override even a
nonzero imputed feature. NOT_MATCHED only means an available predicate did not match.

Each outcome contains code, status, feature name, observed numeric value, threshold,
missing indicators and optional RiskReason. Only matches produce reasons. Messages
refer to bounded admitted/captured history, never claim a recipient is globally new,
and do not accuse a customer of fraud. The median rule avoids treating an arbitrary
MAD-floor multiplier as an independently calibrated risk threshold. Device novelty,
recipient age and other features remain available for later experiments.

No blacklist rule is implemented because there is no authoritative versioned blacklist
input. Simulated blacklist facts must be explicit captured inputs in a future contract,
not inferred from recipient identifiers. No score aggregation or automatic decision
is introduced: Phase 9 owns risk/decision integration and durable assessment design.

## Validation and boundaries

Reject unsupported feature versions, reordered names, nonbinary flags, negative values,
fractional counts and inconsistent nested velocity counts. These checks do not establish
external input truth or provenance. Prefer evaluating captured contexts rather than
hand-built vectors. All Phase 5 cutoff, currency and historical availability limitations
continue to apply. Training experiments must not recapture present-day history for past
predictions; replay previously retained facts with pinned versions.

Tests cover adjacent float amount boundaries, integer velocity boundaries, missing-data
suppression, stable reasons/order/evidence, policy fingerprints, invalid versions/policies,
artifact round-trip parity and CLI replay with deliberately invalid database settings.
All previous PostgreSQL tests remain unchanged. No schema or dependencies are added.
