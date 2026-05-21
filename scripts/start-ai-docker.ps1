# Start ai-demo-dev on Windows: collect real host hardware, then start/rebuild the container.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$MonoRoot = Split-Path -Parent $Root
$ComposeFile = if ($env:AI_COMPOSE_FILE) { $env:AI_COMPOSE_FILE } else { Join-Path $MonoRoot "docker-compose.dev.yml" }
$ComposeWindows = Join-Path $MonoRoot "docker-compose.ai-windows.yml"
$SnapshotDir = Join-Path $Root ".host-profile-snapshot.d"
$SnapshotFile = Join-Path $SnapshotDir "host_profile_injected.json"

New-Item -ItemType Directory -Force -Path $SnapshotDir | Out-Null
Write-Host "Collecting Windows host profile snapshot..."
& (Join-Path $PSScriptRoot "collect_windows_host_profile.ps1") -OutputPath $SnapshotFile

$ComposeArgs = @("-f", $ComposeFile)
if (Test-Path $ComposeWindows) {
    $ComposeArgs += @("-f", $ComposeWindows)
}
$ComposeArgs += @("up", "-d", "--build", "ai-demo-dev")

docker compose @ComposeArgs
