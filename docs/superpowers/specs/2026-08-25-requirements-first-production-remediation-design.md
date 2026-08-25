# Requirements-First Production Remediation Design

**Product:** LodgeFlow / Quill of the Craft  
**Date:** 2026-08-25  
**Authority:** `Quill_of_the_Craft_Final_Master_Requirements_v1.0`  
**Supporting context:** `Lodge_Management_SaaS_Spec_Proposal`  
**Implementation baseline:** supplied `LodgeFlow_FULL_SOURCE_afefebe_20260824` archive

## 1. Purpose and acceptance policy

This programme turns the supplied baseline into a production-deployable multi-tenant lodge-management SaaS without replacing the existing Django/Next.js architecture or discarding existing data.

The master requirements contain 298 traced requirements: 258 MUST, 35 SHOULD and 5 MAY. The release policy is:

1. Every MUST and every SHOULD is an implementation requirement and must have executable acceptance evidence.
2. MAY requirements are not release gates unless already promised by another accepted requirement or enabled in the delivered configuration.
3. A requirement is PASS only when its observable behavior is exercised by an executable test or a documented human acceptance procedure that cannot be automated.
4. Static source-string assertions are not acceptance evidence for runtime behavior.
5. External checks requiring real provider credentials, DNS/TLS, VPS infrastructure or human UAT remain BLOCKED_EXTERNAL until performed. They are never relabelled PASS from mocks or source inspection.
6. The final package must have zero open P0/Critical or P1/High defects. Lower-severity accepted defects require an owner, rationale and target release.

## 2. Chosen approach

Use requirements-first additive remediation:

- Preserve Django 5.2+, Python 3.12+, Next.js 16, React 19, PostgreSQL, Redis/Celery, Docker Compose and Nginx.
- Preserve tenant IDs and existing records; use forward-only additive migrations and explicit data migrations when normalization is required.
- Extract focused services from the large view module only where a security or workflow boundary needs independent testing. Avoid an unrelated rewrite.
- Complete backend behavior and its primary frontend workflow together so an API-only implementation cannot be counted as a finished user requirement.
- Generate traceability from test metadata and execution results rather than maintaining unverified hand-written PASS claims.
- Deliver one final ZIP after the complete local release gate. External acceptance evidence is delivered separately inside the ZIP as an exact checklist.

## 3. System boundaries

### 3.1 Tenant and platform isolation

All tenant-owned queries, mutations, files, background jobs, exports, search results and audit events are scoped by the resolved tenant. Platform-operator functions use separate routes and permissions and cannot silently reuse tenant authorization. Cross-tenant object IDs return the documented 403/404 behavior without leaking object existence.

### 3.2 Identity and authorization

The identity boundary includes login, logout, invitation acceptance, password reset, MFA enrolment/recovery/reset, step-up authentication, session security, impersonation and role/permission enforcement. Server-side authorization remains authoritative; hidden or disabled frontend controls are usability measures, not security controls.

### 3.3 Data and files

PostgreSQL is authoritative for transactional state. Redis supports cache, rate limiting and Celery but loss of Redis cannot disable critical abuse controls without a conservative fallback. Private files are served only after an authorization check. File retention and deletion respect tenant policy. Storage may be local or S3-compatible, and the disaster-recovery design covers whichever mode is enabled.

### 3.4 External services

Email, ClamAV, object storage, Stripe, PayMongo and Xendit are adapters behind validated configuration. Provider callbacks are authenticated, replay-resistant, idempotent and tolerant of duplicate or out-of-order delivery. Provider-specific payload creation uses decimal-safe serialization and the current documented API version.

## 4. Workstream design

### 4.1 Release foundation and traceability

Create a reproducible dependency baseline with a committed frontend lockfile and pinned/compatible Python dependencies. Keep development and production environment examples synchronized with strict production validation.

Replace the present source-string QA model with a requirement registry that contains, for every MUST and SHOULD:

- requirement ID and exact normative level;
- owning subsystem;
- executable backend, frontend, integration, E2E, security, performance, recovery or visual test IDs;
- latest result: PASS, FAIL, BLOCKED_EXTERNAL or NOT_RUN;
- artifact/evidence path and execution timestamp;
- external environment prerequisites where applicable.

The report generator rejects unknown test IDs and cannot report PASS if referenced evidence is absent or stale.

### 4.2 Identity, security and privacy

Implement the complete invitation journey:

- tenant administrator creates a role-bounded invitation;
- an email contains a single-use random token and configured frontend URL;
- `/invite` validates expiry, tenant status and token state without leaking accounts;
- the user sets a password subject to Django validators, accepts applicable terms, and optionally enrols MFA;
- successful acceptance consumes the token atomically; reuse and concurrent acceptance fail safely.

