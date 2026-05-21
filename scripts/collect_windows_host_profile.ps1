# Collect real Windows host hardware for ai-demo-dev (run on the Windows machine).
param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-Sha256Prefix([string]$Text) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    $hex = -join ($hash | ForEach-Object { $_.ToString("x2") })
    return "sha256:$($hex.Substring(0, 32))"
}

function Get-NvidiaGpuDevices {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $smi) {
        return @()
    }
    $raw = & nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits 2>$null
    if (-not $raw) {
        return @()
    }
    $devices = @()
    foreach ($line in @($raw)) {
        $parts = @($line -split "," | ForEach-Object { $_.Trim() })
        if ($parts.Count -lt 3) { continue }
        $name, $driver, $memoryMb = $parts[0..2]
        $vramBytes = [int64]([double]$memoryMb * 1024 * 1024)
        $devices += @{
            name = $name
            vendor = "NVIDIA"
            vramBytes = $vramBytes
            driverVersion = $driver
        }
    }
    return $devices
}

$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutputPath -or $OutputPath.Trim().Length -eq 0) {
    $OutputPath = Join-Path $Root ".host-profile-snapshot.d\host_profile_injected.json"
}

$hostname = $env:COMPUTERNAME
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$computer = Get-CimInstance Win32_ComputerSystem
$gpus = Get-NvidiaGpuDevices
$primaryGpu = if ($gpus.Count -gt 0) { $gpus[0].name } else { "" }

try {
    $machineGuid = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Cryptography" -Name MachineGuid).MachineGuid
} catch {
    $machineGuid = $hostname
}

$workerId = Get-Sha256Prefix("$hostname|Windows|$machineGuid|$primaryGpu")
$collectedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$logicalCores = [int]$computer.NumberOfLogicalProcessors
$physicalCores = [int](Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum
if ($physicalCores -le 0) { $physicalCores = $logicalCores }

$disks = @()
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    if ($_.Size -gt 0) {
        $disks += @{
            mountPoint = $_.DeviceID
            totalBytes = [int64]$_.Size
            freeBytes = [int64]$_.FreeSpace
            fsType = "NTFS"
        }
    }
}

$snapshot = @{
    schemaVersion = 1
    workerInstanceId = $workerId
    collectedAtUtc = $collectedAt
    scope = "host"
    hostname = $hostname
    os = @{
        family = "Windows"
        version = $os.Version
        arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        displayName = $os.Caption
    }
    cpu = @{
        logicalCores = $logicalCores
        physicalCores = $physicalCores
        modelName = $cpu.Name.Trim()
    }
    gpu = @{
        devices = @($gpus)
        cudaAvailable = ($gpus.Count -gt 0)
    }
    memory = @{
        ramTotalBytes = [int64]$computer.TotalPhysicalMemory
        ramAvailableBytes = [int64]$os.FreePhysicalMemory * 1024
        swapTotalBytes = 0
        swapUsedBytes = 0
    }
    disks = $disks
    detection = @{
        collectorVersion = "1.0.0"
        platform = "win32"
        insideDocker = $false
        capturedOnHost = $true
        capturedOnWindowsHost = $true
        warnings = @()
    }
}

$dir = Split-Path -Parent $OutputPath
if ($dir) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$json = $snapshot | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutputPath, ($json + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))

Write-Host "Windows host profile snapshot written to $OutputPath"
Write-Host "  hostname: $hostname"
Write-Host "  gpu: $(if ($primaryGpu) { $primaryGpu } else { 'none detected' })"
