# FraudLens local analyst console

This React/TypeScript/Vite console reads scoped synthetic facts from the local FastAPI backend. It displays retained experimental evaluations and cases, profile history and the admin-only, read-only Scenario lab. Risk results are uncalibrated and production-ineligible. A missing evaluation remains **NOT EVALUATED**; an insufficient result remains **INSUFFICIENT EVIDENCE**.

The console uses locally provisioned human accounts and short-lived PostgreSQL-backed sessions. Access/refresh cookies are HttpOnly; the CSRF value stays in the tab's memory. Password plus WebAuthn is available to local analysts with enrolled keys. Production human login is deliberately disabled pending the security gates in [`docs/security/deployment-gates.md`](../docs/security/deployment-gates.md). The console is for loopback use only.

From the repository root, follow [`development.md`](../development.md#phase-15-local-human-sessions-completed-local-checkpoint) to start PostgreSQL, apply migrations, provision a synthetic account and start the API. Then, from `frontend/`:

```sh
npm ci
npm run dev -- --port 5173
```

Open `http://127.0.0.1:5173` and sign in with the locally provisioned account. Vite proxies `/api` and `/health` to `127.0.0.1:8000`. An admin account can view Scenario lab; it does not write labels, evaluations or profile observations to PostgreSQL and does not run ML. See [`data/synthetic/README.md`](../data/synthetic/README.md).

Checks:

```sh
npm run lint
npm test
npm run build
```