Implement password reset request and confirmation with enumeration-safe responses, single-use expiring tokens, rate limiting, password validation, session invalidation policy and audit evidence. MFA recovery/reset requires step-up or an explicitly audited platform recovery flow.

Introduce one trusted client-IP resolver shared by auditing and all throttled endpoints. It accepts forwarded addresses only from configured trusted proxies. Critical auth/public-form throttles use a bounded local fallback or deny conservatively when Redis fails instead of failing open.

Generate a per-response CSP nonce for the Next.js application or use another Next.js-supported CSP construction verified by a production build and browser test. Eliminate unsafe URL schemes from CMS links and assets; validate external URLs against explicit schemes and media-fetch rules. Maintain secure cookie, CSRF, CORS, HSTS and security-header checks.

### 4.3 Core product workflows and user interface

Each primary module page supports the required real-data journeys, responsive layout, keyboard operation, accessible naming, loading/empty/error states and permission-aware actions.

**Members:** paginated/searchable list; details; create/edit/archive or permitted delete; activity; custom fields; duplicate warnings on create/update; import mapping; row-level preview/errors; duplicate decisions before commit; bounded bulk-action preflight and confirmation; export authorization; merge/anonymization safeguards.

**Officers:** officer-role definitions, current/historic assignments, create/edit/end/delete as permitted, date validation, member links, roster view and roster PDF.

**Candidates:** create/edit/detail, stage workflow, mentor assignment, tasks, history, filters and authorized actions.

**Meetings and minutes:** creation, recurrence, attendance, apologies, agenda/notices, workflow transitions, locking, version conflict handling, attachments and complete meeting-pack output.

**Documents and templates:** private access control, categories/tags, upload/scan status, templates, retention-aware deletion and authorized download.

**Search and settings:** global tenant-scoped search with permission filtering; structured settings editors instead of raw JSON for normal administration; operator-only raw diagnostics remain separated.

**Offline/PWA:** only the documented low-risk allowlist can queue. Queued changes are encrypted and bound to the authenticated principal, never silently evicted, carry idempotency and optimistic-concurrency metadata, expose conflicts, and require an explicit decision before logout discards unsynced data. High-risk actions always require an online server.

### 4.4 Finance, billing and provider payments

Preserve immutable financial evidence and transactionally serialized receipt numbering. Complete dues-cycle governance, assessments, proration, late fees, payments, allocations, adjustments, waivers, credits, reversals, expenses, approvals, arrears, statements and precision-safe exports with permission and audit coverage.

Payment adapters use these production contracts:

- Stripe: official SDK request/webhook helpers; raw-body signature verification; configured timestamp tolerance; idempotent event processing.
- PayMongo: current `/v1/payment_links` API and current request/response shape; mode-appropriate `te` or `li` webhook signature; timestamp tolerance and replay protection.
- Xendit: `/v3/payment_requests` with `api-version: 2024-11-11`; callback-token validation per environment; decimal-safe amounts and idempotent ordering.

Return URLs are HTTPS and approved-origin validated in production. Secrets never enter logs, audit metadata, browser payloads or the package. Tenant SaaS subscription billing is separate from tenant member-payment collection.

### 4.5 Reports, documents and communications

Implement every report promised by the master Appendix C as a real report definition, not an unrelated alias. Tenant and platform catalogues are separate. Each definition declares audience, permission, supported formats, schedulability, sensitivity, filters, columns/sections and row-estimation behavior.

`reports.view` permits catalog/preview access. `reports.export` is required for generation and download. Sensitive threshold policies may add requester/approver separation, reason, expiry and immutable evidence. Scheduled-report UI options are loaded from the live schedulable catalogue.

Report-specific contracts include:

- complete monthly management pack and annual comparison;
- member directory/custom-field, retention/churn and configurable PII exports;
- candidate pipeline, prior-stage duration and exception reporting;
- meeting attendance percentages, participation indicators and full meeting pack;
- finance receipts, opening balances, statements, payment mix and treasurer pack;
- communications delivery and compliance evidence;
- accessible operator endpoints for R-080 through R-084 with platform-only authorization.

Generated PDF/DOCX/CSV/XLSX outputs reconcile headline totals to detail rows and record filters, row count, generator, approval, checksum and file metadata. Premium PDF templates use embedded or deployment-stable fonts, predictable spacing, repeating headers/footers, page numbering, tenant branding, sensible page breaks and accessible text contrast.

Communications support authorized audiences, safe template rendering, preview, scheduling, cancellation rules, idempotent delivery, retry classification and per-recipient evidence. SMS remains disabled unless an approved provider is configured; enabling it activates the same authorization, audit and delivery principles.

### 4.6 Background processing and concurrency

Celery jobs are idempotent and tenant-scoped. Retried report, campaign, webhook and recurrence jobs do not duplicate durable effects. Job state records attempts, bounded errors, timestamps and correlation IDs without secrets.

