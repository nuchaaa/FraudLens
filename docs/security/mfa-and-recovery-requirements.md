# Remote human-authentication requirements

Status: local analyst WebAuthn login, first/additional-factor enrollment and
different-key removal are implemented as engineering checkpoints (ADR-026/027).
Independently verified recovery, admin approvals and remote factor lifecycle
are not implemented. ADR-028 adds a non-executing, pure approval-claim policy;
it does not authenticate operators or verify institutional proof.
The local password/session flow must stay on localhost until these requirements are
implemented, tested and independently assessed. Production human auth still fails
closed under ADR-025.
ADR-025 adds a fail-closed production human-auth gate and local-operator CLI guard;
these guards do not themselves implement MFA or verified recovery.

## MFA enrollment and login

- Require an independent, phishing-resistant WebAuthn authenticator for each remote
  analyst/admin account. Bind the RP ID to the reviewed public hostname and verify
  challenge, origin, credential ID, user presence and user verification on every
  assertion. Password-only login must not issue a remote session.
- Require a current authenticated session plus fresh password and authenticator
  assertion to add or remove an authenticator. Admin enrollment/removal must also
  have an independent authorized operator approval. Revoke other sessions and
  increment the account authorization version on a factor change.
- Store public credential material and lifecycle state in PostgreSQL; never store
  private authenticator keys. Challenges must be unpredictable, short-lived,
  one-use and bound to the account and ceremony. Concurrent assertions and
  credential replacement must be tested for replay and race behavior.
- Cover lost devices and a second registered authenticator. A TOTP code alone
  would not meet the phishing-resistance target, and recovery must not silently
  downgrade to password-only access.

## Verified recovery

- The CLI's asserted `--operator-id` is not identity verification. Before remote
  use, require two distinct authenticated authorized operators, an out-of-band
  identity check using a documented institutional process, a case/reference ID
  and an immutable audit record of both approvals. Neither operator may be the
  recovering account.
- Freeze access during recovery; revoke every session and affected authenticator,
  rotate the password only after approvals, and require enrollment of a new
  authenticator before issuing a business session. Notify through an independently
  verified channel. Never send a login-capable reset link to an unverified address.
- Test denial and rollback on missing approval, same-actor approval, expired
  proof, concurrent recovery, token replay, account disablement and audit failure.
  Document how an operator is authenticated and how records are retained.

These are design gates, not claims of NIST conformance or an implemented process.
An independent reviewer must assess the final protocol and deployment. See
[NIST SP 800-63B authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)
and the [OWASP MFA guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).
