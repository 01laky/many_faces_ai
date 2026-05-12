#!/bin/bash

# rebuild-dev.sh - Script to rebuild Many Faces AI Docker image from scratch
#
# This script performs a clean rebuild of the Docker image by:
# 1. Removing old Docker images
# 2. Building a fresh image with --no-cache
#
# NOTE: This script only builds images, it does NOT start containers.
# Use ./start-dev.sh to start containers after rebuilding images.
#
# Usage: ./rebuild-dev.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🔨 Rebuilding Many Faces AI Docker image (clean build)..."
echo ""

# Remove old images
echo "🧹 Removing old Docker images..."
docker images | grep -E "many_faces_ai|ai-demo" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Build new image with --no-cache (clean build)
echo "🔨 Building fresh Docker image (no cache)..."
cd ..
docker-compose -f docker-compose.dev.yml build --no-cache ai-demo-dev

echo ""
echo "✅ Rebuild completed!"
echo ""
echo "💡 Note: Containers were not started. Use ./start-dev.sh to start containers."
