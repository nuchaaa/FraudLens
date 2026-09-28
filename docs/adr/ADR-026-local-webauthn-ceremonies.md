# ADR-026: Local WebAuthn ceremony checkpoint

Status: accepted for local research only, 2026-09-27. Production human
authentication remains disabled by ADR-025.

## Decision

An analyst can enroll a first WebAuthn authenticator while holding a current local
session and proving knowledge of the current password. Admin enrollment is denied.
The browser creates the private key; FraudLens stores only the credential ID,
public key, counter and lifecycle metadata. Enrollment increments the account
authorization version and revokes every existing session. Subsequent login requires
both the password and a verified assertion; the password step creates no session.

Migration `0009_human_webauthn` stores credentials and 32-byte challenges in
PostgreSQL. A challenge is bound to account, ceremony, authorization version,
RP ID and exact Origin, expires in two minutes and is consumed in the transaction
that verifies the response and creates the session. Invalid registration/assertion
attempts against a valid challenge consume it and append a denial audit. Row locks
serialize concurrent uses. User presence, user verification, signature and sign
counter are checked by the pinned `webauthn` verifier. Private keys and authenticator
responses are never written to audit events. The React console uses the browser
WebAuthn API and HttpOnly cookies; it does not persist tokens in browser storage.

The restricted production API role may read credential presence to reject password
login for enrolled accounts. It has no grants to create/consume challenges or
register/update factors. The production human-auth gate still rejects startup with
human auth enabled. The current localhost public-schema demo can exercise these
ceremonies using its owner connection; that arrangement is not a deployment model.

## Remaining gates

First-factor enrollment is a local bootstrap, not independently approved identity
proof. ADR-027 subsequently adds local analyst additional-factor management and
lazy expired-challenge pruning. Admin factor approval, two-operator verified
recovery, supervised remote bootstrap and independent notice remain absent.
The local HTTP browser flow has not been exercised with a physical authenticator;
PostgreSQL integration uses generated software credentials. Exact remote hostname,
HTTPS browser ceremony, restricted-role MFA workflow, deployed four-role topology,
backup/recovery and independent security assessment remain unverified. Do not
remove ADR-025's production gate based on this checkpoint.
