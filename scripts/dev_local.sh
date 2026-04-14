#!/usr/bin/env bash
# Start the full local stack in Docker (LocalStack + cafe + image + static web).
# Python deps are installed during image build (see services/*/Dockerfile).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and run this script again."
  exit 1
fi

echo "Building and starting containers..."
docker compose up --build -d

cat <<EOF

--- Stack is up ---

  Static site:  http://127.0.0.1:3000/add.html
  Cafe API:     http://127.0.0.1:8000/health
  Image API:    http://127.0.0.1:8002/docs  (FastAPI OpenAPI)
  LocalStack:   http://localhost:4566

  Logs:         docker compose logs -f
  Stop:         docker compose down

Auth still uses authUrl from web/api-config.js (deployed Lambda) unless you change it.

Optional (seed LocalStack from host after compose is up):
  bash scripts/localstack_setup_resources.sh
  See docs/localstack.md and tests/README.md

EOF
