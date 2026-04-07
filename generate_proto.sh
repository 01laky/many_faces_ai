#!/bin/bash
# Generate Python gRPC stubs from proto/health.proto into proto/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Generating gRPC Python code from proto/health.proto..."
python3 -m grpc_tools.protoc \
  -I proto \
  --python_out=proto \
  --grpc_python_out=proto \
  proto/health.proto
echo "Done: proto/health_pb2.py, proto/health_pb2_grpc.py"
