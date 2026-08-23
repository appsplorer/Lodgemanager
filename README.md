# Quill of the Craft — Lodge Management System

Quill of the Craft is a multi-tenant Lodge-management SaaS covering the public CMS website, member/officer/candidate workflows, meetings and controlled minutes, dues/payments, multi-currency finance, documents, communications, reporting/insights, platform administration, RBAC/MFA/auditing, and an offline-continuity layer for appropriate routine work.

This repository is being implemented and verified against **Quill of the Craft Master Software Requirements Specification & Acceptance Standard v1.0 (23 Aug 2026)**. Requirements and runtime acceptance status are tracked in `docs/IMPLEMENTATION_STATUS.md` and the `qa/requirements_traceability.*` artifacts.

## Fastest local start on Windows

1. Start Docker Desktop.
2. Extract/clone this project and open the repository root in PyCharm.
3. Open the PyCharm Terminal (PowerShell).
4. Run:

```powershell
Copy-Item .env.local.example .env.local
powershell -ExecutionPolicy Bypass -File .\scripts\local-up.ps1
```

Then open:

- Quill of the Craft: http://localhost:3000
- API health: http://localhost:8000/api/health/
- Mailpit: http://localhost:8025

Local demo login:

```text
admin@lodgeflow.local
QuillCraftLocal123!
```

These credentials are deliberately **local-only**. Never reuse the local environment file or password on a server.

## Run the local QA gate

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-qa.ps1
```

The Docker-backed gate checks Compose configuration, Django, migration drift, PostgreSQL-backed Django integration tests, frontend syntax/type safety and a real Next.js production build.

## Full instructions

- `docs/LOCAL_PYCHARM_DOCKER_QA.md` — Windows/PyCharm/Docker setup and QA workflow.
- `docs/OFFLINE_AND_PERFORMANCE.md` — PWA/offline storage, queued writes, reconnect synchronization and safety boundaries.
- `docs/PRODUCTION_DEPLOYMENT.md` — production deployment preparation.
- `docs/IMPLEMENTATION_STATUS.md` — current source implementation and remaining runtime acceptance gates.

## Important security boundary

Quill of the Craft intentionally does **not** queue high-risk operations offline. Payment/provider actions, billing, MFA, credentials, impersonation, approvals, file uploads, minutes transitions and other sensitive operations require an active server connection. Routine queueable mutations use idempotency and optimistic conflict checks during reconnect.

## Repository structure

```text
backend/                  Django API, business rules, services, migrations, tests
frontend/                 Next.js UI, CMS/marketing UI, PWA/offline client
qa/                       Requirements traceability and release assertions
frontend/e2e/             Playwright + accessibility browser suites
docs/                     QA, admin/operator, DR and production guides
scripts/                  Local helpers, QA, backup/restore/deploy/monitoring
.github/workflows/ci.yml   PostgreSQL/frontend/security/Docker-E2E CI gates
docker-compose.local.yml  Local Docker/PyCharm development stack
docker-compose.prod.yml   Production-oriented container stack
.env.local.example        Local-only QA configuration template
.env.production.example   Production configuration template
```

## Source-only check

```bash
./scripts/release-check.sh
```

For deployment decisions, use the Docker-backed QA/CI/UAT gates. Source-only checks are deliberately not treated as production acceptance.
