$ErrorActionPreference = "Stop"
Write-Host "This deletes the LOCAL LodgeFlow PostgreSQL/Redis/media volumes." -ForegroundColor Yellow
$answer = Read-Host "Type RESET to continue"
if ($answer -ne "RESET") { Write-Host "Cancelled"; exit 0 }
docker compose --env-file .env.local -f docker-compose.local.yml down -v --remove-orphans
docker compose --env-file .env.local -f docker-compose.local.yml up --build -d
