#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.local}"; export ENV_FILE
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.local.yml}"; export COMPOSE_FILES
C=(docker compose --env-file "$ENV_FILE" -f docker-compose.local.yml)
KEY_FILE="${BACKUP_ENCRYPTION_PASSWORD_FILE:-$ROOT/.backup-test-key}"
export BACKUP_ENCRYPTION_PASSWORD_FILE="$KEY_FILE"
if [[ ! -f "$KEY_FILE" ]]; then
  umask 077; printf '%s' "$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)" > "$KEY_FILE"
  CLEAN_KEY=1
else CLEAN_KEY=0
fi
TMPDIR_BACKUP="$(mktemp -d)"
cleanup(){ rm -rf "$TMPDIR_BACKUP"; [[ "$CLEAN_KEY" == 1 ]] && rm -f "$KEY_FILE"; }
trap cleanup EXIT

SENTINEL="restore-sentinel-$(date +%s)@example.test"
"${C[@]}" exec -T backend python manage.py shell -c "from platform_core.models import Tenant,Member; t=Tenant.objects.first(); assert t; Member.objects.create(tenant=t,first_name='Restore',last_name='Sentinel',email='$SENTINEL')"
BACKUP="$(./scripts/backup.sh "$TMPDIR_BACKUP")"
"${C[@]}" exec -T backend python manage.py shell -c "from platform_core.models import Member; Member.objects.filter(email='$SENTINEL').delete(); assert not Member.objects.filter(email='$SENTINEL').exists()"
RESTORE_CONFIRM=RESTORE ./scripts/restore.sh "$BACKUP"
"${C[@]}" exec -T backend python manage.py shell -c "from platform_core.models import Member; assert Member.objects.filter(email='$SENTINEL').exists(); print('Representative restored record verified')"
echo "Encrypted backup -> destructive restore drill passed."
