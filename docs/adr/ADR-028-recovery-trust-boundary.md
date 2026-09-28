# ADR-028: Recovery trust boundary before execution

Status: accepted as a **policy-only** Phase 15 checkpoint, 2026-09-27. No remote
recovery, admin factor change or bootstrap is enabled by this decision.

## Context

Local WebAuthn factors now protect analyst sign-in and self-management. The local
operator CLI accepts an asserted UUID and can change a password; that UUID is
not authentication and cannot approve remote identity changes. No institutional
out-of-band identity-verification process, independent notice channel, remote
admin authenticator bootstrap, or reviewed production TLS/role deployment has
been supplied. Accepting a case number or a second typed UUID as approval would
turn recovery into an MFA bypass.

## Decision

`backend/app/identity/recovery.py` defines a pure, non-executing validator for a
bounded case and exactly two approval *claims*. It requires a frozen subject at
the pinned authorization version, a proof digest and reference with at most a
15-minute lifetime, two distinct active admin actors who are not the subject,
separate session families, credentials and assertion challenges, approvals no
older than five minutes, and exact case/subject/purpose/proof/**action** binding.
The policy checks each operator against a supplied current account snapshot:
the operator must still be enabled, an admin and at the authorization version
that approved the action. Approval-carried role/active flags are not trusted.
The policy rejects absent, extra, stale, reused or mismatched claims. The constants are conservative
engineering limits, not institutional policy or NIST conformance.

These dataclasses do **not** prove that a human, assertion or out-of-band identity
check occurred. `subject.active=False` alone does not prove the account was frozen
for this recovery case; a future durable case/account binding must establish that.
They are not accepted from an HTTP request or the local CLI, and
there is no recovery execution path. Production human auth remains disabled.

Before a workflow may call this validator as part of an atomic PostgreSQL unit of
work, it must:

1. Establish an institutional proof process, authorized proof issuer and
   independently verified notice destination. Bind a unique case/reference to
   its subject, purpose and digest. Never store raw identity documents in the
   fraud database or treat a caller-supplied reference as verified proof.
2. Bootstrap remote admin factors under a separately reviewed, supervised
   procedure. Authenticate each admin using a current account/session, fresh
   password and fresh WebAuthn assertion over the **same** case/action digest.
   Define and version canonical action serialization, including the target
   credential for removals, before any live approval path is connected.
   Neither admin may be the subject or act twice. Admin factor changes need
   independent approval too.
3. Fetch current operator accounts under the reviewed transaction locks; never
   accept caller-provided role/active/version values as authority. Persist case
   state and immutable approvals with uniqueness constraints and
   database locks. Freeze the subject before proof verification, increment
   authorization version and revoke sessions. Only after both verified approvals
   revoke affected factors and permit password rotation/new-factor enrollment.
   A new factor must precede
   business access. Record and independently deliver notice; a failed notice
   must not silently complete recovery.
4. Test concurrent approval, expiry at commit, replay, disabled actors/subject,
   proof withdrawal, audit/notice failure and rollback under PostgreSQL runtime
   grants. Review retention and an incident path for compromised operators.

No role grant, migration, endpoint or CLI command is introduced by this ADR.
The current public-schema demo and owner credentials are not a recovery trust
root. This checkpoint narrows the policy contract but does not clear any remote
deployment gate.
