#!/usr/bin/env bash
# Collect host hardware snapshot before ai-demo-dev starts (Option A: Docker + real host info).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${HOST_PROFILE_SNAPSHOT_FILE:-$ROOT/.host-profile-snapshot.d/host_profile_injected.json}"

if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "No python interpreter found for host profile snapshot" >&2
  exit 1
fi

"$PY" "$ROOT/scripts/collect_host_snapshot.py" -o "$OUT"
