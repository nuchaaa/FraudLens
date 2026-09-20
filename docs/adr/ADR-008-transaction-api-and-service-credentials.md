# ADR-008: authenticated intake and durable request replay

Status: accepted for Phase 3 synthetic transaction intake, 2026-09-20.

## Context

Phase 3 must accept and retrieve synthetic transactions without exposing an
unauthenticated write API. Human login/session security is scheduled for Phase 15.
Persistence already supplies atomic units of work and scoped idempotency records.
There is no evaluation pipeline or trusted profile enrollment process yet.

## Decision

Use configured, expiring opaque **service credentials**, generated with
`secrets.token_urlsafe(32)`. Configuration contains only SHA-256 token digests,
stable principal UUIDs, roles, explicit customer scopes and mandatory aware expiry
times. SHA-256 is appropriate here for random 256-bit tokens, not human passwords.
Constant-time digest comparison authenticates the token. Empty configuration
denies every business request; malformed or duplicate configuration rejects startup.
Settings redact the registry. No default deployed credential exists.

| Role | Enroll synthetic customers | Submit | Retrieve |
|---|---|---|---|
| admin | Yes | Any customer | Any customer |
| service | No | Explicit customer allowlist | Explicit customer allowlist |
| analyst | No | No | Explicit customer allowlist |

Principal IDs and roles never come from a request body. Role and scope checks also
run inside the framework-free use cases. An inaccessible transaction returns the
same 404 as a missing one. Rotation preserves a principal ID so it preserves the
idempotency namespace; configure a new random token digest and restart the process.
Removal, reduced scope or expiry prevents replay as well as new writes. Policy is
a startup snapshot; restart every process for revocation. Do not reuse a principal
UUID for a different identity. Registry size is intended for a small synthetic demo.

Routes are `POST /api/v1/transactions`, `GET /api/v1/transactions/{id}` and
admin-only `POST /api/v1/customers`. Customer enrollment creates only a customer
record and audit entry, never trusted observations. Repeated customer IDs return 409.
Transaction amounts must be JSON decimal strings; timestamps must include a timezone;
extra body fields are rejected. Business request bodies are capped at 16 KiB before
JSON parsing, including streamed bodies. Errors omit input values and SQL details.
Business responses use `Cache-Control: no-store`.

Submission requires a 1–200-character printable ASCII Idempotency-Key with no
spaces. The digest includes an operation/format version, canonical UUIDs, two-place
Decimal amounts, UTC instants and every transaction fact. Identical semantic
amounts and timestamps share a digest. Device identifiers remain case-sensitive.

The use case checks current authorization, opens one UoW and acquires the
authenticated principal/key advisory lock **before business writes**. It then:

1. Returns the exact stored JSON and status for a matching completed request, or
   rejects a changed digest with 409.
2. Verifies the customer and duplicate transaction ID.
3. Inserts transaction, authenticated audit entry, TransactionReceived outbox event
   and successful response record, then explicitly commits once.

POST returns 201 on both initial success and replay, with a stable Location and
Idempotency-Replayed header. Different keys cannot insert the same transaction ID:
the application read gives an early conflict and PostgreSQL's primary-key constraint
arbitrates races. Only the known transaction/customer uniqueness constraints map to
those domain conflicts; other database errors are not mislabeled as duplicates.
Failures leave no completed key or partial writes, permitting a retry. A commit
whose acknowledgement is lost can be recovered by retrying the same key/body.
Successful records have no expiry/purge policy yet. Failed responses are not cached.

## Lifecycle and consequences

Transactions remain immutable, including their stored RECEIVED status. Intake does
not score risk, create assessments/cases, publish events or admit profile data.
Before evaluation is exposed, introduce an explicit append-only processing lifecycle
or derive a separately named evaluation state from assessments; do not silently
rewrite historical transactions or the original stored submission response.

No database schema revision or additional dependency was needed. API tests use
actual PostgreSQL and verify authorization, durable replay across app instances,
principal scope, conflicts, rollback, concurrent same-key requests and forced
duplicate-ID insert races. Pure domain imports remain framework-free.

This is service authentication, not a completed human authentication system.
Password hashing, session/JWT lifecycle, interactive login, immediate centralized
revocation, distributed rate limiting, least-privilege database grants, credential
management and deployment review remain later work. Use localhost for the synthetic
demo; remote deployments require TLS and edge request/time/rate limits. The app's
body-size limit is not a denial-of-service defense for a public deployment.

## References

- [FastAPI security dependencies](https://fastapi.tiangolo.com/reference/security/)
- [Pydantic standard types](https://docs.pydantic.dev/latest/api/standard_library_types/)
- [Python cryptographically strong token generation](https://docs.python.org/3/library/secrets.html)
- [ADR-007 persistence boundaries](ADR-007-persistence-consistency.md)
