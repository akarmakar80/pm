Set-Location (Join-Path $PSScriptRoot "..")
docker compose up -d --build
Write-Host "Study Hub running at http://localhost:3000"
