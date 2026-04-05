#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Starting PM Docker stack..."
docker-compose up --build -d

echo "Started. Backend should be available at http://localhost:8000"