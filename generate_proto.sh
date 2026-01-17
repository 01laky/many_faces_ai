#!/bin/bash

# Script to generate Python gRPC code from .proto files
# This script uses grpc_tools.protoc to generate Python stubs from proto definitions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Generating Python gRPC code from .proto files..."

# Create proto output directory if it doesn't exist
mkdir -p proto

# Generate Python code from proto files
# --python_out: output directory for generated Python code
# --grpc_python_out: output directory for generated gRPC Python code
# --proto_path: directory where proto files are located
python3 -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    --proto_path=proto \
    proto/health.proto

echo "✅ Python gRPC code generated successfully!"
echo "   Generated files:"
echo "   - proto/health_pb2.py"
echo "   - proto/health_pb2_grpc.py"
