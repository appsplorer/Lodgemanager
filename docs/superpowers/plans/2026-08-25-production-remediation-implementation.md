# Production Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Subagents are intentionally not used in this workspace.

**Goal:** Complete every MUST and SHOULD requirement in the Quill of the Craft master requirements, preserve correct existing behavior, and produce an honestly verified production-release ZIP.

**Architecture:** Retain the Django/Next.js/PostgreSQL/Redis/Celery architecture. Add focused domain/services and additive migrations at security and workflow boundaries, complete the corresponding frontend journeys, and generate traceability from executable evidence.

**Tech Stack:** Python 3.12, Django 5.2, PostgreSQL, Redis/Celery, ReportLab/openpyxl/pypdf, Next.js 16, React 19, TypeScript 5.8, Playwright/axe, Docker Compose/Nginx.

**Spec:** `docs/superpowers/specs/2026-08-25-requirements-first-production-remediation-design.md`

## Global Constraints

- All 258 MUST and all 35 SHOULD requirements are implementation gates.
- MAY requirements are not gates unless another accepted requirement depends on them.
- Preserve existing tenant IDs/data and use additive migrations.
- PostgreSQL is the acceptance database; SQLite is not production evidence.
- No source-string assertion may be the sole evidence for runtime behavior.
- No provider/VPS/UAT check is marked PASS without real external evidence.
- Every behavior change follows red-green-refactor and uses stable requirement-aware test IDs.
- The original uploaded ZIP remains unchanged.
- The supplied source contains no Git repository; SHA-256 checkpoint manifests replace commit steps in this execution workspace.

---

### Task 1: Reproducible release and executable evidence foundation

**Files:**
- Create: `qa/test_registry.py`
- Create: `scripts/run-source-tests.py`
- Create: `scripts/generate-traceability.py`
- Create: `qa/acceptance_registry.json`
- Modify: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Modify: `backend/requirements.txt`
- Modify: `.github/workflows/ci.yml`
- Test: `qa/test_release_foundation.py`

**Interfaces:**
- Produces `@requirement_test(test_id, requirement_ids, evidence_kind)` metadata for Python runtime tests.
- Produces `qa/latest-test-results.json` and regenerated `qa/requirements_traceability.json`.
- `generate-traceability.py` exits non-zero for unknown test IDs, stale evidence, missing MUST/SHOULD mappings, or false PASS states.

- [ ] Write `QA-001`/`QA-010` failing tests that load the registry, prove every mapped ID exists, execute a controlled sample, and reject source-only PASS evidence.
- [ ] Run `python scripts/run-source-tests.py qa/test_release_foundation.py`; confirm failures report missing registry/generator.
- [ ] Implement the registry, stdlib source-test runner and traceability generator with JSON Schema-like validation performed in Python.
- [ ] Generate a lockfile from the exact `package.json` graph when npm resolution is available; CI uses `npm ci`, never `npm install`.
- [ ] Run foundation tests and SHA-checkpoint the task.

### Task 2: Invitation, password reset and password policy

**Files:**
- Create: `backend/platform_core/services/account_tokens.py`
- Modify: `backend/platform_core/models.py`
- Create: `backend/platform_core/migrations/0012_account_recovery.py`
- Modify: `backend/platform_core/views.py`
- Modify: `backend/lodgeflow/urls.py`
- Modify: `backend/lodgeflow/settings.py`
- Modify: `.env.local.example`, `.env.staging.example`, `.env.production.example`
- Create: `frontend/app/invite/page.tsx`
- Create: `frontend/app/forgot-password/page.tsx`
- Create: `frontend/app/reset-password/page.tsx`
- Test: `backend/platform_core/tests/test_account_recovery.py`
- Test: `frontend/e2e/account-recovery.spec.ts`

**Interfaces:**
- `issue_account_token(*, user, purpose, tenant=None, ttl_seconds) -> tuple[AccountActionToken, str]`
- `consume_account_token(*, raw_token, purpose, now=None) -> AccountActionToken`
- `POST /api/auth/invitation`, `/api/auth/password-reset/request`, `/api/auth/password-reset/confirm`.

