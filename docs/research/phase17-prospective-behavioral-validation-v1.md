# Phase 17 prospective behavioral validation protocol v1

Status: **frozen protocol, study not started**. This document specifies decisions
before access to any independently permitted behavioral source. It does not
approve a dataset, authenticate a manifest, prescribe a live bank action, or
make a performance claim. The current ULB `ulb-pca-v1` benchmark and authored
Phase 16/17 fixtures cannot qualify as behavioral validation. Predictive
validation remains OPEN.

## Research questions and units

The primary question is whether a conservative, evidence-gated adaptive
customer profile better resists exceptional purchases and attempted poisoning
than naive admission, while still adapting to independently confirmed ordinary
change. A paired factorial comparison crosses profile statistic (arithmetic
mean versus median/MAD) with update policy (static, naive, gated). Use the same
eligible customers, candidate transactions, knowledge cutoffs, labels, and
partitions for every cell. Report profile displacement, delayed adaptation,
quarantine and review burden separately from fraud-detection outcomes. A later
rules/ML comparison may use the same frozen partitions, but cannot turn profile
statistics into predictive validation on their own.

The observation is one uniquely identified transaction decision for one stable
pseudonymous customer and currency. Record a separate versioned recipient and
device identity where the source supports them. A person, account, household,
merchant and transaction must not be conflated. No cross-customer aggregation
may reconstruct a held-out identity. The data owner must document identity
stability, rotations, merges, reassignments and currency units before a split is
frozen; unresolved continuity is a block, not an inferred identifier.

## Gate 0: permission, privacy and custody

The data owner supplies an independently verifiable written agreement naming
the controller/owner, permitted research purpose, lawful basis or consent
authority as applicable, data fields, accessors, processing location, onward
transfer, publication/redistribution limits, retention and deletion dates, and
incident procedure. An institutional privacy/legal reviewer signs the authority
and a data steward signs source lineage and extraction scope. A dataset-card
license alone does not grant permission to process private records. No source
rows or raw identities enter Git, chat, issue trackers or public artifacts.

The owner generates stable pseudonyms in its controlled environment and keeps
the mapping key separately. Export only fields needed for the registered
questions; redact free text and unnecessary direct identifiers. Document
access logs, encryption in transit/at rest, least-privilege users, location,
retention and deletion evidence. Cross-owner joins and public enrichment need
separate written authority. If the owner cannot show the authority and custody
controls, stop before copying or opening rows. Independent sign-off cannot be
replaced by a self-attested JSON `DOCUMENTED` value.

## Gate 1: source and clock lineage

Freeze a source/version identifier and cryptographic hash of the exact received
bytes. The owner supplies a field dictionary, units, clock precision/timezone,
extract query/version and immutable provenance for at least:

- stable pseudonymous customer, recipient and device identities; amount and
  currency; transaction ID; event time and first durable ingestion/arrival time;
  original decision time and decision/source-system identity;
- independent outcome definition, value, evidence source, adjudicator identity
  or process, feedback creation and **availability** time, plus later correction
  and revocation time and reason category if one exists;
- every trusted profile-admission decision, authorized actor/process, underlying
  evidence, policy/version, record creation and availability time, supersession
  link, and the original profile snapshot/version used at each decision.

An event timestamp is not ingestion time. A feedback timestamp is not proof its
content was available to the decision-maker. The owner must document if a
clock was reconstructed, rounded, overwritten, or inferred. Unrecoverable
availability, unknown timezones, insufficient minute-level precision for
velocity, or invented all-null revocation columns block the relevant
behavior-v1 analysis. A documented absence of revocations needs an audited
source process able to distinguish none from missing records. The source must
provide raw, point-in-time transaction activity separately from trusted
admissions. Intake, enrollment, a model suggestion and a final retrospective
label never establish prior legitimacy.

## Gate 2: row-level rejection and point-in-time replay

