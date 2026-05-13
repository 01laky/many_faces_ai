#!/bin/bash
# Generate Python gRPC stubs from proto/health.proto into proto/

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=python3
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
fi

echo "Generating gRPC Python code from proto/health.proto (using $PY)..."
"$PY" -m grpc_tools.protoc \
  -I proto \
  --python_out=proto \
  --grpc_python_out=proto \
  proto/health.proto
echo "Done: proto/health_pb2.py, proto/health_pb2_grpc.py"
