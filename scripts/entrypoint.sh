#!/bin/sh
set -e

SNAPSHOT="${HOST_PROFILE_INJECTED_PATH:-/app/injected/host_profile_injected.json}"
mkdir -p "$(dirname "$SNAPSHOT")"

echo "ai-demo-dev: refreshing host profile snapshot..."
if python /app/scripts/refresh_host_snapshot.py -o "$SNAPSHOT"; then
  echo "ai-demo-dev: host profile snapshot ready at $SNAPSHOT"
else
  echo "ai-demo-dev: host profile refresh failed — GetHostProfile may use container scope" >&2
fi

exec python -m server