Database constraints and `select_for_update` protect receipt sequences, invitation consumption, workflow transitions, approvals, imports, bulk actions and provider reconciliation. Tests cover duplicate delivery, retry, concurrent acceptance and ordering.

### 4.7 Deployment, observability and disaster recovery

Production Compose gates backend, worker and beat startup on successful migration and readiness. Readiness verifies database plus configured critical dependencies; liveness only verifies the process. Containers run non-root with health checks, bounded resources, restart policy, read-only or minimal-write filesystems where practical, and no development service exposure.

Backups include PostgreSQL and all private/generated files for the active storage mode. A provided timer/cron example performs encrypted off-VPS transfer, retention, failure alerting and age monitoring. The restore drill verifies a database sentinel, representative private file, generated document checksum and application readiness in an isolated target.

Operational evidence covers HTTP errors/latency, worker queue and failures, webhook quarantine, email, storage, malware scanner, database capacity, backup age/failure, TLS expiry, disk pressure and audit-chain anomalies. Logs are structured, correlated, privacy-minimized and rotation-ready.

### 4.8 API and error contracts

OpenAPI paths use valid parameter syntax and document authentication, tenant context, request/response schemas, pagination and error envelopes. Runtime schema validation and representative contract tests prevent documentation drift.

Errors are stable and actionable without exposing secrets, stack traces, cross-tenant existence or provider credentials. Mutations validate the entire request before durable side effects. Network/external failures are classified as retryable or terminal, and UI messages preserve a safe correlation reference.

## 5. Data migration strategy

1. Run `makemigrations --check --dry-run` before and after changes.
2. Add schema with nullable/default-safe fields first.
3. Backfill in bounded batches through deterministic data migrations when required.
4. Add uniqueness/check constraints only after duplicate reconciliation.
5. Document irreversible normalization and require a verified backup before production migration.
6. Test fresh install, upgrade from the supplied migration head and representative rollback of application code.

No migration deletes tenant data merely to make tests pass.

## 6. Testing and evidence architecture

Tests follow red-green-refactor. Each test names a stable requirement-aware ID, exercises real behavior, and identifies the production mutation it catches.

Required layers:

- fast unit tests for validation, permission policy, calculations and adapters;
- PostgreSQL integration tests for tenant scoping, constraints, transactions and concurrency;
- API tests for authentication, permissions, idempotency, pagination, validation and OpenAPI contracts;
- frontend component/journey tests for real states and actions;
- Playwright browser tests for complete role journeys, accessibility, CSP, offline and responsive behavior;
- provider sandbox contract tests where credentials are available, with recorded non-secret evidence;
- file/malware/storage integration tests;
- PDF/document render-and-visual checks plus human UAT approval;
- backup/restore, container, security and performance gates against representative data.

Static checks remain useful for compilation, linting, dependency policy and configuration validation, but they cannot replace runtime tests.

## 7. Release gates

A final ZIP may be produced only after fresh evidence for all locally executable gates:

1. dependency install from lock/pins succeeds;
2. Python compile, Django checks and migration drift checks pass;
3. backend unit/integration/API suites pass on PostgreSQL and Redis;
4. frontend lint, type-check, unit tests and production build pass;
5. Playwright/axe journeys pass against the production-like stack;
6. OpenAPI validation, shell/YAML checks and secret/dependency/container scans pass;
7. report reconciliation and generated-document render checks pass;
8. backup/restore drill and reference performance gates pass where the local runner supports them;
9. the traceability generator reports every MUST and SHOULD as PASS or an accurately explained BLOCKED_EXTERNAL;
10. no P0/P1 defect is open.

## 8. Final deliverables

The final ZIP contains:

- complete frontend, backend, worker and deployment source;
- committed migrations and reproducible dependency files;
- environment templates without secrets;
- executable tests and test commands;
- generated requirement traceability and release-evidence index;
- OpenAPI specification;
- deployment, administration, backup and restoration instructions;
- representative regenerated PDFs required by the master specification;
- known-defect register and exact external-acceptance checklist;
- release notes and checksums.

The final handoff states exactly which checks ran, their counts/results, which checks require the real deployment environment, and any remaining lower-severity defects. It does not claim that a local mock proves live-provider, VPS, TLS, email-deliverability or human-UAT acceptance.

## 9. Explicit non-goals

- Rewriting the platform in another framework.
- Replacing PostgreSQL with a development-only database for acceptance.
- Enabling optional SMS without an approved provider.
- Embedding production secrets or test customer data.
- Treating MAY requirements as mandatory unless another accepted requirement depends on them.
- Claiming external deployment approval from source inspection alone.

## 10. Design acceptance

This document formalizes the approved requirements-first approach. Implementation is divided into separate plans for release foundation, identity/security, core workflows, finance/providers, reports/documents/communications, and deployment/release verification. All plans inherit the acceptance policy in Section 1.
