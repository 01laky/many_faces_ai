#!/usr/bin/env bash
# Reproduce GitHub Actions checks locally: protos, ruff, pytest (no torch).
# Creates .venv-ci-verify/ on first run (gitignored).
# Usage: ./verify-ci.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

echo "🔍 ai_demo verify-ci (python: $PY)..."
"$PIP" install -q --upgrade pip setuptools wheel
# Pinned set with wheels for Python 3.11–3.13 (1.60.x often fails to build on 3.13).
"$PIP" install -q ruff pytest \
  grpcio==1.68.1 \
  grpcio-tools==1.68.1 \
  grpcio-testing==1.68.1 \
  protobuf==5.28.3

"$PYEXE" -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/health.proto

"$VENVDIR/bin/ruff" check .
"$VENVDIR/bin/ruff" format --check .

PYTHONPATH="$ROOT" "$VENVDIR/bin/pytest" test_server.py -q

echo "✅ ai_demo verify-ci passed"
