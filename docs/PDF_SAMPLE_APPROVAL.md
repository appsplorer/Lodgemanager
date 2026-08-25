# Representative PDF Sample Approval Pack

These files contain synthetic/non-PII fixture data and are included for contractual document visual QA. Seven samples are rendered through the production `platform_core.services.pdfs` functions; the management-pack fixture reproduces the runtime R-001 visual/report contract without requiring a live Django database.

| File | Pages | Bytes | SHA-256 | visual QA |
|---|---:|---:|---|---|
| `attendance-sheet.pdf` | 1 | 2515 | `1d18c6a287748d4b906ab2afa28c968e8858ed9770d07750309daba0ff317b6d` | Local visual QA passed; staging/UAT approval pending |
| `meeting-pack.pdf` | 4 | 5298 | `0afc5b0f835ad71850344ad80f40701b107617363283653e014453b9330bac72` | Local visual QA passed; staging/UAT approval pending |
| `member-statement.pdf` | 1 | 2610 | `b031e0260b609eb7ac5720b8a2ff8fbf2d8ed91531672355fa031e0b3510f900` | Local visual QA passed; staging/UAT approval pending |
| `minutes.pdf` | 1 | 2807 | `a3bfa9dec6a6cb53c25cac079d7626dba361546b8912a77ea078e544546a2648` | Local visual QA passed; staging/UAT approval pending |
| `monthly-management-pack.pdf` | 1 | 3039 | `e2c18dc8acdf5f4d16ede5503c07926a8d2cbd3494efab03e684ecab273c3238` | Local visual QA passed; staging/UAT approval pending |
| `officer-roster.pdf` | 1 | 2388 | `13133e2d5ccfb317a39fae18808a2dfc563fb76b1c88a7ec5e8d07a65e08e9ad` | Local visual QA passed; staging/UAT approval pending |
| `receipt.pdf` | 1 | 2525 | `96e5c9a2d2a3ed57f51d10b38ddf5438813e5546e9a797fd5e3abc0f48dab938` | Local visual QA passed; staging/UAT approval pending |
| `summons.pdf` | 1 | 2483 | `46b2c51a6497cd6060d2e3e22d9f530e72cb7443c88ec8d809d03b8db8657c2f` | Local visual QA passed; staging/UAT approval pending |

Production UAT must separately approve PDFs generated from the staging application because these local samples do not replace runtime acceptance.
