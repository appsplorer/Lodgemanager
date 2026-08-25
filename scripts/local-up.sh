#!/usr/bin/env bash
set -euo pipefail
[[ -f .env.local ]] || cp .env.local.example .env.local
docker compose --env-file .env.local -f docker-compose.local.yml up --build -d
docker compose --env-file .env.local -f docker-compose.local.yml ps
printf '\nLodgeFlow: http://localhost:3000\nAPI health: http://localhost:8000/api/health/\nMailpit: http://localhost:8025\n'
