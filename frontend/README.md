# FraudLens analyst console

Phase 14 React/TypeScript/Vite console for the authenticated local API. It renders only
retained PostgreSQL facts. Experimental scores are labelled uncalibrated and
production-ineligible; missing evaluations remain explicit.

The bearer credential lives only in React memory. It is never placed in source, URLs,
localStorage or sessionStorage and disappears on refresh. This is suitable for localhost
service-credential demonstrations, not human authentication or remote deployment.

```sh
npm ci
npm run dev
```

Run the backend on `127.0.0.1:8000`; Vite proxies `/api` and `/health`. Open
`http://127.0.0.1:5173`, paste a short-lived analyst/admin credential generated using
the repository development runbook, and connect. Use synthetic data only.

Checks: `npm run lint`, `npm test`, `npm run build`.
