# ADR-025: Fail-closed remote human authentication gate

Status: accepted for a Phase 15 security checkpoint, 2026-09-27. ADR-026 later
adds local WebAuthn first-factor ceremonies; verified recovery and the full factor
lifecycle are still unimplemented. This ADR is not deployment approval.

## Context

ADR-021's password and opaque-session flow is a local research console. The
candidate HTTPS edge in ADR-024 can protect transport, but it does not add an
independent authenticator or verify account recovery. Previously, setting
`FRAUDLENS_ENVIRONMENT=production` with `FRAUDLENS_HUMAN_AUTH_ENABLED=true`
still allowed a password-only session. The operator CLI accepted a caller-asserted
UUID and could change a password in a dedicated schema when misconfigured as a
development process.

## Decision implemented now

FastAPI application construction rejects **all** production configurations with
human authentication enabled. The production API can still start with human auth
disabled and its restricted database role, but browser login, refresh and session
routes have no identity service and cannot issue or accept a human session. The
local/test HTTPS cookie and Host checks remain available for engineering tests.
The operator CLI rejects production mode before opening the database. It also
rejects a non-public runtime schema where its login lacks schema CREATE, even if
its environment is incorrectly set to development. The existing local owner-run
CLI and disposable test-schema workflow remain available. This is defense in
depth, not a claim that a database owner is unable to bypass application policy.

Tests cover rejection of production human auth, the production CLI, the
misconfigured dedicated-schema CLI, a positive local HTTPS cookie workflow and
the real four-role PostgreSQL boundary. This gate must remain until the complete
ceremonies and independent recovery process below are implemented and assessed.

## Proposed completion protocol (partly implemented locally under ADR-026)

1. Use a reviewed WebAuthn server verifier and explicit HTTPS origin/RP ID from
   deployment configuration. Keep credential public keys, credential IDs,
   counters and lifecycle in PostgreSQL. Require user presence and user
   verification. Never store a private authenticator key.
2. After password verification, issue a random, short-lived login challenge in
   PostgreSQL bound to the account ID, authorization version, ceremony, RP ID and
   origin. The password step issues no business session. The assertion step
   atomically consumes the challenge, locks the account and credential, validates
   current policy and signature/counter, writes an audit event and issues a
   session. A second use or concurrent assertion cannot create another session.
3. Enrollment and removal need a current session, fresh password and assertion
   from an existing factor. Admin factor changes additionally need an independent
   authenticated operator approval. Define a supervised first-factor bootstrap
   before enabling remote accounts. Factor changes increment authorization
   version and revoke existing sessions. Test multiple factors and lost devices.
4. Recovery needs two distinct authenticated authorized operators who are not
   the subject, a recorded institutional out-of-band identity check, a bounded
   proof lifetime and a case ID. Freeze access during the process, revoke all
   sessions and affected credentials, and require fresh factor enrollment before
   business login. Keep immutable approval/audit records and independent notice.
   The existing `--operator-id` CLI cannot supply these assurances.
5. Exercise PostgreSQL replay/race/rollback tests, browser ceremonies at the
   actual origin, restricted-role grants, backup/restore and an independent
   security assessment before removing this fail-closed gate.

The [WebAuthn specification](https://www.w3.org/TR/webauthn-3/) defines the
origin/RP and ceremony checks. [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)
describes phishing-resistant authenticators; neither source alone validates
this proposed implementation. The binding and recovery requirements are in
`docs/security/mfa-and-recovery-requirements.md`.