- [ ] Write failing tests for single-use invitation acceptance, expiry, concurrent replay, inactive membership, password validators, enumeration-safe reset request, reset expiry and session invalidation.
- [ ] Run the focused Django tests; confirm expected missing-model/route failures when dependencies are available, and record BLOCKED_TOOLCHAIN otherwise.
- [ ] Add a SHA-256-at-rest token model with purpose, user, optional tenant, expiry, consumed timestamp and unique digest.
- [ ] Replace Django default-token invitation links with explicit invitation records while retaining a safe transition path for unconsumed legacy links.
- [ ] Configure `AUTH_PASSWORD_VALIDATORS`, `FRONTEND_BASE_URL`, invitation/reset TTLs and production URL validation.
- [ ] Build accessible invite/reset pages with password guidance, loading/error/success states and no token leakage to analytics or logs.
- [ ] Run focused tests, syntax/type gates and SHA-checkpoint the task.

### Task 3: Trusted client IP, resilient throttling, CSP and URL validation

**Files:**
- Create: `backend/platform_core/services/client_ip.py`
- Create: `backend/platform_core/services/safe_urls.py`
- Modify: `backend/platform_core/services/rate_limit.py`
- Modify: `backend/platform_core/services/audit.py`
- Modify: `backend/platform_core/security_policy.py`
- Modify: `backend/platform_core/middleware.py`
- Modify: `backend/platform_core/views.py`
- Modify: `backend/lodgeflow/settings.py`
- Modify: `frontend/next.config.mjs`
- Test: `backend/platform_core/tests/test_security_boundaries.py`
- Test: `frontend/e2e/security-policy.spec.ts`

**Interfaces:**
- `client_ip(request) -> str` trusts X-Forwarded-For only when REMOTE_ADDR is in `TRUSTED_PROXY_CIDRS`.
- `allow(key, limit, window, *, critical=False) -> bool` uses Redis and a bounded process-local fallback for critical endpoints.
- `validate_public_url(value, *, allow_relative=True, https_required=False) -> str` rejects credentials, control characters and non-http(s) schemes.

- [ ] Write failing behavior tests for spoofed forwarding headers, trusted-proxy chains, distinct user buckets behind Nginx, cache failure, audit-IP consistency, `javascript:` CMS links and Next hydration under CSP.
- [ ] Verify red failures.
- [ ] Implement canonical IP resolution and replace every direct `REMOTE_ADDR` security/audit use.
- [ ] Implement thread-safe bounded fallback throttling; auth, reset, public forms and webhooks pass `critical=True`.
- [ ] Validate CMS/navigation/redirect/media/billing URLs at write boundaries.
- [ ] Implement and browser-verify a Next-compatible nonce/hash CSP strategy; keep deny-by-default CORS.
- [ ] Run tests and SHA-checkpoint the task.

### Task 4: Complete member lifecycle, import and bulk-action contracts

**Files:**
- Create: `backend/platform_core/services/member_imports.py`
- Modify: `backend/platform_core/models.py`
- Create: `backend/platform_core/migrations/0013_member_operations.py`
- Modify: `backend/platform_core/views.py`
- Create: `frontend/components/MemberWorkspace.tsx`
- Modify: `frontend/app/members/page.tsx`
- Modify: `frontend/app/globals.css`
- Test: `backend/platform_core/tests/test_member_operations.py`
- Test: `frontend/e2e/members.spec.ts`

**Interfaces:**
- `preview_member_import(tenant, rows, mapping, actor) -> ImportPreview`
- `commit_member_import(tenant, preview_token, duplicate_decisions, actor) -> ImportResult`
- `POST /api/members/bulk/preflight` returns impacted IDs/count and a short-lived bound confirmation token.
- `POST /api/members/bulk` requires that token and exact action/filter fingerprint.

