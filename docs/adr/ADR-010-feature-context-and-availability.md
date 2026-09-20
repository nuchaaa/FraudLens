# ADR-010: Shared features and captured input availability

Status: accepted for Phase 5, 2026-09-20.

## Decision

`backend/app/features/engine.py` is the single pure training/inference transformation.
`extract_many` calls `extract_features`, preserving dataset row order. The ordered
29-name `FEATURE_NAMES` tuple and version `behavior-v1` are a model input contract.
Changing order, formulas, cutoffs, imputation or policy requires a new feature version.
Inputs are immutable `FeatureContext` facts; the output contains finite floats.
Source money remains Decimal, including artifact strings; extraction uses precision
38 and half-even rounding independently of ambient Decimal settings.

## Baseline features

Baseline observations come only from the explicitly selected profile revision, never
raw intake. Roll its windows to candidate event time and exclude both interval ends.
The candidate ID may not already appear in that revision. Profiles must match customer
and currency and cannot have a revision head later than the candidate. The revision
pins timezone and window policy (normally 30/180 days).

- `amount`: native-currency candidate amount; future models need currency-aware preprocessing.
- `profile_missing`, `baseline_insufficient`, `long_history_count`, `short_history_count`:
  distinguish absent, empty and fewer-than-five admitted observations.
- `amount_vs_customer_median`, `amount_vs_customer_mean`, `amount_vs_p95`: amount divided
  by the respective long-window statistic, zero-imputed when insufficient.
- `robust_amount_deviation`: absolute amount-minus-median divided by max(MAD, 0.01).
  `mad_zero` and `mad_floor_applied` disclose zero/sub-cent MAD. This is finite feature
  scaling, not a calibrated anomaly score or probability.
- `short_term_vs_long_term_amount_ratio`: short/long median ratio, requiring five
  observations in each window; otherwise zero with `short_baseline_insufficient=1`.
- `new_recipient`: absent from admitted long-window recipients, masked to zero when
  baseline history is insufficient.
- `unusual_hour`, `hour_deviation`, `typical_hours_missing`: local-hour membership and
  nearest circular hour distance. Typical hours require at least two observations and
  10% of long history, plus five baseline observations; missing values are zero-imputed.

The fixed descriptive policy is profile-read-v1 (5 observations, 2 per hour, 10% share).
These thresholds and the MAD floor are uncalibrated. Repository admission is not proof
of analyst legitimacy: `admission_workflow_verified=false` remains explicit.

## Raw activity features

One repository SELECT reads the same customer's same-currency transactions strictly
inside (candidate time - 180 days, candidate time), excluding candidate UUID. Ordering
is event time then UUID. More than 10,000 rows raises an explicit error using limit+1;
never silently truncate. Existing indexes suffice; no schema migration is needed.

- `transactions_last_5_min`, `transactions_last_10_min`, `transactions_last_hour` and
  `recipient_transactions_last_hour`: counts, with strict lower and upper cutoffs.
- `activity_history_count`, `activity_history_missing`: bounded raw history availability.
- `recipient_observed_age_days`, `recipient_activity_missing`: age of earliest matching
  raw transaction in that window. This is not recipient account age or lifetime tenure.
- `device_changed`, `device_change_missing`: compare the last observed device; conflicting
  devices tied at the last timestamp yield missing, not arbitrary UUID-based ordering.
- `device_not_seen_before`: absence in available raw history; zero when history is missing.
- `days_since_last_transfer`: fractional elapsed days since last raw transaction; zero
  when history is missing. Counts of zero mean no rows in the captured database scope,
  not proof of complete external bank history.

No raw activity enters profiles. IDs, labels, transaction status and future outcomes
are not numeric features. Histories from different currencies never mix.

## Availability, replay and authorization

`FeatureService.capture` enforces existing principal/customer scopes and requires an
explicit profile version or an assertion that no profile currently exists. A revision
selected today is not proof it was available at a historical decision. The service
captures immutable profile facts plus one statement's raw history; it does not claim
a global multi-query MVCC snapshot. Captured-at is application capture time, not an
invented database commit time. Late arrivals can change a new capture at the same event
cutoff. Only an artifact retained before a decision can reproduce its original inputs.

Offline code consumes those same contexts and extractor. `declared_offline` records a
caller's source assertion; dataset chronology, labels, split isolation and external
availability evidence still need validation. No knowledge-at reconstruction exists.

The local CLI authenticates capture through configured expiring service credentials;
replay uses only a local file and needs no database. Artifact envelope schema 1 contains
strictly validated typed facts, feature version and SHA256 payload digest, with a 16 MiB
limit. Decimal values survive JSON exactly. Files are created without overwriting an
existing path. The checksum detects corruption, not authenticity or malicious editing;
artifacts contain customer/transaction facts and require appropriate local access.
The infrastructure adapter uses [Pydantic TypeAdapter](https://docs.pydantic.dev/latest/api/type_adapter/)
for strict serialization/validation; the domain remains framework-free.

This phase does not create durable assessment records. Future evaluation must persist
context, vector, versions and assessment atomically before promising decision replay.
No feature HTTP endpoint, rule result, trained model, risk score or admission workflow
is introduced. Transactions remain immutable RECEIVED records.

## Verification

Exact feature values/order, missing histories, finite MAD handling, boundaries, currency,
future/candidate exclusion, device ties, decimal context independence, artifact validation,
authorized PostgreSQL capture, old revision stability and late-arrival replay are tested.
Batch and single extraction match exactly. These are software checks, not research metrics.
