# External Production Acceptance Checklist

This checklist is generated from the final requirements baseline. Local source, unit, Django/SQLite, typecheck and build results are useful implementation evidence, but they do not replace these production-like gates.

Required scope: **293 requirements** (258 MUST, 35 SHOULD).

Production acceptance remains blocked until every gate below is executed against the exact release ZIP and its evidence is archived.

## GEN — Deployed product smoke and tenant isolation

Covers 9 MUST and 1 SHOULD requirements: `GEN-001`, `GEN-002`, `GEN-003`, `GEN-004`, `GEN-005`, `GEN-006`, `GEN-007`, `GEN-008`, `GEN-009`, `GEN-010`.

Prerequisites: Docker, PostgreSQL, Redis, S3, SMTP, ClamAV and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test)
```

Exit criteria: All three product layers persist real data; cross-tenant negative cases and core journeys pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## ARC — Production architecture and service topology

Covers 10 MUST and 0 SHOULD requirements: `ARC-001`, `ARC-002`, `ARC-003`, `ARC-004`, `ARC-005`, `ARC-006`, `ARC-007`, `ARC-008`, `ARC-009`, `ARC-010`.

Prerequisites: Docker Compose v2 and staging secrets.

Run:

```bash
docker compose --env-file .env.staging -f docker-compose.prod.yml -f docker-compose.staging.yml config && ./scripts/staging-e2e.sh
```

Exit criteria: Only intended ingress is exposed; migration/readiness ordering and all stateful dependencies pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## IAM — Identity, MFA and session security

Covers 9 MUST and 1 SHOULD requirements: `IAM-001`, `IAM-002`, `IAM-003`, `IAM-004`, `IAM-005`, `IAM-006`, `IAM-007`, `IAM-008`, `IAM-009`, `IAM-010`.

Prerequisites: PostgreSQL, Redis and real browser.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)
```

Exit criteria: Invitation/reset expiry and replay, MFA enrolment, timeouts, suspension and tenant switching pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## RBAC — Tenant and platform role matrix

Covers 7 MUST and 1 SHOULD requirements: `RBAC-001`, `RBAC-002`, `RBAC-003`, `RBAC-004`, `RBAC-005`, `RBAC-006`, `RBAC-007`, `RBAC-008`.

Prerequisites: Seeded staging role accounts and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)
```

Exit criteria: Every allowed and denied API/UI action matches the approved role matrix; dual control passes.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## CMS — Public website, CMS, SEO and lead capture

Covers 12 MUST and 1 SHOULD requirements: `CMS-001`, `CMS-002`, `CMS-003`, `CMS-004`, `CMS-005`, `CMS-006`, `CMS-007`, `CMS-008`, `CMS-009`, `CMS-010`, `CMS-011`, `CMS-012`, `CMS-013`.

Prerequisites: Staging public hostname, SMTP and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Publishing, revisions, redirects, SEO, forms, consent and responsive public journeys pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## PAD — Platform operator console

Covers 9 MUST and 1 SHOULD requirements: `PAD-001`, `PAD-002`, `PAD-003`, `PAD-004`, `PAD-005`, `PAD-006`, `PAD-007`, `PAD-008`, `PAD-009`, `PAD-010`.

Prerequisites: Platform role accounts with MFA.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)
```

Exit criteria: Tenant, user, feature, credential, billing, logs and impersonation actions obey platform permissions.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## TAD — Tenant administration and configuration

Covers 9 MUST and 0 SHOULD requirements: `TAD-001`, `TAD-002`, `TAD-003`, `TAD-004`, `TAD-005`, `TAD-006`, `TAD-007`, `TAD-008`, `TAD-009`.

Prerequisites: Owner/admin staging accounts.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Branding, locale, timezone, finance, security, custom fields/stages and user settings persist and validate.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DASH — Dashboard, navigation and global search

Covers 6 MUST and 1 SHOULD requirements: `DASH-001`, `DASH-002`, `DASH-003`, `DASH-004`, `DASH-005`, `DASH-006`, `DASH-007`.

Prerequisites: Representative staging dataset and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: KPIs reconcile to persisted data and search/navigation remain tenant- and permission-scoped.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## MEM — Member CRM and lifecycle

