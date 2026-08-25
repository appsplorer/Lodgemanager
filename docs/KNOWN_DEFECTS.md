# Known Defects, Limitations and Unfinished Acceptance

## Open implementation defects

No known P0/Critical, P1/High or unimplemented MUST/SHOULD item remains after the source, dependency, build and Django/SQLite remediation pass. This statement is not a production certification: environment-dependent defects may still be found by the blocked gates below.

## Required acceptance still outstanding

Production is blocked on all 33 external gate groups covering 293 MUST/SHOULD requirements. The main unavailable evidence classes are:

- PostgreSQL clean/upgrade migrations, uniqueness/locking semantics and concurrent financial receipt allocation.
- Redis/Celery/Beat job, retry, scheduling and failure-recovery behavior.
- Docker Compose build, non-root images, private networking, migration ordering and readiness.
- Real desktop/mobile Chromium journeys, keyboard behavior, offline/PWA scenarios and axe accessibility.
- Private S3-compatible storage, SMTP delivery and required ClamAV scanning.
- Stripe, PayMongo and Xendit sandbox callbacks for each enabled provider, including duplicate and mismatch/quarantine cases.
- Production-scale performance/LCP/error-rate acceptance and external operational alert delivery.
- Encrypted off-site backup plus destructive database/private-storage restore with measured RPO/RTO.
- Dependency/container/secret/DAST evidence on the exact images, staged UAT, production smoke, rollback rehearsal and formal sign-off.

Exact commands, prerequisites, covered requirement IDs and exit criteria are in `docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md`. These are release blockers, not accepted risks.

## Optional MAY extensions

Five optional rows are excluded from the required acceptance denominator and remain NOT_RUN unless separately commissioned:

- `CMS-014`: translated page variants and locale switching.
- `OFF-006`: extended succession planning/nominations.
- `MTG-010`: QR attendance check-in.
- `DOC-009`: OCR/full-text document indexing.
- `COM-009`: SMS provider delivery.

Some underlying extension points already exist, but none of these optional rows is represented as production-accepted in the traceability output.

## Packaging-environment limitations

Docker, PostgreSQL, Redis, ClamAV, provider credentials and browser binaries were not available in the packaging workspace. SQLite emitted expected warnings for four PostgreSQL-only `NULLS NOT DISTINCT` constraints, and the PostgreSQL concurrency test was skipped rather than simulated. No claim in this package converts those limitations into PASS evidence.
