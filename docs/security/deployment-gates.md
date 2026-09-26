# Remote deployment gates

FraudLens remains a localhost research system. The role matrix is locally tested,
but the current Compose topology still uses one database owner credential. Do not
expose it remotely or claim production fraud-detection performance.

A separate `frontend/Dockerfile.production` now contains a candidate HTTPS edge;
the existing `frontend/Dockerfile` and Compose file remain local HTTP. The edge
requires `FRAUDLENS_PUBLIC_HOST` and read-only certificate/key files at
`/run/secrets/tls.crt` and `/run/secrets/tls.key`, and expects the backend only on
its private Docker network as `backend:8000`. Map external ports 80/443 to its
internal 8080/8443 only in a reviewed topology; do not publish backend port 8000.
The backend image ignores forwarded headers. The local nginx/TLS smoke and exact
limits are recorded in [ADR-024](../adr/ADR-024-local-https-edge-checkpoint.md).
The candidate image itself has not run because Docker Desktop cannot start here.

## Database setup for a dedicated deployment

Use a new dedicated PostgreSQL 17 database. Create four distinct login roles with
separately managed random passwords: a migrator that owns the database and a
non-public `fraudlens` schema, plus API, worker and identity-operator roles with
no membership, `SUPERUSER`, `CREATEDB`, `CREATEROLE` or `BYPASSRLS`. The
operator's credentials must not be present in the API or worker environment;
migration credentials must not be present in either runtime environment. Never
run the grants command on the existing `public` localhost demo schema. A database
administrator can start a **new** dedicated instance/database with the following
role outline; `\password` prompts interactively and no example secret is reusable:

```sql
CREATE ROLE fraudlens_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE fraudlens_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE fraudlens_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE fraudlens_operator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
\password fraudlens_migrator
\password fraudlens_api
\password fraudlens_worker
\password fraudlens_operator
CREATE DATABASE fraudlens_secure OWNER fraudlens_migrator;
```

Connect to that new database as `fraudlens_migrator` and run
`CREATE SCHEMA fraudlens;`. These names are examples; check for collisions and
review network authentication/host access separately. Do not grant runtime roles
membership in the migrator or other roles.

As migrator, point `FRAUDLENS_DATABASE_URL` at that database with
`options=-csearch_path%3Dfraudlens`, then run `alembic upgrade head`. Still as
migrator, apply the reviewed grants:

```sh
.venv/bin/python -m backend.adapters.database.grants \
  --schema fraudlens \
  --api-role fraudlens_api \
  --worker-role fraudlens_worker \
  --operator-role fraudlens_operator
```

Supply the four actual role names; this command neither creates roles nor reads
their passwords. It is atomic, fails on unknown tables/extra effective privileges,
and revokes PUBLIC CONNECT/TEMP on the dedicated database. Reapply and verify
after every schema migration. Configure the API, outbox worker and identity CLI
with their *own* credential and the same schema search path. Set
`FRAUDLENS_ENVIRONMENT=production` so each process verifies its role on startup.
This is a deployment procedure, not a command to run on the current demo database.

## Controls still requiring deployed verification

- Verify the candidate HTTPS edge on the actual hostname, certificate, container
  network and production database roles. The local self-signed smoke verified
  Origin, Host, Secure cookies, HSTS/CSP and sanitized forwarded headers, but did
  not exercise the deployed topology. Do not place another proxy in front without
  a new trust and client-IP design.
- Load-test edge request size, concurrency, timeout and rate limits before Argon2
  work within an agreed resource budget. The authored local 413/429 smoke is not
  a capacity test. Current nginx timeouts are idle intervals, not total deadlines;
  design and verify an end-to-end request deadline. PostgreSQL login throttles
  remain a second layer.
- Store and rotate database passwords, API service credentials and TLS keys through
  operational secret management. Verify backup/restore, account/session revocation,
  monitoring and incident response without changing immutable evidence.
- Implement [phishing-resistant MFA and independently verified recovery](mfa-and-recovery-requirements.md)
  for human analysts and admins before remote access. The local getpass CLI has
  neither identity verification nor MFA; no email reset route exists.
- Obtain an independent security assessment, run the real Docker topology and remote
  CI, and validate fraud performance on suitable point-in-time behavioral data.

Any failed gate keeps the application local and experimental. Suggested fraud
actions are never executed; raw intake, enrollment and feedback do not authorize
profile learning.
