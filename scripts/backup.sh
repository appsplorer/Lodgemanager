#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.prod.yml}"
DEST="${1:-./backups}"
KEY_FILE="${BACKUP_ENCRYPTION_PASSWORD_FILE:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-35}"
[[ -f "$ENV_FILE" ]] || { echo "Missing environment file: $ENV_FILE" >&2; exit 2; }
[[ -n "$KEY_FILE" && -f "$KEY_FILE" ]] || { echo "BACKUP_ENCRYPTION_PASSWORD_FILE must point to a readable secret file" >&2; exit 2; }
[[ "$RETENTION_DAYS" =~ ^[0-9]+$ && "$RETENTION_DAYS" -ge 1 ]] || { echo "BACKUP_RETENTION_DAYS must be a positive integer" >&2; exit 2; }
mkdir -p "$DEST"; chmod 700 "$DEST" 2>/dev/null || true
DEST="$(cd "$DEST" && pwd -P)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE="$DEST/lodgeflow-$STAMP.backup"
mkdir "$BUNDLE"; chmod 700 "$BUNDLE"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lodgeflow-backup.XXXXXX")"
cleanup(){ rm -rf -- "$TMP_DIR"; }
trap cleanup EXIT

C=(docker compose --env-file "$ENV_FILE")
IFS=':' read -r -a _files <<< "$COMPOSE_FILES"
for f in "${_files[@]}"; do C+=(-f "$f"); done

SENTINEL="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
printf '%s\n' "$SENTINEL" > "$BUNDLE/sentinel.txt"; chmod 600 "$BUNDLE/sentinel.txt"
"${C[@]}" exec -T backend python manage.py backup_sentinel create --token "$SENTINEL" >/dev/null

DB_TMP="$TMP_DIR/database.dump"
"${C[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DB_TMP"
[[ -s "$DB_TMP" ]] || { echo "Database backup is empty" >&2; exit 1; }
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$DB_TMP" -out "$BUNDLE/database.dump.enc"
chmod 600 "$BUNDLE/database.dump.enc"
(cd "$BUNDLE" && sha256sum database.dump.enc > database.dump.enc.sha256); chmod 600 "$BUNDLE/database.dump.enc.sha256"

MEDIA_MODE="${BACKUP_MEDIA_MODE:-auto}"
if [[ "$MEDIA_MODE" == auto ]]; then
  MEDIA_MODE="$("${C[@]}" exec -T backend python manage.py storage_inventory --mode-only | tr -d '\r\n')"
fi
case "$MEDIA_MODE" in
  local)
    MEDIA_TMP="$TMP_DIR/media.tar"
    "${C[@]}" exec -T backend tar -C /app/media -cf - . > "$MEDIA_TMP"
    [[ -s "$MEDIA_TMP" ]] || { echo "Local media archive is empty or unavailable" >&2; exit 1; }
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$MEDIA_TMP" -out "$BUNDLE/media.tar.enc"
    chmod 600 "$BUNDLE/media.tar.enc"
    (cd "$BUNDLE" && sha256sum media.tar.enc > media.tar.enc.sha256); chmod 600 "$BUNDLE/media.tar.enc.sha256"
    python scripts/backup_manifest.py create --bundle "$BUNDLE" --media-mode local --artifact database=database.dump.enc --artifact media=media.tar.enc --artifact sentinel=sentinel.txt >/dev/null
    ;;
  s3)
    INVENTORY_TMP="$TMP_DIR/s3-inventory.json"
    "${C[@]}" exec -T backend python manage.py storage_inventory > "$INVENTORY_TMP"
    python -m json.tool "$INVENTORY_TMP" >/dev/null
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass file:"$KEY_FILE" -in "$INVENTORY_TMP" -out "$BUNDLE/s3-inventory.json.enc"
    chmod 600 "$BUNDLE/s3-inventory.json.enc"
    (cd "$BUNDLE" && sha256sum s3-inventory.json.enc > s3-inventory.json.enc.sha256); chmod 600 "$BUNDLE/s3-inventory.json.enc.sha256"
    python scripts/backup_manifest.py create --bundle "$BUNDLE" --media-mode s3 --artifact database=database.dump.enc --artifact s3_inventory=s3-inventory.json.enc --artifact sentinel=sentinel.txt >/dev/null
    ;;
  *) echo "BACKUP_MEDIA_MODE must be auto, local or s3" >&2; exit 2 ;;
esac

python scripts/backup_manifest.py verify --bundle "$BUNDLE" >/dev/null
printf '{"backup":"%s","created_at":"%s","media_mode":"%s"}\n' "$BUNDLE" "$STAMP" "$MEDIA_MODE" > "$DEST/latest-success.json"
chmod 600 "$DEST/latest-success.json"

if [[ -n "${BACKUP_TRANSFER_EXECUTABLE:-}" ]]; then
  [[ -x "$BACKUP_TRANSFER_EXECUTABLE" ]] || { echo "BACKUP_TRANSFER_EXECUTABLE is not executable" >&2; exit 2; }
  "$BACKUP_TRANSFER_EXECUTABLE" "$BUNDLE"
fi

find "$DEST" -mindepth 1 -maxdepth 1 -type d -name 'lodgeflow-*.backup' -mtime "+$RETENTION_DAYS" -exec rm -rf -- {} +
printf '%s\n' "$BUNDLE"
