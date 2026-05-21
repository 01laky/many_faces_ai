# Start ai-demo-dev; compose init service collects host profile automatically.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$MonoRoot = Split-Path -Parent $Root
$ComposeFile = if ($env:AI_COMPOSE_FILE) { $env:AI_COMPOSE_FILE } else { Join-Path $MonoRoot "docker-compose.dev.yml" }
$ComposeWindows = Join-Path $MonoRoot "docker-compose.ai-windows.yml"

$ComposeArgs = @("-f", $ComposeFile)
if (Test-Path $ComposeWindows) {
    $ComposeArgs += @("-f", $ComposeWindows)
}
$ComposeArgs += @("up", "-d", "--build", "ai-demo-dev")

docker compose @ComposeArgs