Covers 9 MUST and 1 SHOULD requirements: `MEM-001`, `MEM-002`, `MEM-003`, `MEM-004`, `MEM-005`, `MEM-006`, `MEM-007`, `MEM-008`, `MEM-009`, `MEM-010`.

Prerequisites: Representative member fixtures.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: CRUD, duplicate override, archive/anonymize, activity, custom fields and statements pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## OFF — Officer terms and governance

Covers 4 MUST and 1 SHOULD requirements: `OFF-001`, `OFF-002`, `OFF-003`, `OFF-004`, `OFF-005`.

Prerequisites: Representative officer fixtures.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Role definitions, overlapping terms, succession, history and roster output pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## CAN — Candidate, mentor and milestone workflows

Covers 7 MUST and 1 SHOULD requirements: `CAN-001`, `CAN-002`, `CAN-003`, `CAN-004`, `CAN-005`, `CAN-006`, `CAN-007`, `CAN-008`.

Prerequisites: Candidate/mentor role fixtures.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Pipeline, scoped mentor access, tasks, stage history, milestones and progress output pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## MTG — Meeting governance workflows

Covers 8 MUST and 1 SHOULD requirements: `MTG-001`, `MTG-002`, `MTG-003`, `MTG-004`, `MTG-005`, `MTG-006`, `MTG-007`, `MTG-008`, `MTG-009`.

Prerequisites: Meeting fixtures, PostgreSQL and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Recurrence, agenda, attendance, visitors, minutes locks/reopen and generated packs pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## FIN — Finance, dues, payments and receipts

Covers 11 MUST and 1 SHOULD requirements: `FIN-001`, `FIN-002`, `FIN-003`, `FIN-004`, `FIN-005`, `FIN-006`, `FIN-007`, `FIN-008`, `FIN-009`, `FIN-010`, `FIN-011`, `FIN-012`.

Prerequisites: PostgreSQL concurrency plus representative finance fixtures.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: Proration, assessment idempotency, unique receipts, allocation, reversal, approvals and exports reconcile.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DOC — Documents, templates and secure media

Covers 8 MUST and 0 SHOULD requirements: `DOC-001`, `DOC-002`, `DOC-003`, `DOC-004`, `DOC-005`, `DOC-006`, `DOC-007`, `DOC-008`.

Prerequisites: Private S3-compatible storage and required ClamAV.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: MIME/signature/size/scan controls, ACL downloads, templates, previews and generated files pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## COM — Communications and delivery

Covers 7 MUST and 1 SHOULD requirements: `COM-001`, `COM-002`, `COM-003`, `COM-004`, `COM-005`, `COM-006`, `COM-007`, `COM-008`.

Prerequisites: SMTP sandbox/Mailpit and Celery worker.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: Consent, segmentation, preview, scheduling, idempotent delivery, retry and delivery logs pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## REP — Report catalogue, analytics and scheduling

Covers 10 MUST and 2 SHOULD requirements: `REP-001`, `REP-002`, `REP-003`, `REP-004`, `REP-005`, `REP-006`, `REP-007`, `REP-008`, `REP-009`, `REP-010`, `REP-011`, `REP-012`.

Prerequisites: PostgreSQL, Celery/Beat, SMTP and browser runtime.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Every Appendix C report reconciles, filters, exports, saves, schedules and enforces permissions.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## RPTFMT — Professional report format acceptance

Covers 9 MUST and 1 SHOULD requirements: `RPTFMT-001`, `RPTFMT-002`, `RPTFMT-003`, `RPTFMT-004`, `RPTFMT-005`, `RPTFMT-006`, `RPTFMT-007`, `RPTFMT-008`, `RPTFMT-009`, `RPTFMT-010`.

Prerequisites: LibreOffice/PDF renderer, SMTP and representative data.

Run:

```bash
./scripts/staging-e2e.sh && python scripts/generate-pdf-samples.py
```

Exit criteria: PDF/XLSX/CSV are searchable, formula-safe, branded, paginated, private and visually approved.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## AUD — Audit, compliance and sensitive export controls

