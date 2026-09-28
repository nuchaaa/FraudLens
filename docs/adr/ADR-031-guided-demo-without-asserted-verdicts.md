# ADR-031: Guided local demo without asserted verdicts

Status: accepted Phase 16 presentation checkpoint, 2026-09-27. The behavioral
outcomes remain unverified until actual independent local review inputs exist.

## Context

The 62-row manifest and read-only evidence JSON are reproducible, but the JSON
is too large to walk through live. The working disposable test database has not
been seeded: the ledger reports 62 absent fixture facts and no profile revisions.
Neither an author-assigned story label nor a simulated analyst verdict can fill
that evidence gap. Phase 15 remote human access remains closed.

## Decision

`python -m backend.adapters.demo --walkthrough` applies the same Unix-socket
`*_test` and non-production guard as `--progress`, then renders the same
PostgreSQL repeatable-read, read-only snapshot. It lists only the 14 candidate
transfers (the other 48 are unreviewed background facts), grouped into A–E.
Each row displays fixture match state, retained experimental risk status and
captured profile version, case/feedback/learning counts, and a next manual step.
Each story includes its customer and current KZT profile version plus the
evidence requirement. The renderer checks the report's manifest digest and
fails on omitted candidates or customer summaries. A `CONFLICT` is a stop state
and the evidence ledger suppresses attribution from the conflicting stored row.

The walkthrough does not infer a verdict, bootstrap a profile, perform a gate
update, choose a historically available version, or execute a banking action.
It does not certify B/C preservation or D adaptation. Those claims require
stored independent review and separate authorized learning evidence, examined
against immutable revisions in event order. The authored story remains a
question for a reviewer, not ground truth.

## Consequences

Presenters get a concise, repeatable guide without adding fake analyst accounts
or automating decisions. The current unseeded database truthfully shows all
five stories as pending. Tests may create transaction/evaluation/case facts
through authorized services, but no Phase 16 test scripts an analyst verdict.
This is a demonstration workflow, not a production validation or release gate.
