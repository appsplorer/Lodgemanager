$ErrorActionPreference = "Stop"
Write-Host "1/5 Compose configuration" -ForegroundColor Cyan
docker compose --env-file .env.local -f docker-compose.local.yml config --quiet
Write-Host "2/5 Django checks" -ForegroundColor Cyan
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py check
Write-Host "3/5 Migration drift" -ForegroundColor Cyan
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py makemigrations --check --dry-run
Write-Host "4/5 Django integration tests" -ForegroundColor Cyan
docker compose --env-file .env.local -f docker-compose.local.yml exec -T backend python manage.py test platform_core --verbosity 1
Write-Host "5/5 Frontend typecheck + production build" -ForegroundColor Cyan
docker compose --env-file .env.local -f docker-compose.local.yml run --rm frontend sh -lc "npm install && npm run check:syntax && npm run typecheck && npm run build"
Write-Host "All automated local QA commands completed successfully." -ForegroundColor Green
