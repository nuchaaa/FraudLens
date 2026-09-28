# ADR-034: Experimental sequence review floor for the controlled simulator

Status: accepted for the Phase 16 controlled simulator, 2026-09-28. Not a
production decision policy.

## Context

The deterministic E story exposed a specific risk-v1 gap. Its six small
transfers matched sequence-v1 signals, but risk-v1 returned LOW/ALLOW because
its versioned rules do not consume sequence evidence. Changing risk-v1 in place
would erase the observed failure and break replay compatibility.

## Decision

Add `risk-v2-sequence-experimental` as a separate, fingerprinted pure policy.
It consumes an exact risk-v1 rules-only result and sequence-v1 result for the
same context and transaction. Evidence version, fingerprints, signal order and
uncalibrated status must agree. A complete MATCHED sequence outcome with a
reason and no missing indicators raises a LOW or abstaining base result to at
least MEDIUM with a STEP_UP_VERIFICATION suggestion. Otherwise the policy
retains the risk-v1 level/action, or abstains when both sources are unavailable.
Incompatible evidence fails explicitly. No numeric score, probability or bank
action is manufactured. risk-v1 remains unchanged.

The offline simulator reports both policies. The authenticated admin-only,
experimental `/api/v1/experimental/demo/controlled-scenarios` endpoint computes
the same deterministic report in memory and serves it with `no-store`. The
React Scenario lab labels oracle intent and actual results separately and
shows every A–E transfer, reasons and pass/fail checks. It neither reads nor
writes PostgreSQL and cannot create analyst feedback or profile admissions.

## Consequences

A–D retain their controlled outcomes; E receives a review suggestion only
after a complete sequence signal. Its first two transfers remain LOW/ALLOW,
and the entire E risk-v1 gap remains visible. The authored thresholds and
oracle approvals are uncalibrated simulation assumptions. Passing these tests
does not establish detection quality on bank traffic, actual transaction
availability, or a production deployment. The separate live analyst walkthrough
and Phase 15 security gate remain open.
