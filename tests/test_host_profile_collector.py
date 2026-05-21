"""Unit tests for host profile collection (HP-P1..P9)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from services.host_profile_collector import collect_host_profile


@pytest.fixture
def base_env(monkeypatch):
    monkeypatch.setenv("HOST_PROFILE_SCOPE", "host")
    monkeypatch.delenv("NVIDIA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "demo-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


def test_hp_p6_worker_instance_id_stable(base_env):
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": False}
            first = collect_host_profile()
            second = collect_host_profile()
    assert first["workerInstanceId"] == second["workerInstanceId"]
    assert first["workerInstanceId"].startswith("sha256:")


def test_hp_p2_no_gpu(base_env):
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": False}
            profile = collect_host_profile()
    assert profile["gpu"]["devices"] == []


def test_hp_p1_windows_nvidia(base_env, monkeypatch):
    monkeypatch.setenv("HOST_PROFILE_SCOPE", "host")

    def fake_gpu(_warnings):
        return {
            "devices": [
                {
                    "name": "NVIDIA GeForce RTX 4090",
                    "vendor": "NVIDIA",
                    "vramBytes": 24 * 1024 * 1024 * 1024,
                    "driverVersion": "552.22",
                }
            ],
            "cudaAvailable": True,
        }

    with patch("services.host_profile_collector._collect_gpu", side_effect=fake_gpu):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": True}
            profile = collect_host_profile()
    assert profile["gpu"]["devices"][0]["name"].startswith("NVIDIA")


def test_hp_p3_container_scope_warning(base_env, monkeypatch):
    monkeypatch.setenv("HOST_PROFILE_SCOPE", "container")
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": False}
            profile = collect_host_profile()
    assert profile["scope"] == "container"
    assert any("container" in w.lower() for w in profile["detection"]["warnings"])


def test_hp_p4_nvidia_smi_timeout(base_env):
    import subprocess

    def fake_gpu(warnings):
        try:
            subprocess.run(["sleep", "5"], timeout=0.01)
        except subprocess.TimeoutExpired:
            warnings.append("nvidia-smi timed out")
        return {"devices": [], "cudaAvailable": False}

    with patch("services.host_profile_collector._collect_gpu", side_effect=fake_gpu):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": False}
            profile = collect_host_profile()
    assert profile["gpu"]["devices"] == []


def test_hp_p5_ollama_down(base_env):
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {
                "ollamaReachable": False,
                "ollamaModelConfigured": "demo-model",
            }
            profile = collect_host_profile()
    assert profile["aiRuntime"]["ollamaReachable"] is False
    assert profile["cpu"]["logicalCores"] >= 1


def test_hp_p9_ollama_down_host_sections_present(base_env):
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
            ollama.return_value = {"ollamaReachable": False}
            profile = collect_host_profile()
    assert "os" in profile
    assert "cpu" in profile
    assert "gpu" in profile


def test_hp_p8_ollama_loaded_models(base_env):
    runtime = {
        "ollamaReachable": True,
        "ollamaModelConfigured": "demo-model",
        "ollamaModelDetail": {"parameterSize": "7.6B", "quantizationLevel": "Q4_K_M"},
        "ollamaLoadedModels": [
            {
                "name": "demo-model",
                "sizeBytes": 100,
                "sizeVramBytes": 200,
                "processor": "100% GPU",
            }
        ],
    }
    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._collect_ollama_runtime", return_value=runtime):
            profile = collect_host_profile()
    loaded = profile["aiRuntime"]["ollamaLoadedModels"]
    assert loaded[0]["processor"] == "100% GPU"


def test_ollama_http_probe_integration(base_env, monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")
    monkeypatch.setenv("OLLAMA_NUM_GPU", "999")

    def fake_get(url, timeout):
        if url.endswith("/api/tags"):
            return {"models": []}
        if url.endswith("/api/ps"):
            return {"models": []}
        return None

    def fake_post(url, payload, timeout):
        if url.endswith("/api/show"):
            return {
                "size": 1234,
                "details": {
                    "family": "qwen2",
                    "parameter_size": "7.6B",
                    "quantization_level": "Q4_K_M",
                    "format": "gguf",
                },
            }
        return None

    with patch(
        "services.host_profile_collector._collect_gpu",
        return_value={"devices": [], "cudaAvailable": False},
    ):
        with patch("services.host_profile_collector._http_get_json", side_effect=fake_get):
            with patch("services.host_profile_collector._http_post_json", side_effect=fake_post):
                profile = collect_host_profile()
    runtime = profile["aiRuntime"]
    assert runtime["ollamaReachable"] is True
    assert runtime["ollamaContextLength"] == 4096
    assert runtime["ollamaNumGpu"] == 999
    assert runtime["ollamaModelDetail"]["parameterSize"] == "7.6B"
    json.dumps(profile)


def test_hp_injected_snapshot_merges_host_gpu(base_env, tmp_path, monkeypatch):
    injected_path = tmp_path / "host_profile_injected.json"
    injected = {
        "schemaVersion": 1,
        "workerInstanceId": "sha256:abc123",
        "collectedAtUtc": "2026-05-21T10:00:00Z",
        "scope": "host",
        "hostname": "win-gaming-pc",
        "os": {
            "family": "Windows",
            "version": "10.0.26100",
            "arch": "AMD64",
            "displayName": "Windows 10.0.26100",
        },
        "cpu": {"logicalCores": 16, "physicalCores": 8, "modelName": "Intel Core i7"},
        "gpu": {
            "devices": [
                {
                    "name": "NVIDIA GeForce RTX 3050",
                    "vendor": "NVIDIA",
                    "vramBytes": 8 * 1024 * 1024 * 1024,
                    "driverVersion": "552.22",
                }
            ],
            "cudaAvailable": True,
        },
        "memory": {
            "ramTotalBytes": 32 * 1024 * 1024 * 1024,
            "ramAvailableBytes": 16 * 1024 * 1024 * 1024,
            "swapTotalBytes": 0,
            "swapUsedBytes": 0,
        },
        "disks": [{"mountPoint": "C:\\", "totalBytes": 1000, "freeBytes": 500, "fsType": "NTFS"}],
        "detection": {"capturedOnHost": True, "insideDocker": False, "warnings": []},
    }
    injected_path.write_text(json.dumps(injected), encoding="utf-8")
    monkeypatch.setenv("HOST_PROFILE_INJECTED_PATH", str(injected_path))
    monkeypatch.setenv("HOST_PROFILE_USE_INJECTED", "1")

    runtime = {
        "ollamaReachable": True,
        "ollamaModelConfigured": "demo-model",
        "ollamaNumGpu": 0,
    }
    with patch("services.host_profile_collector._inside_docker", return_value=True):
        with patch("services.host_profile_collector._collect_ollama_runtime", return_value=runtime):
            profile = collect_host_profile()

    assert profile["scope"] == "host"
    assert profile["hostname"] == "win-gaming-pc"
    assert profile["gpu"]["devices"][0]["name"] == "NVIDIA GeForce RTX 3050"
    assert profile["aiRuntime"]["ollamaReachable"] is True
    assert profile["detection"]["injectedFromHost"] is True
    assert profile["detection"]["insideDocker"] is True
    assert profile["detection"]["hostSnapshotAtUtc"] == "2026-05-21T10:00:00Z"


def test_hp_invalid_injected_snapshot_falls_back(base_env, tmp_path, monkeypatch):
    injected_path = tmp_path / "host_profile_injected.json"
    injected_path.write_text('{"schemaVersion":1,"scope":"container"}', encoding="utf-8")
    monkeypatch.setenv("HOST_PROFILE_INJECTED_PATH", str(injected_path))
    monkeypatch.setenv("HOST_PROFILE_USE_INJECTED", "1")
    monkeypatch.setenv("HOST_PROFILE_SCOPE", "container")

    with patch("services.host_profile_collector._inside_docker", return_value=True):
        with patch(
            "services.host_profile_collector._collect_gpu",
            return_value={"devices": [], "cudaAvailable": False},
        ):
            with patch("services.host_profile_collector._collect_ollama_runtime") as ollama:
                ollama.return_value = {"ollamaReachable": False}
                profile = collect_host_profile()

    assert profile["scope"] == "container"
    assert "injectedFromHost" not in profile.get("detection", {})


def test_docker_desktop_windows_host_profile(base_env, monkeypatch, tmp_path):
    host_root = tmp_path / "c"
    system32 = host_root / "Windows" / "System32"
    system32.mkdir(parents=True)
    (system32 / "hostname.exe").write_bytes(b"")
    (system32 / "WindowsPowerShell" / "v1.0").mkdir(parents=True)
    (system32 / "WindowsPowerShell" / "v1.0" / "powershell.exe").write_bytes(b"")
    nvidia_smi = host_root / "Windows" / "System32" / "nvidia-smi.exe"
    nvidia_smi.write_bytes(b"")

    monkeypatch.setenv("HOST_PROFILE_WINDOWS_ROOT", str(host_root))

    def fake_run(executable, args, timeout):
        name = Path(executable).name.lower()
        if name == "hostname.exe":
            return type("R", (), {"returncode": 0, "stdout": "WIN-PC\n", "stderr": ""})()
        if name == "powershell.exe":
            command = args[-1]
            if "OSVersion" in command:
                return type(
                    "R",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "Microsoft Windows NT 10.0.26100.0\n",
                        "stderr": "",
                    },
                )()
            if "Win32_OperatingSystem" in command and "Caption" in command:
                return type(
                    "R", (), {"returncode": 0, "stdout": "Microsoft Windows 11 Pro\n", "stderr": ""}
                )()
            if "Win32_Processor" in command and "Name" in command:
                return type("R", (), {"returncode": 0, "stdout": "Intel Core i7\n", "stderr": ""})()
            if "NumberOfLogicalProcessors" in command:
                return type("R", (), {"returncode": 0, "stdout": "16\n", "stderr": ""})()
            if "NumberOfCores" in command:
                return type("R", (), {"returncode": 0, "stdout": "8\n", "stderr": ""})()
            if "TotalPhysicalMemory" in command:
                return type("R", (), {"returncode": 0, "stdout": "34359738368\n", "stderr": ""})()
            if "FreePhysicalMemory" in command:
                return type("R", (), {"returncode": 0, "stdout": "16777216\n", "stderr": ""})()
        if name == "nvidia-smi.exe":
            return type(
                "R",
                (),
                {
                    "returncode": 0,
                    "stdout": "NVIDIA GeForce RTX 3050, 552.22, 8192\n",
                    "stderr": "",
                },
            )()
        return None

    with patch("services.host_profile_collector._inside_docker", return_value=True):
        with patch("services.host_profile_collector._run_host_executable", side_effect=fake_run):
            from services.host_profile_collector import collect_host_hardware_snapshot

            profile = collect_host_hardware_snapshot()

    assert profile["scope"] == "host"
    assert profile["hostname"] == "WIN-PC"
    assert profile["gpu"]["devices"][0]["name"] == "NVIDIA GeForce RTX 3050"
    assert profile["detection"]["dockerDesktopWindowsHost"] is True
