# Start ai-demo-dev; entrypoint refreshes host profile snapshot automatically.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$MonoRoot = Split-Path -Parent $Root
$ComposeFile = if ($env:AI_COMPOSE_FILE) { $env:AI_COMPOSE_FILE } else { Join-Path $MonoRoot "docker-compose.dev.yml" }

docker compose -f $ComposeFile up -d ai-demo-dev
