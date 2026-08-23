# Release Status — Quill of the Craft Lodge Management System v1.0

Baseline reviewed: **Master Software Requirements Specification & Acceptance Standard v1.0, 23 Aug 2026**.

## Source implementation status

The commercial source tree contains the three required product layers (public CMS website, tenant workspace and operator console) plus the requested optional/Phase-2 extension surfaces. The source implementation includes tenant isolation/RBAC/MFA, members/officers/candidates/meetings/finance/documents/communications/reports, payment providers, PWA continuity, CMS/media/SEO/consent/localization, QR attendance, SMS extension, OCR/full-text indexing, scheduling, audit/exports, backup/restore tooling, observability, API documentation and deployment/CI assets.

The latest expert source-QA pass additionally corrected:

- unsafe tenant-context dereferences on method-specific endpoints so anonymous/unscoped calls fail with controlled 401/403 responses;
- candidate mentor mutation authorization (view permission is no longer sufficient to change mentor assignments);
- background campaign/import jobs now revalidate active tenant and requester permissions before execution;
- Stripe webhook processing no longer lets invoice/payment object statuses overwrite subscription lifecycle state;
- production API Origin allowlisting and conservative browser security headers/CSP;
- CI evidence collection and production `check --deploy` gate;
- deterministic synthetic reference PDFs for every Appendix-D generated-document family;
- same-site-only CMS redirect validation to close open-redirect abuse;
- scheduled-report recipient authorization (active tenant users by default, explicit policy required for external addresses);
- complete before/after tenant-settings audit snapshots and stronger password-policy bounds validation;
- media-library decorative-image metadata persistence and additional bounded-list safeguards.

## QA executed in the packaging environment

- `pytest -q qa` — **85 passed** after the latest hardening batch.
- `python -m compileall backend` — passed.
- TypeScript parser — **59 files, 0 syntax errors**.
- Python AST parse — **58 files parsed**.
- GitHub Actions YAML parse — passed.
- Shell syntax checks for deployment/backup/restore scripts — passed.
- **10** reference PDFs generated and verified with `pdfinfo` + `pdftotext`.

These results are source/static evidence only. They are not used to fabricate runtime acceptance.

## Runtime release gates

The SRS requires runtime evidence before a customer production deployment. GitHub Actions is configured to execute PostgreSQL/Redis integration tests, frontend typecheck/build, Docker stack E2E, Playwright/axe, dependency/secret checks and collect browser/container artifacts. A production-like staging environment must additionally validate SMTP, S3-compatible storage, ClamAV, Celery/Beat, Stripe sandbox, enabled PayMongo/Xendit callbacks, backup→restore, performance/load profile and signed UAT.

**Release policy:** do not promote to customer production until all release-blocking CI/staging/UAT gates are green and the final defect register has zero open P0/Critical or P1/High defects.
