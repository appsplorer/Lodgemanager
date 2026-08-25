#!/usr/bin/env bash
set -euo pipefail
docker compose --env-file .env.local -f docker-compose.local.yml config --quiet
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py check
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py test platform_core --verbosity 1
docker compose --env-file .env.local -f docker-compose.local.yml run --rm frontend sh -lc 'npm ci && npm run check:syntax && npm run typecheck && npm run build'
