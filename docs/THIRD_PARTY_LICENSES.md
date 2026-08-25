# Third-Party Dependency Licence Inventory

This file records the declared application dependencies. The release pipeline must produce a resolved transitive dependency/SBOM and verify licence/advisory status before production sign-off; this source-level inventory is not a substitute for that scan.

| Component | Declared version | Ecosystem | Typical upstream licence* |
|---|---:|---|---|
| Django | 5.2.17 | PyPI | BSD-3-Clause |
| gunicorn | 23.0.0 | PyPI | MIT |
| psycopg | 3.2.10 | PyPI | LGPL-3.0-or-later |
| Celery | 5.6.2 | PyPI | BSD-3-Clause |
| redis-py | 6.4.0 | PyPI | MIT |
| cryptography | 45.0.7 | PyPI | Apache-2.0 OR BSD-3-Clause |
| openpyxl | 3.1.5 | PyPI | MIT |
| ReportLab | 4.4.3 | PyPI | BSD-3-Clause |
| Requests | 2.32.5 | PyPI | Apache-2.0 |
| Stripe Python | 12.5.0 | PyPI | MIT |
| django-redis | 6.0.0 | PyPI | BSD-3-Clause |
| django-storages | 1.14.6 | PyPI | BSD-3-Clause |
| boto3 | 1.40.21 | PyPI | Apache-2.0 |
| Sentry SDK | 2.35.0 | PyPI | BSD-2-Clause |
| pypdf | 5.9.0 | PyPI | BSD-3-Clause |
| Next.js | 16.3.0 | npm | MIT |
| React / React DOM | 19.2.0 | npm | MIT |
| TypeScript | 5.8.3 | npm | Apache-2.0 |
| Playwright test | 1.55.0 | npm | Apache-2.0 |
| axe-core Playwright | 4.10.2 | npm | MPL-2.0 |

\* Licence labels are an operator convenience and must be confirmed against the exact resolved package metadata/licence files in the release SBOM before distribution.
