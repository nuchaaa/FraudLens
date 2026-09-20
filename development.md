# Development and PostgreSQL tests

From the repository root, install dependencies with `uv sync --locked`.
The original workspace also has `../../work/bootstrap/bin/uv`; set
`UV_CACHE_DIR=../../work/uv-cache` when using that copy. Existing `.venv/bin`
executables work without a globally installed uv command.

## Current local test cluster

PostgreSQL 17.10 is installed at `/opt/homebrew/opt/postgresql@17/bin`.
The disposable cluster created for this task is at `../../work/fraudlens-postgres/data`
relative to the repository. It has database `fraudlens_test` and uses the current
macOS user's database role. It listens on a Unix socket, with no TCP listener.

If stopped, restart the existing cluster from the repository root:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl \
  -D ../../work/fraudlens-postgres/data \
  -l ../../work/fraudlens-postgres/server.log \
  -o "-h '' -k /private/tmp -p 55439 -c unix_socket_permissions=0700" -w start
```

Do not reinitialize the existing data directory. The socket uses local trust
authentication for synthetic tests only. The 0700 socket mode restricts access to
the operating-system owner. A sandboxed agent may need execution approval for
PostgreSQL shared memory and socket access; a normal local terminal does not.

```sh
export TEST_DATABASE_URL='postgresql+psycopg:///fraudlens_test?host=/private/tmp&port=55439'
export FRAUDLENS_DATABASE_URL="$TEST_DATABASE_URL"
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=backend --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

Stop this cluster when no longer needed:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D ../../work/fraudlens-postgres/data -m fast -w stop
```

## Another machine or CI

Use PostgreSQL 17 with a dedicated database whose name ends in `_test`. Set
`TEST_DATABASE_URL` with the `postgresql+psycopg` driver. The test role needs schema
creation rights because the suite creates a unique temporary schema, applies real
Alembic migrations, tests an upgrade/downgrade, then drops only that test schema.
The migration smoke test also upgrades the supplied test database's default schema.
Without `TEST_DATABASE_URL`, database tests explicitly skip; that is not database
verification. Never use a production or shared business database for these tests.

CI provisions PostgreSQL as a service. Local Docker remains optional for database
testing and has not yet been runtime-verified in this workspace.

## Current application

```sh
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1
```

`/health/live` is public process liveness. Business routes require PostgreSQL and
configured credentials. No model is trained or loaded; accepted transactions remain
RECEIVED and do not update profiles.

## Authenticated synthetic API

Configure `FRAUDLENS_DATABASE_URL` and apply migrations before sending requests.
`FRAUDLENS_API_PRINCIPALS` is a JSON array of entries with `principal_id`,
`token_sha256`, `roles`, `customer_ids` and `expires_at`. An empty registry denies all
business requests. The app refuses malformed configuration. Settings redact the
registry, and only token digests belong in configuration; never commit raw tokens.

For a local synthetic demonstration, generate a one-hour admin credential in your
own terminal (the token is printed once; keep it private):

```sh
.venv/bin/python - <<'PY'
import hashlib, json, secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4
token = secrets.token_urlsafe(32)
entry = {
    "principal_id": str(uuid4()),
    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
    "roles": ["admin"],
    "customer_ids": [],
    "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
}
print("Bearer token:", token)
print("FRAUDLENS_API_PRINCIPALS='" + json.dumps([entry]) + "'")
PY
```

Put the printed configuration assignment in your ignored `.env`, or export its value
in the server terminal, then start Uvicorn as shown above. The server reads the
registry on startup. Use `/docs` → Authorize to enter the bearer token. Production
mode disables docs; local development mode enables them.

First call `POST /api/v1/customers` with a generated synthetic UUID:

```json
{"customer_id":"00000000-0000-4000-8000-000000000001","timezone":"Asia/Almaty"}
```

Then call `POST /api/v1/transactions`, setting `Idempotency-Key: demo-transfer-1`:

```json
{
  "transaction_id": "00000000-0000-4000-8000-000000000002",
  "customer_id": "00000000-0000-4000-8000-000000000001",
  "recipient_id": "00000000-0000-4000-8000-000000000003",
  "amount": "30000.00",
  "currency": "KZT",
  "timestamp": "2026-09-20T12:00:00+05:00",
  "channel": "MOBILE",
  "device_id": "synthetic-demo-device"
}
```

Use fresh IDs for a new demonstration. Repeat the same transaction request/key to
see the original 201 body with `Idempotency-Replayed: true`. Change an amount under
that key to see 409. Retrieve the transaction using the response Location. Customer
enrollment is not idempotent replay: a duplicate customer ID returns 409.

For a producer credential, generate another random token/digest and principal,
use `roles: ["service"]`, and put only permitted customer UUIDs in `customer_ids`.
For read-only access, use `roles: ["analyst"]` and the same explicit customer scope.
Both roles are denied customer enrollment. Only admins have unrestricted customer
access. Enrolling a customer creates no trusted behavioral observations.

Rotate by replacing the digest while retaining the principal UUID and restarting
every API process. This keeps its durable idempotency namespace. Remove an entry,
reduce its scope or let it expire to deny future requests, including replay; restart
is required for configuration changes. Never reuse principal UUIDs for new identities.
Credentials are service keys, not user passwords; interactive login remains Phase 15.

HTTP behavior: missing/invalid/expired token → 401, denied submission → 403,
missing or inaccessible transaction → 404, changed key body or duplicate ID → 409,
oversized body → 413, invalid fields/key → 422, unavailable storage → 503. Maximum
business body size is 16 KiB; keys contain 1–200 printable ASCII characters without
spaces. Responses and errors use no-store caching; validation errors omit input
values. Money must be a string, not a floating-point JSON number.

Use only synthetic data and localhost for this demo. Remote deployment needs TLS,
edge time/rate limits, restricted database roles and a security review. Outbox rows
are durable but no dispatcher runs. See [ADR-008](docs/adr/ADR-008-transaction-api-and-service-credentials.md)
for authorization, atomicity and the planned immutable transaction lifecycle.