- [ ] Write failing tests for duplicate warning on create, cross-tenant matching, field mapping, row errors, duplicate skip/merge/create decisions, atomic import commit, bounded preflight and confirmation replay.
- [ ] Verify red failures.
- [ ] Add expiring import/bulk operation records containing hashes and non-sensitive summaries.
- [ ] Refactor import preview/commit and duplicate policy into the focused service.
- [ ] Build member table/detail/editor/activity/custom-field/import/bulk/export UI with permission-aware actions and accessible states.
- [ ] Run focused backend and Playwright tests; SHA-checkpoint the task.

### Task 5: Complete officers, candidates, search and structured settings UI

**Files:**
- Create: `frontend/components/OfficerWorkspace.tsx`
- Create: `frontend/components/CandidateWorkspace.tsx`
- Create: `frontend/components/GlobalSearch.tsx`
- Create: `frontend/components/CustomFieldEditor.tsx`
- Modify: `frontend/app/officers/page.tsx`
- Modify: `frontend/app/candidates/page.tsx`
- Modify: `frontend/app/settings/page.tsx`
- Modify: `frontend/components/AppShell.tsx`
- Modify: `frontend/app/globals.css`
- Test: `backend/platform_core/tests/test_governance_workflows.py`
- Test: `frontend/e2e/governance-workspaces.spec.ts`

**Interfaces:**
- Reuse existing `/api/officers`, `/api/officers/roles`, roster PDF, candidate CRUD/mentor/task/transition and `/api/search` contracts.
- Global search renders only server-authorized result types and URLs.

- [ ] Write failing E2E journeys for officer role/term CRUD, roster download, candidate create/edit/detail/mentor/task/stage history, permission-filtered search and custom-field editing.
- [ ] Add backend regression tests for date overlap, tenant ownership, stage rules and permission-filtered search destinations.
- [ ] Verify red failures.
- [ ] Implement the four focused frontend components and structured settings editor.
- [ ] Run backend/E2E/accessibility gates and SHA-checkpoint the task.

### Task 6: Report authorization, catalogue access and platform reports

**Files:**
- Modify: `backend/platform_core/services/reports.py`
- Modify: `backend/platform_core/views.py`
- Modify: `backend/lodgeflow/urls.py`
- Modify: `frontend/components/PremiumReports.tsx`
- Modify: `frontend/app/platform-admin/page.tsx`
- Test: `backend/platform_core/tests/test_report_authorization.py`
- Test: `frontend/e2e/reports.spec.ts`

**Interfaces:**
- Tenant preview requires `reports.view`; generation/download/schedule delivery require `reports.export`.
- `GET /api/platform/reports/catalog`, preview/generate/generated/download expose only R-080–R-084 under platform `reports.view`/`reports.export` permissions.
- Schedule forms consume only catalogue entries with `schedulable=true` and formats declared by that entry.

- [ ] Write failing tests proving a Viewer can preview but cannot generate/download/schedule, generated-file ownership cannot bypass permission, and operator reports cannot leak tenant PII.
- [ ] Verify red failures.
- [ ] Correct decorators and add defence-in-depth download checks.
- [ ] Add platform report routes and UI using a separate platform catalogue.
- [ ] Validate schedule attachment IDs, formats and current creator authorization again at execution time.
- [ ] Run tests and SHA-checkpoint the task.

### Task 7: Contract-complete report data and premium document rendering

**Files:**
- Create: `backend/platform_core/services/report_datasets.py`
- Create: `backend/platform_core/services/report_packs.py`
- Modify: `backend/platform_core/services/reports.py`
- Modify: `backend/platform_core/services/pdfs.py`
- Modify: `scripts/generate-pdf-samples.py`
- Modify: `docs/PDF_SAMPLE_APPROVAL.md`
- Test: `backend/platform_core/tests/test_report_contracts.py`
- Test: `qa/test_pdf_rendering.py`

**Interfaces:**
- Every Appendix C ID has an independently named dataset/pack builder or an explicitly shared builder whose output contract is identical.
- `build_report_dataset(tenant, report_id, filters) -> ReportDataset(columns, rows, kpis, sections)`.
- PDF visual tests render pages to images, check overflow/font embedding/basic contrast, and keep human UAT separate.

