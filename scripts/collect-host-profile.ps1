# Collect host hardware snapshot before ai-demo-dev starts (Option A: Docker + real host info).
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Out = if ($env:HOST_PROFILE_SNAPSHOT_FILE) { $env:HOST_PROFILE_SNAPSHOT_FILE } else { Join-Path $Root ".host-profile.snapshot.json" }

$Python = $env:PYTHON
if (-not $Python) {
    $Python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
}
if (-not $Python) {
    $Python = (Get-Command python3 -ErrorAction SilentlyContinue)?.Source
}
if (-not $Python) {
    throw "No python interpreter found for host profile snapshot"
}

& $Python (Join-Path $PSScriptRoot "collect_host_snapshot.py") -o $Out
