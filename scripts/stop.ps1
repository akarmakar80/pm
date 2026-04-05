$root = Split-Path $PSScriptRoot -Parent
Write-Host "Stopping PM Docker stack..."
docker-compose -f "$root\docker-compose.yml" down
Write-Host "Stopped."