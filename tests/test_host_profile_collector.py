"""Unit tests for host profile collection (HP-P1..P9)."""

from __future__ import annotations

import json
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
