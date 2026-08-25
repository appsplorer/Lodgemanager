# LodgeFlow Release Evidence — 2026-08-25

## Scope and baseline

The audited baseline is `Quill_of_the_Craft_Final_Master_Requirements_v1.0`: 298 requirements comprising 258 MUST, 35 SHOULD and 5 MAY rows. The release evidence model never treats implementation presence, source inspection or a successful build as production acceptance.

## Locally executed evidence

| Gate | Result | Evidence |
|---|---:|---|
| Portable source/runtime contracts | 67 passed, 0 failed | `qa/latest-source-test-results.json` |
| Complete Python QA suite | 117 passed, 0 failed | `PYTHONPATH=backend:. python -m pytest -q qa` |
| Django integration/regression | 40 passed, 1 PostgreSQL-only skip | `DEBUG=true DJANGO_SETTINGS_MODULE=lodgeflow.test_settings python manage.py test platform_core` |
| Django checks/migration drift | Pass / no changes | `manage.py check`; `manage.py makemigrations --check --dry-run` |
| Fresh migration path | 0001–0015 applied | Django test database creation log |
| OpenAPI runtime contract | 162 paths, 3 contract tests passed | `docs/openapi.yaml`; `qa/test_openapi_contract.py` |
| TypeScript/TSX syntax | 50 files, 0 errors | `frontend/scripts/parse-tsx.mjs` |
| TypeScript typecheck | Pass | `tsc --noEmit` |
| Next production build | Pass, 22 routes | `next build` |
| Frontend dependency audit | 0 vulnerabilities | `npm audit --audit-level=high` |
| Backend dependency audit | No known vulnerabilities reported | `pip-audit -r backend/requirements.txt` |
| Shell/YAML contracts | Pass | `bash -n scripts/*.sh`; PyYAML parse |
| Traceability completeness | 293/293 required mapped, 0 unmapped | `qa/requirements_traceability.json` |

The local Django harness uses SQLite only to make dependency-backed application behavior executable in this packaging environment. PostgreSQL remains the deployment database and is independently gated because SQLite cannot reproduce `NULLS NOT DISTINCT`, row locks or production concurrency semantics.

## Acceptance state

| State | All 298 | Required only |
|---|---:|---:|
| PASS | 0 | 0 |
| FAIL | 0 | 0 |
| BLOCKED_EXTERNAL | 293 | 293 |
| NOT_RUN | 5 | 0 |

The five NOT_RUN rows are optional MAY extensions. Every MUST and SHOULD row has an owning production-acceptance gate. Production readiness is deliberately false until the exact artifact passes the external checklist.

## Integrity of the evidence model

- Registered result IDs must exist in `qa/acceptance_registry.json`.
- Unknown requirement IDs and duplicate/empty test IDs fail generation.
- PASS without an evidence reference is rejected.
- FAIL/ERROR dominates a requirement result; any blocked external gate prevents PASS.
- The strict traceability mode rejects unmapped required rows and required NOT_RUN rows.
- `scripts/build-release-evidence.py` regenerates the external registry/results/checklist from the baseline rather than relying on hand-edited status claims.

## Promotion procedure

Run every gate in `docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md` against the final ZIP, archive non-secret logs and artifact/image identifiers, then replace each `BLOCKED_EXTERNAL` row with an evidence-backed PASS or FAIL. Regenerate traceability and require `production_ready: true`, no P0/P1 defects, and named business/security/operations sign-off before live deployment.