Run a read-only checker in the owner's approved environment before examining
model outcomes. Retain source row IDs and reason counts for every rejection;
never silently repair rows. For a candidate with event `e`, arrival `a`,
decision `d`, and unique transaction ID, require valid absolute instants,
`e <= d` and `a <= d`. Later-arriving earlier-event rows remain in the source
but cannot appear in the original decision context. Duplicate IDs with
conflicting facts, impossible orders, identity/currency ambiguity, nonfinite or
invalid amounts, unverified units, and missing required clocks are rejected
from the primary analysis. Identical duplicate deliveries need documented
deduplication identity and a first-arrival record. Reject the candidate itself
and any event at the strict window boundaries from its own history.

For each candidate, raw context includes only same-customer/currency prior
facts with `event < e` and `arrival < d`, within the versioned feature windows
and explicit row cap. Trusted context additionally requires an independently
authorized admission with `admission_available_at < d`, a prior admissible
transaction, and no revocation **available before** `d`. A confirmation made
after `d` cannot be used to build that decision's baseline even when it describes
an older purchase. All feature fitting, imputation, reference medians, model
parameters, and profile updates must be computed from the knowledge set
available at their respective decisions. Preserve the exact original snapshot
and replay its hash; a corrected later view is a separate append-only artifact
linked to the original, never a rewritten historical prediction. If snapshot
availability cannot be reconstructed, stop the original-decision replay and
label it `UNVERIFIABLE_CHRONOLOGY`.

An outcome label is usable for *final evaluation* only if the independent
adjudication process and `label_available_at` are verified. A label available
after a decision may score that decision retrospectively but cannot influence
its features, previous admissions, training chronology, or threshold choice
before its availability. Corrections and revocations available before a later
decision change only that later knowledge set. If availability or independence
is unknown, mark outcome `UNKNOWN`; never use a current case status as if it
were known historically. Report exclusions and missingness by source, time
period, customer and class where disclosure permits. If exclusions bias the
estimand, narrow the claim or stop rather than hide them.

## Split and label freeze

Before outcome inspection, a source-specific signed addendum must set the
observation start/end, event and decision-time precision, `T_train < T_val <
T_test_end`, an outcome ascertainment cutoff `T_label_freeze`, maturation
window, customer holdout assignment, review-capacity budget, versioned feature
and policy candidates, and minimum support needed for each proposed claim.
These values are **unassigned here** because no eligible source exists; do not
substitute convenient defaults after seeing labels. Hash the addendum before
calculating split counts or metrics.

Use disjoint decision-time periods `[start,T_train)`, `[T_train,T_val)` and
`[T_val,T_test_end)`. Freeze customer assignment by a documented deterministic
hash of stable pseudonym, study salt held by the owner, and declared cohort
rule before outcome inspection. Hold out an entire customer cohort from all
fitting and threshold selection; report its test performance separately from
the later-time test of previously seen customers. Never let the same customer
cross the customer holdout, even through account rotation. A held-out customer's
earlier raw facts may establish a *causally available* cold-start/personal
history for that customer's test decision, but its labels or admissions cannot
be fitted retrospectively and no held-out customer contributes to global
training statistics. If the real source cannot support both chronological and
customer-disjoint claims, report separate narrower estimands; do not call a
row-level random split a held-out-customer test.

Only labels with verified `label_available_at <= T_label_freeze` and a completed
predeclared maturation window enter the final outcome denominator. Report
unresolved/censored decisions, late confirmations, and revocations separately;
never assume no label means legitimate. The same ascertainment rule applies to
all study arms. Training at any training cutoff may use only labels available
by that cutoff; validation selection may use validation labels only after their
verified availability and before the frozen test opening. If `T_label_freeze`
cannot be set without peeking at test labels, stop.

## Locked analysis and single final test

