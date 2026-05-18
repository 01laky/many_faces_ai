#!/bin/bash

# rebuild-dev.sh - Rebuild Many Faces AI Docker image
#
# Default: Docker layer cache (fast; Ollama model cache is outside this image).
# Full rebuild: ./rebuild-dev.sh --no-cache
#
# Code-only changes: docker compose restart ai-demo-dev (bind mounts in parent compose).

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NO_CACHE=""
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE="--no-cache"
  echo "🧹 Full rebuild (--no-cache)..."
  docker images | grep -E "many_faces_ai|ai-demo|soft-ai" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
else
  echo "🔨 Rebuilding (cache OK; Ollama model cache is outside this image)..."
fi

cd ..
docker-compose -f docker-compose.dev.yml build $NO_CACHE ai-demo-dev

echo ""
echo "✅ Done. Start: cd many_faces_ai && ./scripts/start-dev.sh"
