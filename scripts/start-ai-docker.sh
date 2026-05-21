#!/usr/bin/env bash
# Collect host snapshot, then start ai-demo-dev from monorepo root compose file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MONO_ROOT="$(cd "$ROOT/.." && pwd)"
COMPOSE_FILE="${AI_COMPOSE_FILE:-$MONO_ROOT/docker-compose.dev.yml}"

"$ROOT/scripts/collect_host_snapshot.sh"

docker compose -f "$COMPOSE_FILE" up -d ai-demo-dev
