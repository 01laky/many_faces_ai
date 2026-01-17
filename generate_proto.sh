#!/bin/bash

# generate_proto.sh - Script to generate Python gRPC code from .proto files
#
# This script uses grpc_tools.protoc to generate Python stubs from proto definitions.
# It generates:
# - health_pb2.py: Protocol buffer message classes
# - health_pb2_grpc.py: gRPC service client and server stubs
#
# Usage:
#   ./generate_proto.sh
#
# Requirements:
#   - Python 3 with grpcio-tools installed
#   - proto/health.proto file must exist

set -e  # Exit on any error

# Get the directory where this script is located
# This allows the script to be run from any directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Generating Python gRPC code from .proto files..."

# Create proto output directory if it doesn't exist
# This ensures the directory structure is ready for generated files
mkdir -p proto

# Generate Python code from proto files using grpc_tools.protoc
# This command generates both protocol buffer and gRPC code
python3 -m grpc_tools.protoc \
    --python_out=. \
        # Output directory for generated Python protocol buffer code (health_pb2.py)
    --grpc_python_out=. \
        # Output directory for generated gRPC Python code (health_pb2_grpc.py)
    --proto_path=proto \
        # Directory where proto files are located (search path for imports)
    proto/health.proto
        # Input proto file to compile

echo "✅ Python gRPC code generated successfully!"
echo "   Generated files:"
echo "   - proto/health_pb2.py        (Protocol buffer message classes)"
echo "   - proto/health_pb2_grpc.py   (gRPC service client and server stubs)"
