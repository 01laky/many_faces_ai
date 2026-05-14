#!/usr/bin/env bash
# Reproduce GitHub Actions checks locally: protos, ruff, pytest (no torch).
# Creates .venv-ci-verify/ on first run (gitignored).
# Usage: ./verify-ci.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pick_python() {
  if [ -n "${PYTHON:-}" ]; then
    echo "$PYTHON"
    return
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    echo python3.11
    return
  fi
  echo python3
}

PY=$(pick_python)
VENVDIR="$ROOT/.venv-ci-verify"
if [ ! -d "$VENVDIR" ]; then
  "$PY" -m venv "$VENVDIR"
fi
PIP="$VENVDIR/bin/pip"
PYEXE="$VENVDIR/bin/python"

echo "🔍 many_faces_ai verify-ci (python: $PY)..."
"$PIP" install -q --upgrade pip setuptools wheel
# Pinned set with wheels for Python 3.11–3.13 (1.60.x often fails to build on 3.13).
"$PIP" install -q ruff pytest \
  grpcio==1.68.1 \
  grpcio-tools==1.68.1 \
  grpcio-testing==1.68.1 \
  protobuf==5.28.3

# gRPC tests import `server.py`, which needs the same ML stack as local dev (CPU wheels).
"$PIP" install -q numpy accelerate "transformers>=4.36" torch --extra-index-url https://download.pytorch.org/whl/cpu

PROTO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/../many_faces_proto/proto"
if [[ ! -f "${PROTO_ROOT}/health.proto" ]]; then
  echo "verify-ci: many_faces_proto missing at ${PROTO_ROOT} — run from monorepo with submodules." >&2
  exit 1
fi
"$PYEXE" -m grpc_tools.protoc -I "$PROTO_ROOT" --python_out=proto --grpc_python_out=proto health.proto

"$VENVDIR/bin/ruff" check .
"$VENVDIR/bin/ruff" format --check .

PYTHONPATH="$ROOT" "$VENVDIR/bin/pytest" test_server.py -q

echo "✅ many_faces_ai verify-ci passed"
