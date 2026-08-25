#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.prod.yml}"
COMPOSE=(docker compose --env-file "$ENV_FILE")
IFS=':' read -r -a _files <<< "$COMPOSE_FILES"
for f in "${_files[@]}"; do COMPOSE+=(-f "$f"); done

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 2; }
if grep -Eq 'replace-with|app\.yourdomain\.com|staging\.yourdomain\.com|noreply@yourdomain\.com' "$ENV_FILE"; then
  echo "Refusing deployment: placeholder values remain in $ENV_FILE" >&2; exit 2
fi

"${COMPOSE[@]}" config -q
"${COMPOSE[@]}" build --pull
"${COMPOSE[@]}" run --rm --no-deps backend python manage.py check --deploy --fail-level WARNING
"${COMPOSE[@]}" run --rm --no-deps backend python manage.py makemigrations --check --dry-run
"${COMPOSE[@]}" run --rm --no-deps backend python manage.py collectstatic --noinput

# Migration is a controlled one-shot service. The backend is not allowed to become
# healthy until it has completed successfully.
"${COMPOSE[@]}" up -d db redis clamav
"${COMPOSE[@]}" up migrate
"${COMPOSE[@]}" up -d --remove-orphans backend worker beat frontend proxy

PORT="$(python - "$ENV_FILE" <<'PYPORT'
import sys
p='8080'
for line in open(sys.argv[1]):
 if line.startswith('APP_HTTP_PORT='): p=line.split('=',1)[1].strip() or p
print(p)
PYPORT
)"
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null \
     && "${COMPOSE[@]}" exec -T backend curl -fsS http://127.0.0.1:8000/api/ready/ >/dev/null; then
    echo "LodgeFlow proxy and backend health checks passed on 127.0.0.1:${PORT}"
    exit 0
  fi
  sleep 2
done
"${COMPOSE[@]}" ps
"${COMPOSE[@]}" logs --tail=120 backend frontend proxy worker beat || true
echo "Health check failed" >&2
exit 1
