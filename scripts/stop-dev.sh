#!/bin/bash

# Script to stop Many Faces AI gRPC server
# Usage: ./stop-dev.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🛑 Stopping Many Faces AI gRPC server..."

cd ..
docker-compose -f docker-compose.dev.yml stop ai-demo-dev 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev 2>/dev/null || true
docker rm -f ai-demo-dev 2>/dev/null || true

echo "✅ Many Faces AI gRPC server stopped and removed"
