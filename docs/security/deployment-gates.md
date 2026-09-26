# Remote deployment gates

FraudLens remains a localhost research system. The role matrix is locally tested,
but the current Compose topology still uses one database owner credential. Do not
expose it remotely or claim production fraud-detection performance.

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

- Put the browser and API behind a reviewed HTTPS same-origin reverse proxy.
  Configure only trusted proxy addresses; reject caller-supplied Host and forwarded
  identity/IP values. Verify exact Origin, Secure `__Host-` cookies, HSTS and CSP
  on the real hostname and TLS termination path.
- Apply edge request size, concurrency, timeout and rate limits before Argon2 work.
  Test them under load within an agreed resource budget. PostgreSQL login throttles
  remain a second layer, not a perimeter.
- Store and rotate database passwords, API service credentials and TLS keys through
  operational secret management. Verify backup/restore, account/session revocation,
  monitoring and incident response without changing immutable evidence.
- Require independently verified recovery and multifactor authentication for human
  analysts and admins before remote access. The local getpass CLI has neither
  identity verification nor MFA. Admin recovery needs a second authorized operator
  and an auditable out-of-band record; no email reset route exists.
- Obtain an independent security assessment, run the real Docker topology and remote
  CI, and validate fraud performance on suitable point-in-time behavioral data.

Any failed gate keeps the application local and experimental. Suggested fraud
actions are never executed; raw intake, enrollment and feedback do not authorize
profile learning.
