# ADR-017: Durable experimental evaluations and analyst review

Status: accepted, Phase 11 experimental checkpoint, 2026-09-21.

## Context

Phases 5–10 can capture behavior-v1 facts, evaluate deterministic rules, run a
reviewed synthetic native model, compose an experimental risk result and explain
that model offline. None of those reports was durable or available through HTTP.
The existing `risk_assessments` schema cannot honestly represent rules-only results,
an absent profile, or the Phase 7 legacy model whose exact training time is unknown.
Filling its required model/profile provenance would fabricate evidence.

Analyst case and feedback entities already existed, but their original persistence
was tied to `risk_assessments`. Phase 11 needs a truthful durable envelope before a
case can refer to an evaluation. It also needs exact retry behavior, scoped access,
append-only review history and one transaction for every business result and its
audit/outbox/idempotency evidence.

## Decision

Add a separate, explicitly experimental evaluation path. It is disabled unless
`FRAUDLENS_EXPERIMENTAL_ENABLED=true`; reads still require normal authentication and
customer scope. `POST /api/v1/experimental/evaluations` accepts a transaction ID,
an explicit profile version or explicit absence, a fixed risk strategy and, for
model strategies, an independently trusted manifest SHA256. It never accepts caller
scores, feature vectors, policy documents, model files or explanations.

The application captures facts and evaluates them inside the same PostgreSQL unit of
work. One commit stores the canonical context, ordered vector, rules/policy, optional
native-model provenance and explanation, experimental result, actor, audit record,
outbox event and exact successful HTTP response. The envelope is either `SCORED` with
a finite score and suggested decision fields, or `INSUFFICIENT_EVIDENCE` with null
score, level and action. Every result states `production_eligible=false` and
`operational_action_executed=false`. A rules-only result has null model provenance.
Model modes preserve the trusted manifest document and digest; unknown `trained_at`
remains null.

Reuse scoped durable idempotency. Authorization is checked before replay. The
transaction-scoped advisory lock is acquired before business writes. The same
principal/key/request returns the exact stored response across process restarts;
a changed request returns conflict. A stored evaluation is never recomputed on GET,
so late-arriving raw transactions or a removed model configuration cannot alter it.

Add cases that reference experimental evaluations separately from legacy fraud cases.
Only analyst/admin principals may create and review them, and customer scope is still
enforced through the evaluation. The lifecycle remains OPEN -> UNDER_REVIEW ->
LEGITIMATE or CONFIRMED_FRAUD -> CLOSED. `NEEDS_INVESTIGATION` records feedback while
remaining under review. Optimistic versions and row locks reject concurrent changes.
Terminal feedback is transactionally bound to the matching actor and transition.

Four new tables are append-only: `experimental_evaluations`, `evaluation_cases`,
`evaluation_case_transitions` and `evaluation_feedback`. PostgreSQL triggers reject
UPDATE, DELETE and TRUNCATE; validate evaluation-envelope identity and score/null
semantics; serialize transitions; and enforce feedback/terminal-transition provenance.
Migration `0005_experimental_reviews` is additive. The existing legacy assessment,
case and feedback tables remain unchanged.

## Trust and learning boundary

An analyst verdict is evidence for future policy work, not an instruction to mutate a
profile, retrain a model or execute a suggested action. Phase 11 writes no profile
observation, changes no transaction status, dispatches no outbox event and performs no
operational fraud action. The outbox row only records a durable event for a future
dispatcher. Raw intake and customer enrollment still establish no legitimacy.

Native inference accepts only the configured reviewed bundle and independently pinned
manifest digest. There is no upload endpoint and no pickle/joblib load in serving.
Rules-only remains usable without a model. ML-only and hybrid fail explicitly when a
trusted configured model is unavailable or incompatible; they never silently fall back.

## Consequences

The exact original facts and result can now be inspected and reviewed after restart,
and insufficient evidence is a durable first-class outcome. Replay is deterministic
because it reads stored bytes rather than querying current history. Database constraints
provide a second line of defense against malformed envelopes and mutable review history.

This is still an experimental research workflow. Thresholds and weights are uncalibrated,
the available native model is synthetic-only and production-ineligible, and current
event-time capture cannot reconstruct facts that were historically available unless the
original context was retained. There is no human login, production authorization model,
model registry, outbox dispatcher, action executor or adaptive-profile admission workflow.
Phase 12 must design a separately authorized feedback-to-gate process, trusted bootstrap,
correction/retraction semantics and resistance to compromised confirmations before any
profile learning is permitted.
