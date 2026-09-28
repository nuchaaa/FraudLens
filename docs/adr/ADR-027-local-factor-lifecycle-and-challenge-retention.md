# ADR-027: Local factor lifecycle and challenge retention

Status: accepted for a local Phase 15 engineering checkpoint, 2026-09-27.
Production human authentication remains disabled under ADR-025.

## Context

ADR-026 allowed a local analyst to enroll one WebAuthn key, but losing it left no
second authenticator. Challenges held random raw values indefinitely even after
expiry. A password-only factor change would negate the protection of the first
key. Remote admin approval and verified account recovery do not yet exist.

## Decision

Migration `0010_factor_lifecycle` adds session-family binding; additive migration
`0011_factor_removal_retention` adds the optional removal target and retention
guard to the existing challenge table. For local analysts only,
adding another key requires a current session, CSRF, fresh password and a
verified assertion from an existing key before the server issues the new
registration challenge. Removing a key requires the same proofs, but the
assertion must come from a *different* active key. The last active key cannot
be removed. Every challenge is account, authorization-version, ceremony, RP,
Origin and session-family bound, expires in two minutes, and is consumed once.
Account advisory locks serialize policy/factor changes; challenge row locks
serialize concurrent attempts. A successful factor change updates the account
authorization version, revokes all sessions, writes an audit event and commits
with the credential mutation. Invalid cryptographic attempts against valid
challenges consume them and append denial audit. The browser renders a list of
the current account's factor metadata; private keys are never stored or returned.

Expired challenge rows may be deleted only after a further one-day retention
interval. A PostgreSQL trigger denies earlier deletion and still denies TRUNCATE;
the repository prunes at most 100 old rows on each new challenge. Immutable
audit events retain ceremony start, denial and completion references after raw
challenge material is removed. This is lazy pruning, so inactive installations
may retain expired rows until the next ceremony or operator maintenance.

## Limits

This is local analyst self-management, not remotely approved factor enrollment.
Admin factor changes are denied. There is no supervised remote first-factor
bootstrap, independently authenticated dual-operator recovery, institutional
out-of-band proof, notification channel, independent review or physical-key
browser smoke. The dedicated production API role still cannot write challenges
or factors, and application construction still refuses production human auth.
The current owner-connected localhost demo is not a deployment pattern. The
software-authenticator tests prove protocol wiring and database behavior, not
formal WebAuthn conformance, hardware usability or organizational identity.

NIST's current [authenticator management guidance](https://pages.nist.gov/800-63-4/sp800-63b.html)
supports binding multiple authenticators and treats recovery as a separate
process. This design does not claim NIST conformance.
