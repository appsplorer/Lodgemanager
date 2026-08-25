#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python}"
NPM_CACHE_DIR="${NPM_CACHE_DIR:-${TMPDIR:-/tmp}/lodgeflow-npm-cache}"
NPM_LOG_DIR="${NPM_LOG_DIR:-${TMPDIR:-/tmp}/lodgeflow-npm-logs}"
mkdir -p "$NPM_CACHE_DIR" "$NPM_LOG_DIR"

"$PYTHON_BIN" -c "import django, yaml, reportlab, pypdf" >/dev/null
"$PYTHON_BIN" -m compileall -q backend scripts qa
"$PYTHON_BIN" scripts/generate-openapi.py
"$PYTHON_BIN" scripts/run-source-tests.py qa/test_offline_release.py --output qa/latest-source-test-results.json
"$PYTHON_BIN" -m unittest discover -s qa -p 'test_*.py' -v

(
  cd backend
  DEBUG=true DJANGO_SETTINGS_MODULE=lodgeflow.test_settings "$PYTHON_BIN" manage.py check
  DEBUG=true DJANGO_SETTINGS_MODULE=lodgeflow.test_settings "$PYTHON_BIN" manage.py makemigrations --check --dry-run
  DEBUG=true DJANGO_SETTINGS_MODULE=lodgeflow.test_settings "$PYTHON_BIN" manage.py test platform_core --verbosity 1
)

"$PYTHON_BIN" scripts/build-release-evidence.py \
  --manifest qa/requirements_manifest.json \
  --registry qa/acceptance_registry.json \
  --results qa/latest-acceptance-results.json \
  --checklist docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md
"$PYTHON_BIN" scripts/generate-traceability.py \
  --manifest qa/requirements_manifest.json \
  --registry qa/acceptance_registry.json \
  --results qa/latest-acceptance-results.json \
  --output qa/requirements_traceability.json \
  --strict

bash -n scripts/*.sh
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import yaml
for path in [Path('docker-compose.local.yml'), Path('docker-compose.prod.yml'), Path('docker-compose.staging.yml'), *Path('.github/workflows').glob('*.yml')]:
    yaml.safe_load(path.read_text(encoding='utf-8'))
    print('YAML OK:', path)
PY

(
  cd frontend
  npm ci --cache "$NPM_CACHE_DIR" --logs-dir "$NPM_LOG_DIR"
  npm run check:syntax
  npm run typecheck
  npm run build
)

echo "Local release-development checks passed. Production acceptance remains governed by docs/EXTERNAL_ACCEPTANCE_CHECKLIST.md."
