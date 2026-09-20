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

Only `/health/live` and development API documentation are exposed. Persistence is
implemented behind ports but transaction submission and risk evaluation routes
are not yet implemented. No model is trained or loaded.
