#!/bin/bash

# Script to start Many Faces AI gRPC server in development mode
# Usage: ./start-dev.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🚀 Starting Many Faces AI gRPC server..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Generate proto files if they don't exist
# Note: Proto generation happens in Docker container during build
# If files don't exist locally, they will be generated in the container
if [ ! -f "proto/health_pb2.py" ] || [ ! -f "proto/health_pb2_grpc.py" ]; then
    echo "⚠️  Proto files not found locally. They will be generated in Docker container during build."
    echo "   This is normal - proto generation happens in Dockerfile.dev"
fi

# Start container using root docker-compose
echo "📦 Starting container with docker-compose..."
cd ..
docker-compose -f docker-compose.dev.yml up -d ai-demo-dev

echo ""
echo "⏳ Waiting for server to start..."
sleep 3

# Check if server is running
if docker ps | grep -q ai-demo-dev; then
    echo "✅ Many Faces AI gRPC server started successfully!"
    echo ""
    echo "📋 Server information:"
    echo "   Container: ai-demo-dev"
    echo "   Port: 50051"
    echo "   gRPC Address: localhost:50051"
    echo ""
    echo "💡 Useful commands:"
    echo "   - View logs: docker-compose -f docker-compose.dev.yml logs -f ai-demo-dev"
    echo "   - Stop: docker-compose -f docker-compose.dev.yml stop ai-demo-dev"
    echo "   - Restart: docker-compose -f docker-compose.dev.yml restart ai-demo-dev"
else
    echo "⚠️  Server may still be starting. Check logs:"
    echo "   docker-compose -f docker-compose.dev.yml logs ai-demo-dev"
fi
