Write-Host "Stopping PM Docker stack..."
docker-compose -f "$(Resolve-Path ..\docker-compose.yml)" down
Write-Host "Stopped."