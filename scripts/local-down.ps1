$ErrorActionPreference = "Stop"
docker compose --env-file .env.local -f docker-compose.local.yml down
