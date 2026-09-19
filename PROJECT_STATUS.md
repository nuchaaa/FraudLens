# FraudLens project status

Current checkpoint: **Phase 0 foundation and Phase 1 domain implemented.**
Phase 0 container/PostgreSQL runtime verification is outstanding.
Next engineering phase: **Phase 2 — Persistence**. This is not the finished product.

## Phase 0 — Repository foundation

- [x] Inspected empty workspace; created isolated repository under `outputs/fraudlens`.
- [x] Preserved full original request in `docs/PROJECT_SPECIFICATION.md`.
- [x] Python 3.13, uv lockfile, virtual environment, Ruff, strict mypy, pytest/coverage.
- [x] FastAPI liveness, environment settings and structured application logging.
- [x] PostgreSQL-only SQLAlchemy boundary and Alembic foundation revision.
- [x] Non-root Dockerfile and backend/PostgreSQL Compose with localhost-bound ports.
- [x] CI definition: lint, typing, PostgreSQL test, dependency audit and builds.
- [x] README, architecture diagrams, six ADRs and research protocol.
- [ ] Container build/start and live PostgreSQL migration verification.
- [ ] Remote GitHub Actions execution; repository has not been pushed.

## Phase 1 — Domain

- [x] Synthetic transaction/customer values, Decimal amounts and aware UTC timestamps.
- [x] Currency-specific profiles, immutable snapshots and 30/180-day robust statistics.
- [x] Feature/model/specification contracts, model and rule version values.
- [x] Assessments, explanations as reason values, risk strategies and decision policy.
- [x] Strict case lifecycle, immutable transition history, audit and feedback records.
- [x] Initial pure profile gate/admission operation: accept, quarantine, reject.
- [x] Events/outbox values, repository/UoW protocols and in-process event adapter.
- [x] Regression tests and domain dependency-boundary enforcement.

Domain work previews later phases; their production use cases are not complete.
`ACCEPT_WITH_LOW_WEIGHT` is reserved and is not applied by the initial gate.

## Tests and validation

- [x] pytest: **93 passed, 1 skipped**, 94 collected; **90%** combined coverage.
- [x] Ruff: lint clean; 78 Python files formatted.
- [x] mypy: no issues in 40 backend source files.
- [x] pip-audit: no known vulnerabilities in exported locked dependencies.
- [x] `uv build`: source archive and wheel built.
- [x] `docker compose config --quiet`: valid with supplied local test password.
- [x] `alembic upgrade head --sql`: foundation SQL generated, not executed on a DB.
- [x] Actual Uvicorn/HTTP smoke: liveness returned 200/expected JSON; process stopped.
- [ ] PostgreSQL integration test skipped: `TEST_DATABASE_URL` not set.
- [ ] Docker socket absent; `open -a Docker` could not launch the application.

No failing tests. Two upstream deprecation warnings remain: Starlette TestClient's
httpx support and AnyIO BlockingPortal alias. They are not suppressed. pip-audit
recommends hash-enforced requirements; uv installs from the hashed lockfile.
Initial missing-README packaging timing and Decimal sum type inference were fixed.

## Architecture decisions

- Domain imports only Python standard library and other domain modules.
- Risk is not a fraud verdict; analyst confirmation is separate from profile admission.
- Gate ratio 10× median, minimum history 5 and decision thresholds are uncalibrated.
- Confirmed fraud is rejected; exceptional legitimate and unverified events are quarantined.
- No fabricated model/SHAP/metrics; no SQLite substitute for PostgreSQL tests.
- Planned outbox writes are atomic; delivery is at-least-once with deduplication.

## Important files

- `backend/app/profile/entities.py`, `gate.py`: profiles and safe admission.
- `backend/app/cases/entities.py`: strict lifecycle.
- `backend/app/risk/`, `decision/`, `fraud/`, `features/`: domain contracts/policies.
- `backend/app/shared/ports.py`, `events.py`: persistence and event boundaries.
- `backend/adapters/`, `backend/main.py`, `config.py`: infrastructure and composition.
- `tests/unit/`, `tests/integration/`: implemented tests.
- `infra/migrations/`, `docker-compose.yml`, `.github/workflows/ci.yml`: infrastructure.
- `docs/adr/`, `docs/research/protocol.md`: decisions and experimental design.

## Known gaps and technical debt

- [ ] Business tables/repositories, atomic UoW, concurrency and durable idempotency.
- [ ] Transaction API, authentication/RBAC and database-enforced immutable audit.
- [ ] Production features/rules, ML training/inference/SHAP and model registry persistence.
- [ ] Full profile history, categories/devices and frequency-qualified typical hours.
- [ ] Trusted cold-start enrollment, weighted updates and correction/retraction replay.
- [ ] Resistance to compromised analyst labels or confirmed gradual poisoning.
- [ ] Application feedback workflow, outbox dispatch/retries and consumer deduplication.
- [ ] React console, full seeded demos, research experiments and model/E2E tests.
- [ ] Container images/Actions use version tags, not immutable digests/commit hashes.

## Exact next tasks

1. Read this status and preserved specification; retain tested domain behavior.
2. Make disposable PostgreSQL available; set `TEST_DATABASE_URL`; verify existing
   migration/test and Docker build/start when the runtime is available.
3. Add Phase 2 SQLAlchemy tables/migrations for customers, transactions, profiles/
   snapshots, assessments, cases/transitions, feedback, versions, audit and outbox.
4. Implement repositories and context-managed atomic UoW, profile version checks,
   uniqueness/immutable-history enforcement; plan scoped idempotency constraints.
5. Add real PostgreSQL round-trip, rollback, concurrency and constraint tests.
6. Proceed to Phase 3 API/idempotency only after persistence is tested.
7. Run checks and update all three checkpoint files before stopping.
