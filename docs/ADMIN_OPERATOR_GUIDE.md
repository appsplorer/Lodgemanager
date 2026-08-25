# LodgeFlow Administrator and Operator Guide

## Platform operator

Platform operators use the operator console for tenant lifecycle, feature entitlements, billing/provider readiness, encrypted provider credentials, webhooks, system jobs, audit/export evidence and security alerts. Permissions separate support, billing, compliance and operations duties. Sensitive credential, impersonation, MFA and replay actions require recent step-up authentication and generate audit/security evidence.

## Tenant administrator

A Tenant administrator manages lodge profile/branding, meeting defaults, custom member fields, candidate stages, dues/payment policy, templates, security settings, retention policy and tenant users/custom roles. Changes are server validated and audited with before/after values. A custom role may only contain permissions the assigning administrator can grant.

## Provider credentials

Provider credentials are encrypted at rest and are never returned in plaintext after storage. Test/live mode is explicit. Operators may enable/disable, rotate and health-check a credential. Disabled credentials are excluded from provider resolution. Never paste secrets into issue trackers, logs, screenshots or repository files.

## Routine operational checks

Review `/api/health/` and `/api/readiness/`, failed `SystemJob` records, webhook quarantine/failures, delivery logs, security alerts, storage health, TLS expiry and backup outcomes. Readiness covers database, cache, configured private storage and malware-scanner availability according to production configuration.

## Backup and restore

Run the encrypted backup tooling from the deployment host using separately managed backup secrets. Verify SHA-256/integrity and retention after each backup. Destructive restore requires explicit confirmation and must first be proven in non-production using `scripts/verify-backup-restore.sh`. Object-storage versioning/backup must protect private/generated files independently of the primary VPS.

## Incident handling

For an Incident: preserve logs/audit evidence, disable compromised credentials or tenant access where needed, rotate affected secrets, quarantine suspicious webhooks/files, restore only from verified backups, and document the scope/timeline. Do not delete financial, audit or delivery evidence to “clean up” an incident. Escalate suspected cross-tenant exposure as P0/Critical until disproved.

## Release operations

Follow `docs/PRODUCTION_DEPLOYMENT.md`. A release is not production-approved merely because source checks pass. PostgreSQL migrations, frontend production build, containers, Playwright/axe, backup restore, performance/reference load, storage/email/Celery/ClamAV and enabled payment-provider sandboxes must pass in CI/staging before sign-off.
