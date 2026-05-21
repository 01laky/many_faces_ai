#!/bin/sh
set -e

SNAPSHOT="${HOST_PROFILE_INJECTED_PATH:-/app/injected/host_profile_injected.json}"
mkdir -p "$(dirname "$SNAPSHOT")"

echo "ai-demo-dev: ensuring host profile snapshot..."
HOST_PROFILE_SNAPSHOT="$SNAPSHOT" python /app/scripts/run_host_profile_init.py || true
if [ ! -s "$SNAPSHOT" ]; then
  python /app/scripts/refresh_host_snapshot.py -o "$SNAPSHOT" || true
fi

exec python -m server
