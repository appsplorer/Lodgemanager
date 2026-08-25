$ErrorActionPreference = "Stop"
if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.local.example" ".env.local"
    Write-Host "Created .env.local from .env.local.example" -ForegroundColor Yellow
}
docker compose --env-file .env.local -f docker-compose.local.yml up --build -d
docker compose --env-file .env.local -f docker-compose.local.yml ps
Write-Host "LodgeFlow: http://localhost:3000" -ForegroundColor Green
Write-Host "API health: http://localhost:8000/api/health/" -ForegroundColor Green
Write-Host "Mailpit: http://localhost:8025" -ForegroundColor Green
