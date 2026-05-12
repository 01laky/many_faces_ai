#!/bin/bash

# Script to completely remove Many Faces AI gRPC server container and volumes
# Usage: ./clear-dev.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🧹 Clearing Many Faces AI gRPC server containers and volumes..."

cd ..
docker-compose -f docker-compose.dev.yml stop ai-demo-dev 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev 2>/dev/null || true
docker rm -f ai-demo-dev 2>/dev/null || true

echo "✅ Many Faces AI gRPC server containers and volumes cleared"
