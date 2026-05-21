# Collect host snapshot, then start ai-demo-dev from monorepo root compose file.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$MonoRoot = Split-Path -Parent $Root
$ComposeFile = if ($env:AI_COMPOSE_FILE) { $env:AI_COMPOSE_FILE } else { Join-Path $MonoRoot "docker-compose.dev.yml" }

& (Join-Path $PSScriptRoot "collect-host-profile.ps1")
docker compose -f $ComposeFile up -d ai-demo-dev
