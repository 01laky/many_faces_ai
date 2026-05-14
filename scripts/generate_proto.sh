#!/bin/bash
# Generate Python gRPC stubs from many_faces_proto (health contract) into proto/

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=python3
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
fi

PROTO_ROOT="${ROOT}/many_faces_proto/proto"
if [[ ! -d "$PROTO_ROOT" ]]; then
  echo "error: many_faces_proto not found at ${PROTO_ROOT}. Run: git submodule update --init --recursive (nested Strategy B)." >&2
  exit 1
fi

echo "Generating gRPC Python code from ${PROTO_ROOT}/health.proto (using $PY)..."
"$PY" -m grpc_tools.protoc \
  -I "$PROTO_ROOT" \
  --python_out=proto \
  --grpc_python_out=proto \
  health.proto
echo "Done: proto/health_pb2.py, proto/health_pb2_grpc.py"
