# Phase 15 threat model

Status: local human-session, database-role and HTTPS-edge checkpoints. Human login is opt-in and locally tested. This is
an engineering threat model, not a completed security audit or deployment approval.

## Assets and boundaries

Protect account/password and session secrets, customer scope, analyst identity,
immutable review/learning evidence and idempotent responses. Actors include an
unauthenticated browser, authenticated analyst, privileged admin, machine producer,
database operator, compromised browser and compromised reviewer/admin. Local OS/DB
owners are trusted operators who can bypass application and trigger protections.

Trust boundaries: browser → same-origin proxy → HTTP authentication → framework-free
authorization/use cases → PostgreSQL; operator CLI → identity store; offline model
artifacts → independently pinned loader. Human login must not expand model trust,
customer scope or profile-admission authority.

| Threat | Required control | Verification before remote exposure |
| --- | --- | --- |
| Password guessing and resource exhaustion | Argon2id, bounded inputs, shared throttle reservations, edge concurrency/time limits | Unknown/known users, concurrent attempts, restart persistence, memory budget |
| Credential stuffing/account enumeration | Generic errors, dummy verification, no public account search/reset | Equal public response shapes; never echo secrets |
| Session theft/fixation | Fresh random values at login/rotation, hashed tokens, bounded idle/absolute lifetimes | No caller-selected identity/token; boundary expiry tests |
| Refresh replay/races | Consumed-token journal, family lock, revoke on reuse | Parallel refresh, lost response, old access denial after reuse |
| CSRF/login CSRF | Exact configured origin plus bound CSRF header; strict cookies | Missing/null/foreign origin, wrong generation, logout/review/learning requests |
| XSS/browser storage exposure | HttpOnly cookies, CSP, no HTML injection, no browser token storage | No access/refresh in JS/JSON/logs; CSP and frontend tests |
| Stale access after disable/scope reduction | Current account lookup, version bump, atomic revocation | Old session and stored idempotent replay denied |
| Identity collision or confused authentication | Separate generated human UUIDs, reject machine collisions and mixed credentials | No cookie fallback for invalid bearer; no identity from body |
| Feedback laundering into trusted profiles | Preserve independent admin and reviewer identity, scopes and gate | Existing PostgreSQL learning and review regressions with human principals |
| Authorization/revocation race | Document auth linearization; current policy before replay | In-flight boundary and subsequent-request denial |
| Host/proxy spoofing | Explicit origins/hosts and trusted proxies, verified TLS | Forged forwarded headers do not alter origin/IP trust |
| DB compromise or excessive runtime permissions | Dedicated schema and separate migrator/API/worker/operator logins; exact effective grants | Fresh database role test denies DDL, trigger changes, history mutation and account provisioning; real deployment remains unverified |
| Recovery/admin compromise | Operator-assisted verified recovery, immutable audit, revoke sessions | Reset/disable failures roll back; role changes recorded |
| Logging disclosure | Fixed errors, SecretStr/repr exclusion, no request body logging | Password/token absence from responses, exception logs and audit |

## Open release gates

- Dedicated role grants are implemented and locally verified, but the current Compose
  configuration still connects as owner. Apply and verify grants in the actual
  deployment before remote exposure; see ADR-023 and deployment-gates.md.
- The self-signed local nginx smoke verified TLS/Host/Origin/cookies/CSP, header
  replacement and basic 413/429 behavior. The candidate container edge has not run;
  actual deployment TLS, load limits and operational secret management remain open.
- External security review and implementation of the defined
  [MFA/recovery requirements](mfa-and-recovery-requirements.md) before remote exposure.
  The locked dependency audit after adding Argon2 found no known vulnerabilities.

No control here proves resistance to colluding authorized reviewers or production
fraud-detection accuracy. Models and adaptive workflows remain experimental.
