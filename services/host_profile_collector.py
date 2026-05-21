"""Collect host hardware/OS profile locally on the AI worker machine."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

import psutil

COLLECTOR_VERSION = "1.0.0"
SCHEMA_VERSION = 1
DEFAULT_INJECTED_PATH = "/app/host_profile_injected.json"
NVIDIA_SMI_TIMEOUT_SECONDS = 1.0
OLLAMA_PROBE_TIMEOUT_SECONDS = 3.0
MAX_DISK_PARTITIONS = 10
HOST_PROFILE_SECTIONS = (
    "schemaVersion",
    "workerInstanceId",
    "scope",
    "hostname",
    "os",
    "cpu",
    "gpu",
    "memory",
    "disks",
)


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _inside_docker() -> bool:
    if os.path.exists("/.dockerenv"):
        return True
    return bool(os.getenv("KUBERNETES_SERVICE_HOST"))


def _resolve_scope() -> str:
    configured = (os.getenv("HOST_PROFILE_SCOPE") or "auto").strip().lower()
    if configured in ("host", "container"):
        return configured
    if not _inside_docker():
        return "host"
    if os.getenv("NVIDIA_VISIBLE_DEVICES"):
        return "host"
    return "container"


def _machine_guid_or_boot_id() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                if value:
                    return str(value)
        except OSError:
            pass
    machine_id_path = "/etc/machine-id"
    if os.path.isfile(machine_id_path):
        try:
            with open(machine_id_path, encoding="utf-8") as handle:
                content = handle.read().strip()
                if content:
                    return content
        except OSError:
            pass
    return platform.node() or "unknown"


def _worker_instance_id(hostname: str, os_family: str, machine_id: str, primary_gpu: str) -> str:
    material = f"{hostname}|{os_family}|{machine_id}|{primary_gpu}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"sha256:{digest}"


def _os_display_name(family: str, version: str) -> str:
    if family == "Windows":
        return f"Windows {version}".strip()
    if family == "Darwin":
        return f"macOS {version}".strip()
    if family == "Linux":
        try:
            import distro

            return distro.name(pretty=True) or f"Linux {version}".strip()
        except ImportError:
            return f"Linux {version}".strip()
    return f"{family} {version}".strip()


def _collect_cpu() -> dict[str, Any]:
    logical = psutil.cpu_count(logical=True) or 0
    physical = psutil.cpu_count(logical=False) or logical
    model_name = platform.processor() or "unknown"
    if sys.platform == "linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as handle:
                for line in handle:
                    if line.lower().startswith("model name"):
                        model_name = line.split(":", 1)[1].strip()
                        break
        except OSError:
            pass
    max_freq = None
    try:
        freq = psutil.cpu_freq()
        if freq and freq.max:
            max_freq = int(freq.max)
    except (AttributeError, OSError):
        pass
    payload: dict[str, Any] = {
        "logicalCores": logical,
        "physicalCores": physical,
        "modelName": model_name,
    }
    if max_freq:
        payload["maxFrequencyMhz"] = max_freq
    return payload


def _collect_gpu(warnings: list[str]) -> dict[str, Any]:
    devices: list[dict[str, Any]] = []
    cuda_available = False
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            completed = subprocess.run(
                [
                    smi,
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=NVIDIA_SMI_TIMEOUT_SECONDS,
                check=False,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                for line in completed.stdout.splitlines():
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) < 3:
                        continue
                    name, driver, memory_mb = parts[:3]
                    try:
                        vram_bytes = int(float(memory_mb) * 1024 * 1024)
                    except ValueError:
                        vram_bytes = None
                    device: dict[str, Any] = {"name": name, "vendor": "NVIDIA"}
                    if vram_bytes is not None:
                        device["vramBytes"] = vram_bytes
                    if driver:
                        device["driverVersion"] = driver
                    devices.append(device)
                cuda_available = bool(devices)
            elif completed.stderr:
                warnings.append(f"nvidia-smi failed: {completed.stderr.strip()[:120]}")
        except subprocess.TimeoutExpired:
            warnings.append("nvidia-smi timed out")
        except OSError as exc:
            warnings.append(f"nvidia-smi error: {exc}")
    if not devices and sys.platform == "darwin":
        try:
            completed = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if completed.returncode == 0:
                for line in completed.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Chipset Model:"):
                        name = stripped.split(":", 1)[1].strip()
                        if name:
                            devices.append({"name": name, "vendor": "Apple"})
        except (subprocess.TimeoutExpired, OSError):
            pass
    return {"devices": devices, "cudaAvailable": cuda_available}


def _collect_disks() -> list[dict[str, Any]]:
    partitions: list[dict[str, Any]] = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (OSError, PermissionError):
            continue
        if usage.total <= 0:
            continue
        partitions.append(
            {
                "mountPoint": part.mountpoint,
                "totalBytes": usage.total,
                "freeBytes": usage.free,
                "fsType": part.fstype or "unknown",
            }
        )
    partitions.sort(key=lambda item: item["freeBytes"])
    return partitions[:MAX_DISK_PARTITIONS]


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")


def _http_get_json(url: str, timeout: float) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": "many-faces-ai-host-profile"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _http_post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any] | None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "many-faces-ai-host-profile"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _injected_profile_path() -> str:
    return (os.getenv("HOST_PROFILE_INJECTED_PATH") or DEFAULT_INJECTED_PATH).strip()


def _is_valid_host_snapshot(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if data.get("schemaVersion") != SCHEMA_VERSION:
        return False
    if data.get("scope") != "host":
        return False
    if not data.get("hostname"):
        return False
    for key in ("os", "cpu", "gpu", "memory"):
        if key not in data:
            return False
    return True


def _load_injected_snapshot() -> dict[str, Any] | None:
    if os.getenv("HOST_PROFILE_USE_INJECTED", "").strip().lower() in ("0", "false", "no"):
        return None
    path = _injected_profile_path()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not _is_valid_host_snapshot(payload):
        return None
    return payload


def _merge_injected_with_runtime(
    injected: dict[str, Any],
    model_name: str | None,
) -> dict[str, Any]:
    warnings: list[str] = list((injected.get("detection") or {}).get("warnings") or [])
    configured_model = model_name or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b-instruct-q4_K_M"
    profile: dict[str, Any] = {
        key: injected[key] for key in HOST_PROFILE_SECTIONS if key in injected
    }
    profile["collectedAtUtc"] = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    profile["scope"] = "host"
    profile["aiRuntime"] = _collect_ollama_runtime(configured_model, warnings)
    injected_detection = (
        injected.get("detection") if isinstance(injected.get("detection"), dict) else {}
    )
    profile["detection"] = {
        **injected_detection,
        "collectorVersion": COLLECTOR_VERSION,
        "platform": sys.platform,
        "insideDocker": _inside_docker(),
        "injectedFromHost": True,
        "hostSnapshotAtUtc": injected.get("collectedAtUtc"),
        "warnings": warnings,
    }
    return profile


def _collect_ollama_runtime(model_name: str, warnings: list[str]) -> dict[str, Any]:
    base = _ollama_base_url()
    runtime: dict[str, Any] = {
        "ollamaBaseUrl": base,
        "ollamaModelConfigured": model_name,
        "ollamaReachable": False,
        "pythonVersion": platform.python_version(),
        "grpcPort": _env_int("PORT") or 50051,
    }
    ctx = _env_int("OLLAMA_NUM_CTX")
    if ctx is not None:
        runtime["ollamaContextLength"] = ctx
    num_gpu = _env_int("OLLAMA_NUM_GPU")
    if num_gpu is not None:
        runtime["ollamaNumGpu"] = num_gpu

    tags = _http_get_json(f"{base}/api/tags", OLLAMA_PROBE_TIMEOUT_SECONDS)
    runtime["ollamaReachable"] = tags is not None
    if tags is None:
        warnings.append("Ollama unreachable")
        return runtime

    show = _http_post_json(
        f"{base}/api/show",
        {"model": model_name},
        OLLAMA_PROBE_TIMEOUT_SECONDS,
    )
    if show:
        details = show.get("details") if isinstance(show.get("details"), dict) else {}
        detail: dict[str, Any] = {}
        for key, target in (
            ("family", "family"),
            ("parameter_size", "parameterSize"),
            ("quantization_level", "quantizationLevel"),
            ("format", "format"),
        ):
            value = details.get(key)
            if value:
                detail[target] = value
        size = show.get("size")
        if isinstance(size, int):
            detail["modelSizeBytes"] = size
        if detail:
            runtime["ollamaModelDetail"] = detail
    else:
        warnings.append("Ollama /api/show failed")

    ps_payload = _http_get_json(f"{base}/api/ps", OLLAMA_PROBE_TIMEOUT_SECONDS)
    loaded: list[dict[str, Any]] = []
    if isinstance(ps_payload, dict):
        for item in ps_payload.get("models") or []:
            if not isinstance(item, dict):
                continue
            entry: dict[str, Any] = {}
            if item.get("name"):
                entry["name"] = item["name"]
            if isinstance(item.get("size"), int):
                entry["sizeBytes"] = item["size"]
            if isinstance(item.get("size_vram"), int):
                entry["sizeVramBytes"] = item["size_vram"]
            if item.get("processor"):
                entry["processor"] = item["processor"]
            expires = item.get("expires_at")
            if expires:
                entry["expiresAtUtc"] = expires
            if entry:
                loaded.append(entry)
    runtime["ollamaLoadedModels"] = loaded
    return runtime


def collect_host_profile(model_name: str | None = None) -> dict[str, Any]:
    """Build the host profile JSON document returned by GetHostProfile."""
    injected = _load_injected_snapshot()
    if injected is not None and (_inside_docker() or os.getenv("HOST_PROFILE_USE_INJECTED") == "1"):
        return _merge_injected_with_runtime(injected, model_name)

    return _collect_live_profile(model_name)


def _collect_live_profile(model_name: str | None = None) -> dict[str, Any]:
    """Collect hardware/OS profile from the current execution environment."""
    warnings: list[str] = []
    scope = _resolve_scope()
    if scope == "container":
        warnings.append("Profile scope is container — GPU/RAM may be under-reported")

    hostname = socket.gethostname()
    os_family = platform.system()
    if os_family == "Darwin":
        os_family = "Darwin"
    elif os_family == "Windows":
        os_family = "Windows"
    elif os_family == "Linux":
        os_family = "Linux"

    gpu = _collect_gpu(warnings)
    primary_gpu = gpu["devices"][0]["name"] if gpu["devices"] else ""
    machine_id = _machine_guid_or_boot_id()
    worker_id = _worker_instance_id(hostname, os_family, machine_id, primary_gpu)

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    configured_model = model_name or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b-instruct-q4_K_M"

    profile: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "workerInstanceId": worker_id,
        "collectedAtUtc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "scope": scope,
        "hostname": hostname,
        "os": {
            "family": os_family,
            "version": platform.version(),
            "arch": platform.machine(),
            "displayName": _os_display_name(os_family, platform.version()),
        },
        "cpu": _collect_cpu(),
        "gpu": gpu,
        "memory": {
            "ramTotalBytes": memory.total,
            "ramAvailableBytes": memory.available,
            "swapTotalBytes": swap.total,
            "swapUsedBytes": swap.used,
        },
        "disks": _collect_disks(),
        "aiRuntime": _collect_ollama_runtime(configured_model, warnings),
        "detection": {
            "collectorVersion": COLLECTOR_VERSION,
            "platform": sys.platform,
            "insideDocker": _inside_docker(),
            "warnings": warnings,
        },
    }
    return profile
