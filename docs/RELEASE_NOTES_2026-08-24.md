# LodgeFlow Release Notes - 24 August 2026

## Scope

This release consolidates LodgeFlow / Quill of the Craft into the Final Baseline source tree: multi-tenant tenant/public/platform layers; RBAC and step-up identity controls; CMS/Page Studio; members/officers/candidates; governed meetings/minutes and PDF packs; dues/payments/expenses; private documents/templates; communications; premium reports; audit/export approval; payment-provider/webhook controls; offline safety boundaries; observability; backup/restore and staging/CI gates.

## Migration notes

Migrations through `0011_meeting_pack_attachments.py` are required. `0010_integrity_controls.py` reconciles legacy duplicate provider references/delivery logs before adding idempotency constraints. `0011` adds tenant-scoped configured meeting-pack PDF attachments. Production migration must be run as a controlled one-shot step and validated on both fresh and prior-release PostgreSQL databases.

## Acceptance status

Local source QA, Python compile and TypeScript/TSX syntax checks are release-development evidence only. **Not production-approved** until the complete CI/staging acceptance sequence passes, including real PostgreSQL, dependency install/build, Docker, Playwright/axe, backup restore, performance/reference data, storage/email/queue/scanner and enabled Provider sandbox callbacks.

## Compatibility and rollback

Application rollback is distinct from database rollback. The duplicate-consolidation step in migration 0010 is intentionally not logically reversible; preserved evidence is retained on the surviving records. Take and verify a production backup before migration. Review `docs/PRODUCTION_DEPLOYMENT.md` and the disaster-recovery instructions before change approval.
