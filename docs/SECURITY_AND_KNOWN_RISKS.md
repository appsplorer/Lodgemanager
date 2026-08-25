# LodgeFlow Security Posture and Known-Risk Register

## Threat model

The baseline threat model covers cross-tenant data access, privilege escalation, credential disclosure, CSRF/session abuse, malicious uploads, webhook forgery/replay, duplicate financial processing, export exfiltration, unsafe offline replay, background-job duplication and compromise of backups/provider credentials.

## Tenant isolation

Tenant isolation is a server-side invariant. Tenant-owned queries include the authorized tenant context and object-level helpers deliberately use 404 in selected cases to avoid existence disclosure. RBAC is enforced in API views/services, not only in the frontend. Custom-role edits are resolved dynamically on subsequent requests.

## Secrets and provider security

Secrets are injected at deployment. `EncryptedCredential` stores ciphertext only and supports test/live separation and enable/disable. Provider webhook signatures, amount/currency/mode and tenant/request references are verified before financial state is applied. High-risk platform operations require step-up authentication.

## Files and generated documents

Uploads use extension/MIME/signature validation, size limits and optional/required ClamAV policy. Private documents download through authenticated ACL checks. Meeting-pack attachments are PDF-only, ACL revalidated, storage-read fail-closed, rejected if encrypted/corrupt, and bounded by per-file/aggregate size and page limits.

## Known release risks

This source tree is **not production-approved** until external runtime acceptance is complete. Current unavoidable environment-dependent gates include real PostgreSQL migration/fresh-upgrade testing, a clean Next.js production build with installed lock-resolved dependencies, Docker non-root runtime checks, Playwright/axe journeys, destructive backup/restore, reference load/LCP measurements, SMTP/S3/Redis/Celery/Beat/ClamAV staging and Stripe/PayMongo/Xendit Provider sandbox callbacks where enabled. These are release blockers, not waived requirements.

The repository currently declares direct dependency versions. `docs/SBOM.json` is a source-level direct-dependency inventory; CI/release must generate/scan the resolved transitive SBOM and archive scanner results. Dependency advisories can change after this document is written.

## Security acceptance

No open P0/Critical or P1/High defect is permitted at production sign-off. Accepted lower-severity issues require an owner, rationale and target release. Security logs/traces must avoid secrets and unnecessary PII.