- [ ] Write literal-fixture failing tests for R-001/R-002/R-010/R-012/R-014/R-031/R-040/R-042/R-044/R-053/R-054/R-055/R-057 and R-080–R-084.
- [ ] Verify red failures against current shallow/alias output.
- [ ] Implement missing period comparisons, custom fields, retention/churn, PII selection, stage duration/exceptions, attendance percentages, participation, finance opening balance/links/mix and full meeting/treasurer packs.
- [ ] Rebuild report/PDF layouts with stable fonts, repeating furniture, wrapping and page-break rules.
- [ ] Regenerate all contractual samples and render every page for visual inspection.
- [ ] Run reconciliation/render tests and SHA-checkpoint the task.

### Task 8: Current payment-provider and webhook contracts

**Files:**
- Modify: `backend/platform_core/services/payments.py`
- Create: `backend/platform_core/services/provider_signatures.py`
- Modify: `backend/platform_core/views.py`
- Modify: `backend/platform_core/services/webhook_processing.py`
- Test: `backend/platform_core/tests/test_provider_contracts.py`

**Interfaces:**
- Stripe verification delegates to `stripe.Webhook.construct_event` and returns parsed event or a typed failure.
- PayMongo uses `POST https://api.paymongo.com/v1/payment_links`; signature verification selects `te` in test and `li` in live and enforces tolerance.
- Xendit uses `POST https://api.xendit.co/v3/payment_requests` with `api-version: 2024-11-11` and string/JSON-safe decimal amounts.

- [ ] Write failing literal contract tests for paths, headers, payloads, multiple Stripe v1 signatures, tolerance, PayMongo mode separation, replay and Xendit decimals.
- [ ] Verify red failures using real adapter code with only the external HTTP boundary replaced.
- [ ] Implement current adapters/signatures and return typed provider errors without secret-bearing messages.
- [ ] Add duplicate/out-of-order webhook reconciliation tests and idempotent state transitions.
- [ ] Run tests and SHA-checkpoint the task.

### Task 9: Documents, media delivery and retention

**Files:**
- Create: `backend/platform_core/services/retention.py`
- Modify: `backend/platform_core/views.py`
- Modify: `backend/lodgeflow/urls.py`
- Modify: `frontend/components/CmsManagers.tsx`
- Modify: `frontend/app/documents/page.tsx`
- Test: `backend/platform_core/tests/test_document_retention.py`

**Interfaces:**
- `retention_decision(document, tenant_policy, now=None) -> RetentionDecision`.
- Authorized platform media and tenant document downloads return private/no-store responses or short-lived signed storage redirects.
- Deletion records disposition evidence and refuses active legal/retention holds.

- [ ] Write failing tests for unauthorized/cross-tenant download, media visibility, retention hold, minimum retention date, storage failure and disposition audit evidence.
- [ ] Verify red failures.
- [ ] Implement retention decisions, authorized media delivery and recoverable error handling.
- [ ] Complete document/media UI status and guarded deletion.
- [ ] Run tests and SHA-checkpoint the task.

### Task 10: Background jobs, concurrency and authorization revalidation

**Files:**
- Modify: `backend/platform_core/tasks.py`
- Modify: `backend/platform_core/services/communications.py`
- Modify: `backend/platform_core/services/reports.py`
- Test: `backend/platform_core/tests/test_background_jobs.py`

**Interfaces:**
- Jobs revalidate tenant/user authorization at execution time.
- `SystemJob.payload` contains correlation and non-secret immutable inputs; result tracks durable output IDs.
- Duplicate task delivery produces no duplicate email, report file, receipt or recurrence occurrence.

- [ ] Write failing tests for revoked report permission, disabled tenant, duplicate task IDs, partial email retry, recurring overlap and provider job ordering.
- [ ] Verify red failures.
- [ ] Add transactional job acquisition/idempotency keys and authorization revalidation.
- [ ] Ensure errors are bounded/redacted and alerts deduplicate.
- [ ] Run tests and SHA-checkpoint the task.

