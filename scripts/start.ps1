Write-Host "Starting PM Docker stack..."
docker-compose -f "$(Resolve-Path ..\docker-compose.yml)" up --build -d
Write-Host "Started. Backend should be available at http://localhost:8000"