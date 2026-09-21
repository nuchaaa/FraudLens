# ADR-018: Independently authorized safe profile learning

Status: accepted, Phase 12 checkpoint, 2026-09-21.

## Context

The profile gate has always been pure and conservative: unverified activity is
quarantined, confirmed fraud is excluded, and exceptional legitimate amounts do not
enter the normal baseline. Before Phase 12, repository callers could persist admitted
observations without durable proof that a trusted workflow authorized them. Profile
reads therefore disclosed `admission_workflow_verified=false`.

Phase 11 made evaluation and analyst feedback durable, but a verdict is evidence rather
than learning permission. Automatically admitting a transaction after one analyst marks
it legitimate would let a compromised credential or mistaken confirmation poison the
baseline. Cold start also cannot safely use the ordinary gate because no trusted median
exists. Existing observations have no weights, and append-only profile history cannot
truthfully implement correction by deleting or rewriting prior facts.

## Decision

Add an explicitly experimental, disabled-by-default profile-learning workflow under the
existing experimental configuration. Only an admin principal may authorize it. The admin
must differ from every terminal reviewer used as evidence. Every case must be closed, have
exactly one terminal verdict, remain inside customer scope and be unused by any earlier
learning decision.

Persist an immutable `profile_learning_decisions` envelope and immutable
`profile_learning_evidence` links. The evidence binds the case, terminal feedback,
reviewer and transaction. PostgreSQL validates the case is closed; identities, scope and
verdict agree; the learning actor is independent; and evidence cardinality matches the
decision kind. UPDATE, DELETE and TRUNCATE are rejected. Each successful request atomically
commits its decision/evidence, optional profile revision/observations, audit record, outbox
event and exact durable idempotent response.

### Cold start

Bootstrap requires 5–100 distinct closed legitimate cases for one customer/currency,
evaluated with an explicitly absent profile, and at least two distinct reviewers. The
admin authorizer must be independent of both. Transactions must fit the active 180-day
window. A fixed `profile-learning-v1-experimental` policy rejects a bootstrap set containing
an amount at least 10 times its median. It creates profile version 1 only when no profile
exists. These values are conservative authored policy, not calibrated thresholds or
evidence of resistance to collusion.

### Existing profiles

A legitimate ordinary update requires a previously verified profile, an evaluation
captured against exactly the current profile version, a nonhistorical transaction and the
existing pure gate's ACCEPT decision. The resulting profile advances exactly once and
records the learning decision and policy version. A legitimate exceptional amount,
insufficient/stale history, legacy unverified profile, late review or stale captured profile
version is durably QUARANTINED without changing the profile. Confirmed fraud is durably
REJECT_FROM_PROFILE without changing it.

Existing profiles are migrated as unverified rather than inventing provenance. Their
revisions retain that state. Verified profile heads/revisions must reference an immutable
matching ACCEPT learning decision; PostgreSQL checks customer, currency, policy and version.
The profile read API exposes these provenance fields.

## Deliberately unavailable behavior

`ACCEPT_WITH_LOW_WEIGHT` is not persisted. Current observations have no weight and silently
storing a low-weight decision as a full observation would be dishonest. Corrections and
retractions are also unavailable: append-only observations and revisions must not be
rewritten. A future design needs explicit weighted observation contributions and additive
superseding correction records, with replay semantics and database constraints.

One admin plus two reviewers is separation of duties, not protection from collusion or
account compromise. Production deployment still needs human identity/session security,
strong approval policy, revocation, restricted database grants and monitoring. Raw intake,
customer enrollment, model score, suggested ALLOW and evaluation success never authorize
learning.

## Consequences

Newly learned profiles can now disclose durable verified workflow provenance without
claiming that the thresholds are calibrated. Exceptional purchases preserve the normal
baseline, confirmed fraud cannot enter it, stale evaluations cannot authorize a newer
profile, repeated case evidence cannot self-reinforce, and competing writers serialize.

The feature remains experimental and production-ineligible. It does not execute fraud
actions, alter immutable RECEIVED transactions, train a model or dispatch the outbox.
Research comparison of naive and safe adaptation remains unrun. Future work should design
corrections/weights, outbox delivery and identity/security hardening before any production
claim or remote enablement.