### Task 11: Production startup, backups, monitoring and restore drill

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `deploy/nginx.conf`
- Modify: `scripts/deploy-production.sh`
- Modify: `scripts/backup.sh`
- Modify: `scripts/restore.sh`
- Modify: `scripts/verify-backup-restore.sh`
- Create: `deploy/lodgeflow-backup.service`
- Create: `deploy/lodgeflow-backup.timer`
- Modify: `scripts/ops-monitor.py`
- Modify: `docs/PRODUCTION_DEPLOYMENT.md`
- Test: `qa/test_operations_runtime.py`

**Interfaces:**
- Worker/beat/backend depend on successful `migrate` and configured readiness.
- Backup manifest includes encrypted database dump, local-media archive or S3 inventory/export evidence, hashes and metadata.
- Restore verification checks database sentinel, private-file content, generated-report checksum and `/api/ready/`.

- [ ] Write failing executable tests that render Compose config, run backup scripts against fixtures, tamper with artifacts, and prove restore refuses bad/missing file evidence.
- [ ] Verify red failures.
- [ ] Add migration/readiness ordering, file-aware encrypted backup, off-VPS transfer hook, retention and systemd timer.
- [ ] Extend monitoring for backup age/failure, disk, queues, webhooks, storage/scanner and TLS.
- [ ] Run shell/YAML/fixture recovery tests and SHA-checkpoint the task.

### Task 12: OpenAPI, UI journeys and accessibility completion

**Files:**
- Modify: `docs/openapi.yaml`
- Modify: `frontend/e2e/core.spec.ts`
- Create: `frontend/e2e/role-matrix.spec.ts`
- Create: `qa/test_openapi_contract.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- OpenAPI uses `{parameter}` syntax and documents all 2xx/4xx contracts, tenant header, auth and pagination.
- Role-matrix E2E covers owner, secretary, treasurer, membership, mentor, auditor and viewer.

- [ ] Write failing contract tests for invalid `<slug:key>` paths, undocumented runtime paths and missing error schemas.
- [ ] Verify red failures.
- [ ] Reconcile the schema with runtime URLs and add schema validation to CI.
- [ ] Add production-like desktop/mobile/keyboard/axe journeys for primary modules and permission boundaries.
- [ ] Run schema/E2E gates and SHA-checkpoint the task.

### Task 13: Full traceability, release verification and final package

**Files:**
- Modify: `qa/acceptance_registry.json`
- Regenerate: `qa/requirements_traceability.json`
- Create: `docs/RELEASE_EVIDENCE.md`
- Create: `docs/KNOWN_DEFECTS.md`
- Create: `docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md`
- Modify: `docs/RELEASE_STATUS.md`
- Modify: `docs/RELEASE_NOTES_2026-08-24.md`
- Modify: `scripts/release-check.sh`

**Interfaces:**
- `scripts/release-check.sh` produces machine-readable and human-readable evidence and exits non-zero for any failed local gate, unmapped MUST/SHOULD or open P0/P1.
- Final ZIP excludes secrets, caches, runtime media, `.env` files, node modules, virtual environments and transient outputs.

- [ ] Re-read all 293 MUST/SHOULD rows and map each to real evidence; fail on any unmapped row.
- [ ] Run all locally available compile, unit, integration, API, frontend, E2E, schema, security, PDF, backup/restore and packaging checks from a clean workspace.
- [ ] Record unavailable environment-dependent checks as BLOCKED_EXTERNAL with exact commands/prerequisites.
- [ ] Correct all stale release claims and regenerate samples/evidence/checksums.
- [ ] Create the final clean ZIP, inspect its file list, extract it into a fresh directory and rerun portable source/package checks.
- [ ] Upload the ZIP and return it with the exact remaining external-only acceptance list.

## Plan self-review result

- Coverage: every design workstream and all requirement families have an owning task.
- Placeholders: no deferred implementation placeholders are accepted.
- Interface consistency: account tokens, client IP, throttling, import/bulk confirmation, report datasets, provider adapters, retention decisions and evidence generation have single named boundaries.
- Execution: inline `superpowers:executing-plans`; no subagents; checkpoints use SHA-256 because the source archive has no Git metadata.
