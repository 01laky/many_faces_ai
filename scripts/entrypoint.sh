#!/bin/sh
set -e

SNAPSHOT="${HOST_PROFILE_INJECTED_PATH:-/app/injected/host_profile_injected.json}"
REQUIRE="${MFAI_REQUIRE_HOST_SNAPSHOT:-0}"
mkdir -p "$(dirname "$SNAPSHOT")"

echo "ai-demo-dev: ensuring host profile snapshot..."
export HOST_PROFILE_SNAPSHOT="$SNAPSHOT"

if ! python /app/scripts/run_host_profile_init.py; then
	if [ "$REQUIRE" = "1" ]; then
		echo "ERROR: Valid Windows host profile snapshot required." >&2
		echo "On the Windows PC run: .\\scripts\\up-ai-windows.ps1" >&2
		exit 1
	fi
fi

if [ ! -s "$SNAPSHOT" ] && [ "$REQUIRE" != "1" ]; then
	python /app/scripts/refresh_host_snapshot.py -o "$SNAPSHOT" || true
fi

if [ "$REQUIRE" = "1" ]; then
	if ! python /app/scripts/refresh_host_snapshot.py -o "$SNAPSHOT"; then
		echo "ERROR: Host profile snapshot is missing or invalid (scope must be host)." >&2
		echo "On the Windows PC run: .\\scripts\\up-ai-windows.ps1" >&2
		exit 1
	fi
fi

# 7B-perf O19: best-effort warm-up of the small helper model. Never fails startup
# (the script always exits 0; `|| true` is belt-and-suspenders). The host Ollama
# model store persists across rebuilds, so this only pulls when genuinely absent.
python /app/scripts/pull_helper_model.py || true

exec python -m server