Covers 6 MUST and 2 SHOULD requirements: `AUD-001`, `AUD-002`, `AUD-003`, `AUD-004`, `AUD-005`, `AUD-006`, `AUD-007`, `AUD-008`.

Prerequisites: PostgreSQL and separate requester/approver/operator accounts.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: Append-only chain, redaction, filters, dual control, impersonation and evidence hashes pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## PAY — Payment-provider sandbox reconciliation

Covers 10 MUST and 1 SHOULD requirements: `PAY-001`, `PAY-002`, `PAY-003`, `PAY-004`, `PAY-005`, `PAY-006`, `PAY-007`, `PAY-008`, `PAY-009`, `PAY-010`, `PAY-011`.

Prerequisites: Real Stripe, PayMongo and Xendit sandbox credentials for enabled providers.

Run:

```bash
gh workflow run staging-acceptance.yml
```

Exit criteria: Staging passes and recorded provider-originated callbacks prove signature, tenant/mode/amount/currency binding, duplicate replay, quarantine and subscription flows.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## PWA — Offline/PWA continuity and conflicts

Covers 7 MUST and 1 SHOULD requirements: `PWA-001`, `PWA-002`, `PWA-003`, `PWA-004`, `PWA-005`, `PWA-006`, `PWA-007`, `PWA-008`.

Prerequisites: Chromium browser with online/offline control.

Run:

```bash
(cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Install/update, safe read cache, queued safe mutations, conflicts and blocked high-risk actions pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DATA — Imports, bulk operations and saved views

Covers 5 MUST and 2 SHOULD requirements: `DATA-001`, `DATA-002`, `DATA-003`, `DATA-004`, `DATA-005`, `DATA-006`, `DATA-007`.

Prerequisites: Large representative import files and PostgreSQL.

Run:

```bash
./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Preview/commit atomicity, duplicate/error reporting, bounded bulk actions, search and saved views pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## JOB — Background jobs and schedules

Covers 5 MUST and 1 SHOULD requirements: `JOB-001`, `JOB-002`, `JOB-003`, `JOB-004`, `JOB-005`, `JOB-006`.

Prerequisites: Redis, Celery worker and Beat running.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: Async imports/reports/campaigns expose progress, retry safely, deduplicate and recover from transient failure.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## API — API and webhook contract acceptance

Covers 8 MUST and 1 SHOULD requirements: `API-001`, `API-002`, `API-003`, `API-004`, `API-005`, `API-006`, `API-007`, `API-008`, `API-009`.

Prerequisites: Staging services and provider sandboxes.

Run:

```bash
./scripts/staging-e2e.sh && python scripts/generate-openapi.py && python -m unittest qa.test_openapi_contract
```

Exit criteria: Runtime routes match OpenAPI; pagination/errors/idempotency and signed webhook replay pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## SEC — Application security acceptance

Covers 9 MUST and 1 SHOULD requirements: `SEC-001`, `SEC-002`, `SEC-003`, `SEC-004`, `SEC-005`, `SEC-006`, `SEC-007`, `SEC-008`, `SEC-009`, `SEC-010`.

Prerequisites: Production-like TLS proxy plus dependency/container and DAST scanners.

Run:

```bash
pip-audit -r backend/requirements.txt && (cd frontend && npm audit --audit-level=high) && trivy image --severity HIGH,CRITICAL --ignore-unfixed lodgeflow-backend:release && trivy image --severity HIGH,CRITICAL --ignore-unfixed lodgeflow-frontend:release
```

Exit criteria: Tenant/RBAC negatives, CSRF/CSP/headers, rate limits, upload attacks and scans have no open High/Critical defects.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## PRIV — Privacy, retention and integrity

Covers 7 MUST and 0 SHOULD requirements: `PRIV-001`, `PRIV-002`, `PRIV-003`, `PRIV-004`, `PRIV-005`, `PRIV-006`, `PRIV-007`.

Prerequisites: PostgreSQL copy with aged test records and separate approver roles.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: Export/anonymize/retention jobs preserve protected records, produce audit evidence and respect legal holds.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## UX — Responsive accessibility and design acceptance

Covers 7 MUST and 3 SHOULD requirements: `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-005`, `UX-006`, `UX-007`, `UX-008`, `UX-009`, `UX-010`.

