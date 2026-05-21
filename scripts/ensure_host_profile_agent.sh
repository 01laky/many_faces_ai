#!/usr/bin/env bash
# Start host-profile-agent on the physical machine (Mac/Windows host Python).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${HOST_PROFILE_AGENT_PORT:-9765}"
SNAPSHOT_DIR="${HOST_PROFILE_SNAPSHOT_DIR:-$ROOT/.host-profile-snapshot.d}"
PID_FILE="${HOST_PROFILE_AGENT_PID_FILE:-/tmp/mfai-host-profile-agent.pid}"
LOG_FILE="${HOST_PROFILE_AGENT_LOG_FILE:-/tmp/mfai-host-profile-agent.log}"

if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "host-profile-agent already running on port ${PORT}"
  exit 0
fi

if [ -f "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "host-profile-agent already running (pid ${old_pid})"
    exit 0
  fi
fi

if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "No host Python found — skipping host-profile-agent" >&2
  exit 0
fi

mkdir -p "$SNAPSHOT_DIR"
export HOST_PROFILE_SNAPSHOT_DIR="$SNAPSHOT_DIR"
nohup "$PY" "$ROOT/scripts/host_profile_agent.py" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.5
if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "host-profile-agent started on port ${PORT} (log: ${LOG_FILE})"
else
  echo "host-profile-agent failed to start — see ${LOG_FILE}" >&2
  exit 1
fi
