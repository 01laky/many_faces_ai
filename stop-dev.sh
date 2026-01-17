#!/bin/bash

# Script to stop AI Demo gRPC server
# Usage: ./stop-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping AI Demo gRPC server..."

cd ..
docker-compose -f docker-compose.dev.yml stop ai-demo-dev 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev 2>/dev/null || true
docker rm -f ai-demo-dev 2>/dev/null || true

echo "✅ AI Demo gRPC server stopped and removed"
