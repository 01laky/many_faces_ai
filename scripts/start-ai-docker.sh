#!/usr/bin/env bash
# Start ai-demo-dev; entrypoint refreshes host profile snapshot automatically.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MONO_ROOT="$(cd "$ROOT/.." && pwd)"
COMPOSE_FILE="${AI_COMPOSE_FILE:-$MONO_ROOT/docker-compose.dev.yml}"

docker compose -f "$COMPOSE_FILE" up -d ai-demo-dev