Prerequisites: Desktop/tablet/mobile browsers and axe.

Run:

```bash
(cd frontend && npx playwright test e2e/core.spec.ts)
```

Exit criteria: Keyboard, focus, contrast, reduced motion, zoom, empty/error/loading states and breakpoints pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## PERF — Reference load and availability targets

Covers 3 MUST and 4 SHOULD requirements: `PERF-001`, `PERF-002`, `PERF-003`, `PERF-004`, `PERF-005`, `PERF-006`, `PERF-007`.

Prerequisites: Production-sized staging dataset and monitoring.

Run:

```bash
LOAD_BASE_URL=https://staging.example.test LOAD_TEST_USERNAME=... LOAD_TEST_PASSWORD=... LOAD_LODGE_ID=... python scripts/load-test.py
```

Exit criteria: Documented p95/error/LCP/throughput targets pass without tenant leakage or job starvation.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## OBS — Observability and operational monitoring

Covers 4 MUST and 2 SHOULD requirements: `OBS-001`, `OBS-002`, `OBS-003`, `OBS-004`, `OBS-005`, `OBS-006`.

Prerequisites: Log/metric sink and alert receiver.

Run:

```bash
./scripts/staging-e2e.sh && PUBLIC_BASE_URL=https://staging.example.test ALERT_WEBHOOK_URL=... python scripts/ops-monitor.py
```

Exit criteria: Structured redacted logs, request IDs, health/readiness, backup age, disk/TLS and alert delivery pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DR — Encrypted backup and disaster recovery

Covers 7 MUST and 1 SHOULD requirements: `DR-001`, `DR-002`, `DR-003`, `DR-004`, `DR-005`, `DR-006`, `DR-007`, `DR-008`.

Prerequisites: Isolated Docker recovery host and off-site backup destination.

Run:

```bash
./scripts/verify-backup-restore.sh
```

Exit criteria: A fresh encrypted backup restores database and private storage; checksums, sentinel, RPO/RTO and readiness pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DEV — Build, deployment and rollback

Covers 10 MUST and 0 SHOULD requirements: `DEV-001`, `DEV-002`, `DEV-003`, `DEV-004`, `DEV-005`, `DEV-006`, `DEV-007`, `DEV-008`, `DEV-009`, `DEV-010`.

Prerequisites: Clean staging host, immutable image registry and rollback image.

Run:

```bash
./scripts/deploy-production.sh
```

Exit criteria: Lock-resolved builds, migrations, non-root health, secret injection, rollout and rollback rehearsal pass.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## QA — Full automated QA and traceability

Covers 10 MUST and 1 SHOULD requirements: `QA-001`, `QA-002`, `QA-003`, `QA-004`, `QA-005`, `QA-006`, `QA-007`, `QA-008`, `QA-009`, `QA-010`, `QA-011`.

Prerequisites: All service dependencies and browsers.

Run:

```bash
./scripts/release-check.sh && (cd frontend && npx playwright test)
```

Exit criteria: Unit/integration/E2E/security/accessibility suites pass and exact artifact evidence maps every MUST/SHOULD.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## UAT — Staging UAT and production acceptance

Covers 7 MUST and 0 SHOULD requirements: `UAT-001`, `UAT-002`, `UAT-003`, `UAT-004`, `UAT-005`, `UAT-006`, `UAT-007`.

Prerequisites: Named business, security and operations approvers.

Run:

```bash
./scripts/staging-e2e.sh
```

Exit criteria: All scripted UAT journeys pass; no P0/P1 defects; formal business/security/operations sign-offs recorded.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.

## DEL — Final package and release sign-off

Covers 9 MUST and 0 SHOULD requirements: `DEL-001`, `DEL-002`, `DEL-003`, `DEL-004`, `DEL-005`, `DEL-006`, `DEL-007`, `DEL-008`, `DEL-009`.

Prerequisites: Exact release ZIP, scan reports and acceptance evidence.

Run:

```bash
./scripts/release-check.sh
```

Exit criteria: Checksum, source, migrations, docs, samples, SBOM, licenses, known risks and signed traceability are archived.

Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.
