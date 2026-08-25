#!/usr/bin/env python3
"""Build honest production-acceptance gates for every MUST/SHOULD requirement.

These rows intentionally remain BLOCKED_EXTERNAL until the exact packaged build is
exercised in a production-like environment. Passing source/unit checks is recorded
separately and is never promoted into production acceptance.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


GATES = {
    "GEN": ("Deployed product smoke and tenant isolation", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test)", "Docker, PostgreSQL, Redis, S3, SMTP, ClamAV and browser runtime", "All three product layers persist real data; cross-tenant negative cases and core journeys pass."),
    "ARC": ("Production architecture and service topology", "docker compose --env-file .env.staging -f docker-compose.prod.yml -f docker-compose.staging.yml config && ./scripts/staging-e2e.sh", "Docker Compose v2 and staging secrets", "Only intended ingress is exposed; migration/readiness ordering and all stateful dependencies pass."),
    "IAM": ("Identity, MFA and session security", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)", "PostgreSQL, Redis and real browser", "Invitation/reset expiry and replay, MFA enrolment, timeouts, suspension and tenant switching pass."),
    "RBAC": ("Tenant and platform role matrix", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)", "Seeded staging role accounts and browser runtime", "Every allowed and denied API/UI action matches the approved role matrix; dual control passes."),
    "CMS": ("Public website, CMS, SEO and lead capture", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Staging public hostname, SMTP and browser runtime", "Publishing, revisions, redirects, SEO, forms, consent and responsive public journeys pass."),
    "PAD": ("Platform operator console", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/role-matrix.spec.ts)", "Platform role accounts with MFA", "Tenant, user, feature, credential, billing, logs and impersonation actions obey platform permissions."),
    "TAD": ("Tenant administration and configuration", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Owner/admin staging accounts", "Branding, locale, timezone, finance, security, custom fields/stages and user settings persist and validate."),
    "DASH": ("Dashboard, navigation and global search", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Representative staging dataset and browser runtime", "KPIs reconcile to persisted data and search/navigation remain tenant- and permission-scoped."),
    "MEM": ("Member CRM and lifecycle", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Representative member fixtures", "CRUD, duplicate override, archive/anonymize, activity, custom fields and statements pass."),
    "OFF": ("Officer terms and governance", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Representative officer fixtures", "Role definitions, overlapping terms, succession, history and roster output pass."),
    "CAN": ("Candidate, mentor and milestone workflows", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Candidate/mentor role fixtures", "Pipeline, scoped mentor access, tasks, stage history, milestones and progress output pass."),
    "MTG": ("Meeting governance workflows", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Meeting fixtures, PostgreSQL and browser runtime", "Recurrence, agenda, attendance, visitors, minutes locks/reopen and generated packs pass."),
    "FIN": ("Finance, dues, payments and receipts", "./scripts/staging-e2e.sh", "PostgreSQL concurrency plus representative finance fixtures", "Proration, assessment idempotency, unique receipts, allocation, reversal, approvals and exports reconcile."),
    "DOC": ("Documents, templates and secure media", "./scripts/staging-e2e.sh", "Private S3-compatible storage and required ClamAV", "MIME/signature/size/scan controls, ACL downloads, templates, previews and generated files pass."),
    "COM": ("Communications and delivery", "./scripts/staging-e2e.sh", "SMTP sandbox/Mailpit and Celery worker", "Consent, segmentation, preview, scheduling, idempotent delivery, retry and delivery logs pass."),
    "REP": ("Report catalogue, analytics and scheduling", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "PostgreSQL, Celery/Beat, SMTP and browser runtime", "Every Appendix C report reconciles, filters, exports, saves, schedules and enforces permissions."),
    "RPTFMT": ("Professional report format acceptance", "./scripts/staging-e2e.sh && python scripts/generate-pdf-samples.py", "LibreOffice/PDF renderer, SMTP and representative data", "PDF/XLSX/CSV are searchable, formula-safe, branded, paginated, private and visually approved."),
    "AUD": ("Audit, compliance and sensitive export controls", "./scripts/staging-e2e.sh", "PostgreSQL and separate requester/approver/operator accounts", "Append-only chain, redaction, filters, dual control, impersonation and evidence hashes pass."),
    "PAY": ("Payment-provider sandbox reconciliation", "gh workflow run staging-acceptance.yml", "Real Stripe, PayMongo and Xendit sandbox credentials for enabled providers", "Staging passes and recorded provider-originated callbacks prove signature, tenant/mode/amount/currency binding, duplicate replay, quarantine and subscription flows."),
    "PWA": ("Offline/PWA continuity and conflicts", "(cd frontend && npx playwright test e2e/core.spec.ts)", "Chromium browser with online/offline control", "Install/update, safe read cache, queued safe mutations, conflicts and blocked high-risk actions pass."),
    "DATA": ("Imports, bulk operations and saved views", "./scripts/staging-e2e.sh && (cd frontend && npx playwright test e2e/core.spec.ts)", "Large representative import files and PostgreSQL", "Preview/commit atomicity, duplicate/error reporting, bounded bulk actions, search and saved views pass."),
    "JOB": ("Background jobs and schedules", "./scripts/staging-e2e.sh", "Redis, Celery worker and Beat running", "Async imports/reports/campaigns expose progress, retry safely, deduplicate and recover from transient failure."),
    "API": ("API and webhook contract acceptance", "./scripts/staging-e2e.sh && python scripts/generate-openapi.py && python -m unittest qa.test_openapi_contract", "Staging services and provider sandboxes", "Runtime routes match OpenAPI; pagination/errors/idempotency and signed webhook replay pass."),
    "SEC": ("Application security acceptance", "pip-audit -r backend/requirements.txt && (cd frontend && npm audit --audit-level=high) && trivy image --severity HIGH,CRITICAL --ignore-unfixed lodgeflow-backend:release && trivy image --severity HIGH,CRITICAL --ignore-unfixed lodgeflow-frontend:release", "Production-like TLS proxy plus dependency/container and DAST scanners", "Tenant/RBAC negatives, CSRF/CSP/headers, rate limits, upload attacks and scans have no open High/Critical defects."),
    "PRIV": ("Privacy, retention and integrity", "./scripts/staging-e2e.sh", "PostgreSQL copy with aged test records and separate approver roles", "Export/anonymize/retention jobs preserve protected records, produce audit evidence and respect legal holds."),
    "UX": ("Responsive accessibility and design acceptance", "(cd frontend && npx playwright test e2e/core.spec.ts)", "Desktop/tablet/mobile browsers and axe", "Keyboard, focus, contrast, reduced motion, zoom, empty/error/loading states and breakpoints pass."),
    "PERF": ("Reference load and availability targets", "LOAD_BASE_URL=https://staging.example.test LOAD_TEST_USERNAME=... LOAD_TEST_PASSWORD=... LOAD_LODGE_ID=... python scripts/load-test.py", "Production-sized staging dataset and monitoring", "Documented p95/error/LCP/throughput targets pass without tenant leakage or job starvation."),
    "OBS": ("Observability and operational monitoring", "./scripts/staging-e2e.sh && PUBLIC_BASE_URL=https://staging.example.test ALERT_WEBHOOK_URL=... python scripts/ops-monitor.py", "Log/metric sink and alert receiver", "Structured redacted logs, request IDs, health/readiness, backup age, disk/TLS and alert delivery pass."),
    "DR": ("Encrypted backup and disaster recovery", "./scripts/verify-backup-restore.sh", "Isolated Docker recovery host and off-site backup destination", "A fresh encrypted backup restores database and private storage; checksums, sentinel, RPO/RTO and readiness pass."),
    "DEV": ("Build, deployment and rollback", "./scripts/deploy-production.sh", "Clean staging host, immutable image registry and rollback image", "Lock-resolved builds, migrations, non-root health, secret injection, rollout and rollback rehearsal pass."),
    "QA": ("Full automated QA and traceability", "./scripts/release-check.sh && (cd frontend && npx playwright test)", "All service dependencies and browsers", "Unit/integration/E2E/security/accessibility suites pass and exact artifact evidence maps every MUST/SHOULD."),
    "UAT": ("Staging UAT and production acceptance", "./scripts/staging-e2e.sh", "Named business, security and operations approvers", "All scripted UAT journeys pass; no P0/P1 defects; formal business/security/operations sign-offs recorded."),
    "DEL": ("Final package and release sign-off", "./scripts/release-check.sh", "Exact release ZIP, scan reports and acceptance evidence", "Checksum, source, migrations, docs, samples, SBOM, licenses, known risks and signed traceability are archived."),
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--checklist", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    requirements = payload.get("requirements", payload)
    if not isinstance(requirements, list):
        raise SystemExit("requirements manifest must contain a list")

    required = [row for row in requirements if str(row.get("level", "")).upper() in {"MUST", "SHOULD"}]
    grouped: dict[str, list[dict]] = {}
    for row in required:
        prefix = str(row.get("id", "")).split("-", 1)[0]
        if prefix not in GATES:
            raise SystemExit(f"no production acceptance gate configured for requirement prefix {prefix!r}")
        grouped.setdefault(prefix, []).append(row)

    generated_at = datetime.now(timezone.utc).isoformat()
    tests = []
    results = []
    checklist_rows = []
    for prefix, rows in sorted(grouped.items(), key=lambda item: min(requirements.index(row) for row in item[1])):
        title, command, prerequisites, exit_criteria = GATES[prefix]
        test_id = f"EXT-{prefix}-PRODUCTION-ACCEPTANCE"
        anchor = slug(f"{prefix} {title}")
        must = sum(str(row.get("level", "")).upper() == "MUST" for row in rows)
        should = len(rows) - must
        tests.append(
            {
                "id": test_id,
                "kind": "uat",
                "requirements": [str(row["id"]) for row in rows],
                "title": title,
                "command": command,
                "prerequisites": prerequisites,
                "exit_criteria": exit_criteria,
            }
        )
        results.append(
            {
                "id": test_id,
                "status": "BLOCKED_EXTERNAL",
                "evidence": f"docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md#{anchor}",
                "detail": f"Not executable in the packaging workspace. Requires: {prerequisites}.",
            }
        )
        checklist_rows.append((prefix, title, rows, must, should, command, prerequisites, exit_criteria, anchor))

    registry = {"schema_version": 2, "generated_at": generated_at, "tests": tests}
    result_payload = {
        "schema_version": 2,
        "generated_at": generated_at,
        "summary": {"blocked_external": len(results), "pass": 0, "fail": 0},
        "tests": results,
    }
    Path(args.registry).write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(args.results).write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# External Production Acceptance Checklist",
        "",
        "This checklist is generated from the final requirements baseline. Local source, unit, Django/SQLite, typecheck and build results are useful implementation evidence, but they do not replace these production-like gates.",
        "",
        f"Required scope: **{len(required)} requirements** ({sum(r['level']=='MUST' for r in required)} MUST, {sum(r['level']=='SHOULD' for r in required)} SHOULD).",
        "",
        "Production acceptance remains blocked until every gate below is executed against the exact release ZIP and its evidence is archived.",
        "",
    ]
    for prefix, title, rows, must, should, command, prerequisites, exit_criteria, _ in checklist_rows:
        lines.extend(
            [
                f"## {prefix} — {title}",
                "",
                f"Covers {must} MUST and {should} SHOULD requirements: `" + "`, `".join(str(row["id"]) for row in rows) + "`.",
                "",
                f"Prerequisites: {prerequisites}.",
                "",
                "Run:",
                "",
                "```bash",
                command,
                "```",
                "",
                f"Exit criteria: {exit_criteria}",
                "",
                "Evidence to archive: command log, environment/image identifiers, timestamp, operator, result, defects and approver sign-off.",
                "",
            ]
        )
    Path(args.checklist).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
