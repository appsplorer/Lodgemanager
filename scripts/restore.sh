#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 /path/to/lodgeflow-TIMESTAMP.backup" >&2; exit 2; }
BUNDLE="$1"
[[ -d "$BUNDLE" ]] || { echo "Backup bundle not found: $BUNDLE" >&2; exit 2; }
BUNDLE="$(cd "$BUNDLE" && pwd -P)"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.prod.yml}"
KEY_FILE="${BACKUP_ENCRYPTION_PASSWORD_FILE:-}"
[[ -f "$ENV_FILE" ]] || { echo "Missing environment file: $ENV_FILE" >&2; exit 2; }
[[ -n "$KEY_FILE" && -f "$KEY_FILE" ]] || { echo "BACKUP_ENCRYPTION_PASSWORD_FILE must point to a readable secret file" >&2; exit 2; }

# Every checksum, required artifact and safe relative path is verified before the
# destructive confirmation or any database/storage mutation.
python scripts/backup_manifest.py verify --bundle "$BUNDLE" >/dev/null
(cd "$BUNDLE" && sha256sum -c database.dump.enc.sha256)
DB_FILE="$(python scripts/backup_manifest.py artifact --bundle "$BUNDLE" --type database)"
SENTINEL_FILE="$(python scripts/backup_manifest.py artifact --bundle "$BUNDLE" --type sentinel)"
SENTINEL="$(tr -d '\r\n' < "$SENTINEL_FILE")"
MEDIA_MODE="$(python - "$BUNDLE/manifest.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8'))['media_mode'])
PY
)"

OK="${RESTORE_CONFIRM:-}"
if [[ "$OK" != RESTORE ]]; then
  read -r -p "Restore will replace the LodgeFlow database and recovery storage. Type RESTORE to continue: " OK
fi
[[ "$OK" == RESTORE ]] || { echo "Restore cancelled" >&2; exit 1; }

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lodgeflow-restore.XXXXXX")"
cleanup(){ rm -rf -- "$TMP_DIR"; }
trap cleanup EXIT
DB_TMP="$TMP_DIR/database.dump"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$DB_FILE" -out "$DB_TMP"
[[ -s "$DB_TMP" ]] || { echo "Decrypted database backup is empty" >&2; exit 1; }

C=(docker compose --env-file "$ENV_FILE")
IFS=':' read -r -a _files <<< "$COMPOSE_FILES"
for f in "${_files[@]}"; do C+=(-f "$f"); done

if [[ "$MEDIA_MODE" == local ]]; then
  (cd "$BUNDLE" && sha256sum -c media.tar.enc.sha256)
  MEDIA_FILE="$(python scripts/backup_manifest.py artifact --bundle "$BUNDLE" --type media)"
  MEDIA_TMP="$TMP_DIR/media.tar"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$MEDIA_FILE" -out "$MEDIA_TMP"
  python scripts/validate-backup-tar.py "$MEDIA_TMP"
elif [[ "$MEDIA_MODE" == s3 ]]; then
  (cd "$BUNDLE" && sha256sum -c s3-inventory.json.enc.sha256)
  INVENTORY_FILE="$(python scripts/backup_manifest.py artifact --bundle "$BUNDLE" --type s3_inventory)"
  INVENTORY_TMP="$TMP_DIR/s3-inventory.json"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$INVENTORY_FILE" -out "$INVENTORY_TMP"
  python -m json.tool "$INVENTORY_TMP" >/dev/null
  [[ -n "${BACKUP_S3_RESTORE_EXECUTABLE:-}" && -x "$BACKUP_S3_RESTORE_EXECUTABLE" ]] || { echo "S3 recovery requires an executable BACKUP_S3_RESTORE_EXECUTABLE" >&2; exit 2; }
else
  echo "Unsupported media mode: $MEDIA_MODE" >&2; exit 2
fi

"${C[@]}" stop backend worker beat frontend proxy >/dev/null 2>&1 || true
"${C[@]}" up -d db redis
cat "$DB_TMP" | "${C[@]}" exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges'
if [[ "$MEDIA_MODE" == local ]]; then
  cat "$MEDIA_TMP" | "${C[@]}" run --rm --no-deps -T backend sh -c 'find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -C /app/media --no-same-owner --no-same-permissions -xf -'
else
  "$BACKUP_S3_RESTORE_EXECUTABLE" "$INVENTORY_TMP"
fi
"${C[@]}" run --rm migrate
"${C[@]}" up -d backend worker beat frontend proxy
"${C[@]}" exec -T backend python manage.py backup_sentinel verify --token "$SENTINEL"
"${C[@]}" exec -T backend curl -fsS http://127.0.0.1:8000/api/ready/ >/dev/null
echo "Restore completed; database, private-file checksum, migrations and readiness verified."
