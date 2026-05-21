# Delegates to monorepo up-ai-windows.ps1 (host collect + compose).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& (Join-Path $RepoRoot "scripts\up-ai-windows.ps1")