Before fitting, freeze source/extraction, inclusion code, deduplication, all
feature/policy versions, split membership, random seeds and package lockfile.
Train-only preprocessing includes scalers, imputers, class weighting or any
resampling. Never fit on validation/test features or labels, including global
profile medians. The planned fixed model families, if the signed addendum
confirms enough data and governance authority, are logistic regression,
random forest and XGBoost; rules-only and predeclared profile-strategy cells
remain explicit comparators. If any family is unsupported, record that before
seeing validation results. No model trained on synthetic data or ULB PCA rows
is silently promoted into this comparison.

Use training folds respecting decision time and customer grouping for model
hyperparameters. On the validation period alone, select a model by average
precision among eligible candidates, with a predeclared deterministic tie
rule. Select one operating threshold that maximizes validation recall subject
to the data owner's **predeclared** review-capacity ceiling and any safety
constraint in the signed addendum; tie-break by higher precision, then higher
threshold. If no threshold satisfies the constraints, report no selected
operating point. Freeze model bytes/hash, feature order, policy fingerprint and
threshold before a single final-test invocation. Any subsequent tuning makes
that test exploratory and requires a new untouched source/cohort for a new
confirmatory test. Do not reuse the ULB final test, Phase 16 A–E cases or seven
sequence challenges for model/threshold selection.

Report exact confusion counts and class prevalence, precision, recall, F1,
false-positive rate, AP/PR-AUC, ROC-AUC where defined, and reviews per eligible
transaction and per time unit at the selected threshold. Show false positives
and missed cases, including by customer and currency where privacy permits;
include abstentions and unavailable evidence in the denominator accounting.
For profiling, report paired per-customer baseline displacement after verified
exceptional purchases, time to adapt after independently confirmed drift,
unverified-admission contamination, legitimate quarantine and workload. Show
normal versus compromised/revoked-confirmation strata only when provenance
supports them. Report uncertainty with customer-clustered intervals and temporal
sensitivity checks where justified; specify resampling seed/replicates in the
signed addendum. If there are too few independent customers, positives or
time periods for an interval or metric, write `NOT_ESTIMABLE` and its denominator
instead of a fabricated estimate. No test-set retuning, post-hoc threshold
optimization or production claim follows from favorable numbers.

## Evidence package, review and stop decisions

Preserve an access-restricted, append-only package containing signed authority
and data-use scope, source/extraction hash, field dictionary, clock/identity and
trusted-admission lineage, row rejection log and counts, split/addendum hash,
pre-decision context hashes, label/correction ledger, code commit, dependency
lockfile, seeds, training/validation selection trace, frozen model/threshold
hashes, one final-test invocation record, denominators, uncertainty method and
deletion/retention proof. Publish only an independently cleared aggregate
summary; hashes establish integrity, not authenticity or permission.

The data steward and an independent privacy/legal reviewer must sign Gate 0;
an independent chronology/label reviewer must sign Gates 1–2 and split
feasibility; a separate methodological reviewer must verify the frozen analysis
and final-test seal. Record reviewer identity, role, decision, time and any
conflict; a project author cannot self-sign the independent gates. Do not begin
model work if any gate is missing, contradicted or revoked. Stop or downgrade to
an explicitly narrower descriptive study for unavailable clocks, unverifiable
identity or admissions, overlapping holdout customers, leakage, insufficient
label maturation/support, uncontrolled test access, permission withdrawal or
unresolved privacy/security findings. A source-specific deviation requires a
new versioned addendum with the prior version retained; post-test changes are
exploratory and cannot repair the original confirmatory claim.

As of this freeze, **no independently permitted behavioral dataset or signed
addendum exists in the repository**. Acquisition gaps are owner permission,
privacy authority, row-level clocks and labels, identity continuity, trusted
admission lineage, feasible split/support, and independent review. This protocol
does not authorize accessing any bank data, training, threshold calibration,
live profile admission, or remote deployment. Phase 15 security remains a
separate fail-closed release gate, and the optional live analyst walkthrough
remains parked pending actual reviewer evidence.
