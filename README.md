# LodgeFlow — Final Local Docker / PyCharm QA Release

LodgeFlow is a multi-tenant Lodge-management SaaS covering the public CMS website, member/officer/candidate workflows, meetings and controlled minutes, dues/payments, multi-currency finance, documents, communications, reporting/insights, platform administration, RBAC/MFA/auditing, and an offline-continuity layer for appropriate routine work.

This package includes a dedicated Windows/PyCharm local Docker stack so the complete application can be evaluated before staging or production deployment.

## Fastest local start on Windows

1. Start Docker Desktop.
2. Extract this project and open the repository root in PyCharm.
3. Open the PyCharm Terminal (PowerShell).
4. Run:

```powershell
Copy-Item .env.local.example .env.local
powershell -ExecutionPolicy Bypass -File .\scripts\local-up.ps1
```

Then open:

- LodgeFlow: http://localhost:3000
- API health: http://localhost:8000/api/health/
- Mailpit: http://localhost:8025

Local demo login:

```text
admin@lodgeflow.local
LodgeFlowLocal123!
```

These credentials are deliberately **local-only**. Never reuse the local environment file or password on a server.

## Run the local QA gate

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-qa.ps1
```

The Docker-backed gate checks Compose configuration, Django, migration drift, PostgreSQL-backed Django integration tests, frontend syntax/type safety and a real Next.js production build. GitHub CI additionally builds non-root production images, runs dependency/container/secret scanning, Playwright desktop/mobile journeys with axe accessibility checks, and performs an encrypted destructive backup/restore drill.

## Full instructions

Read:

- `docs/LOCAL_PYCHARM_DOCKER_QA.md` — complete Windows/PyCharm/Docker setup and QA workflow.
- `docs/OFFLINE_AND_PERFORMANCE.md` — service-worker, encrypted offline cache, queued writes, reconnect sync and safety boundaries.
- `docs/PRODUCTION_DEPLOYMENT.md` — server deployment preparation.

## Important security boundary

LodgeFlow intentionally does **not** queue high-risk operations offline. Payment/provider actions, billing, MFA, credentials, impersonation, approvals, file uploads, minutes transitions and other sensitive operations require an active server connection. Routine queueable mutations use idempotency and optimistic conflict checks during reconnect.

## Repository structure

```text
backend/                  Django API, business rules, services, migrations, tests
frontend/                 Next.js UI, CMS/marketing UI, PWA/offline client
qa/                       Source-level release assertions
docs/                     Local QA, offline/performance and production guides
scripts/                  Local Windows/Linux helpers, QA, backup/restore/deploy
.github/workflows/ci.yml   CI gate
docker-compose.local.yml  Local Docker/PyCharm development stack
docker-compose.prod.yml   Production-oriented container stack
.env.local.example        Local-only QA configuration template
.env.production.example   Production configuration template
```

## Local dependency-backed check

Create a Python virtual environment and install the locked production/QA requirements, then run the local gate:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-qa.txt
./scripts/release-check.sh
```

This runs source/domain tests, the SQLite dependency-backed Django regression suite, migration drift checks, OpenAPI validation, a clean npm install, TypeScript checks and a real Next.js production build. For deployment decisions, the Docker/PostgreSQL/Redis/ClamAV/provider/browser gates in `docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md` remain mandatory.

- `docs/OBSERVABILITY_AND_PERFORMANCE.md` — production monitoring, alerting, reference-scale seed and 100-session load acceptance.
