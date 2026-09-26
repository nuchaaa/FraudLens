# ADR-022: Supplemental sequence evidence without model-contract drift

Status: accepted as an experimental detector-design checkpoint, 2026-09-26.

## Context

`behavior-v1` has five/ten/sixty-minute transaction counts, but a fraudster can keep
each transfer below a customer's median, spread activity over hours and gradually
increase amounts. A per-transaction amount anomaly can therefore remain false while
cumulative exposure becomes meaningful. Changing the frozen 29-feature order would
invalidate the reviewed native model and its parity evidence. Adding an arbitrary
score weight would imply calibration that has not occurred.

The current data has customer, recipient, device identifier and transaction event
time. It has no authoritative IP, geolocation, login/beneficiary lifecycle, merchant,
shared-device ownership, sanctions or cross-customer graph facts. Those signals must
not be inferred from UUIDs or invented for a richer-looking architecture.

## Decision

Add a separate pure `sequence-v1-experimental` engine over the already captured,
strictly prior, same-customer/same-currency `FeatureContext`. Candidate-inclusive
evidence is deterministic and replayable. It requires a profile created by the
verified learning workflow, at least five admitted baseline observations and prior
raw activity. Missing or unverified facts produce `NOT_EVALUATED`, never a clean result.

Four stable signals are retained in every new experimental evaluation:

| Code | Authored experimental predicate |
| --- | --- |
| `CUMULATIVE_LOW_VALUE_SEQUENCE` | Latest four transfers are each no greater than the trusted median and together total at least 2× median within 24 hours |
| `GRADUAL_AMOUNT_ESCALATION` | Latest four strictly increase, last/first is at least 2× and cumulative amount is at least 2× median |
| `REPEATED_NEW_RECIPIENT` | At least three transfers within 24 hours to the candidate recipient, which is absent from the trusted admitted profile |
| `CUMULATIVE_AMOUNT_EXPOSURE` | At least three transfers within 24 hours total at least 5× the trusted median |

The lower window boundary and candidate instant follow the existing strict context
contract; the engine adds the candidate only after selecting prior rows. Evidence
records counts, exact Decimal amount/ratio, missing indicators, full policy and its
canonical SHA256. Thresholds are explicitly uncalibrated.

Sequence evidence is additive to the `experimental-evaluation-v1` response and exact
durable replay. It is excluded from `risk-v1-experimental` scoring, levels and suggested
actions. That avoids silently changing historical semantics or presenting an authored
weight as measured performance. A future `risk-v2` requires a frozen dataset protocol,
validation-only selection, burden/false-positive measurement and explicit migration.

The console now distinguishes `INSUFFICIENT EVIDENCE` from no evaluation and displays
matched rule/sequence reasons from their actual nested reason contracts. Older retained
evaluations have no sequence field and remain readable.

## Layered detector direction

The intended architecture is staged evidence, not one classifier:

1. immutable transaction and point-in-time context capture;
2. robust admitted behavioral baseline and raw velocity;
3. deterministic transaction rules and sequence signals;
4. optional supervised model on its exact compatible feature contract;
5. future anomaly adapter trained without candidate/future leakage;
6. future graph/device/location adapters only after authoritative versioned inputs exist;
7. versioned risk aggregation, decision policy, explanation and human review;
8. separately authorized profile learning and offline retraining.

Each layer must expose availability, version, evidence and provenance. Anomaly and graph
scores are signals rather than fraud verdicts. Customer confirmation is future evidence,
not automatic profile admission or online model retraining.

## Consequences

The low-and-slow example is detectable as explicit sequence evidence even when the
single-amount rule does not match. Existing `behavior-v1`, rules-v1, model artifacts,
scores and stored evaluations are unchanged. The engine can replay saved contexts from
the CLI without a database.

The 24-hour capture currently depends on the existing bounded 180-day raw context and
cannot establish bank-wide completeness or historical database knowledge. The signals
do not detect an attacker who perfectly imitates normal amount, timing, recipient and
device patterns. No graph, anomaly model, location, IP intelligence, real-time action,
calibration or production claim is added.

Rejected: mutating behavior-v1 in place, scoring incomplete subsets, arbitrary graph
edges from identifiers, treating anomaly as fraud, and automatically learning from a
matched or unmatched sequence.
