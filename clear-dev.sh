#!/bin/bash

# Script to completely remove AI Demo gRPC server container and volumes
# Usage: ./clear-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧹 Clearing AI Demo gRPC server containers and volumes..."

cd ..
docker-compose -f docker-compose.dev.yml stop ai-demo-dev 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev 2>/dev/null || true
docker rm -f ai-demo-dev 2>/dev/null || true

echo "✅ AI Demo gRPC server containers and volumes cleared"
