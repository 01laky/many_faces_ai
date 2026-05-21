"""Tests for automatic host profile refresh at container start."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.refresh_host_snapshot import refresh_host_snapshot


def test_refresh_prefers_host_agent(tmp_path, monkeypatch):
    output = tmp_path / "host_profile_injected.json"
    agent_snapshot = {
        "schemaVersion": 1,
        "scope": "host",
        "hostname": "agent-host",
        "os": {"family": "Darwin", "version": "1", "arch": "arm64", "displayName": "macOS"},
        "cpu": {"logicalCores": 8, "physicalCores": 8, "modelName": "Apple M3"},
        "gpu": {"devices": [{"name": "Apple M3", "vendor": "Apple"}], "cudaAvailable": False},
        "memory": {
            "ramTotalBytes": 1,
            "ramAvailableBytes": 1,
            "swapTotalBytes": 0,
            "swapUsedBytes": 0,
        },
    }

    def fake_agent_collect(path: Path):
        assert path == output
        return agent_snapshot

    monkeypatch.setenv("HOST_PROFILE_AGENT_URL", "http://host.docker.internal:9765")
    with patch("scripts.refresh_host_snapshot._try_agent_collect", side_effect=fake_agent_collect):
        snapshot = refresh_host_snapshot(output)

    assert snapshot["hostname"] == "agent-host"
    assert json.loads(output.read_text(encoding="utf-8"))["scope"] == "host"


def test_refresh_falls_back_to_local_collect(tmp_path, monkeypatch):
    output = tmp_path / "host_profile_injected.json"
    local_snapshot = {
        "schemaVersion": 1,
        "scope": "host",
        "hostname": "win-host",
        "os": {"family": "Windows", "version": "10", "arch": "amd64", "displayName": "Windows 10"},
        "cpu": {"logicalCores": 16, "physicalCores": 8, "modelName": "Intel"},
        "gpu": {
            "devices": [{"name": "NVIDIA GeForce RTX 3050", "vendor": "NVIDIA"}],
            "cudaAvailable": True,
        },
        "memory": {
            "ramTotalBytes": 1,
            "ramAvailableBytes": 1,
            "swapTotalBytes": 0,
            "swapUsedBytes": 0,
        },
    }

    with patch("scripts.refresh_host_snapshot._try_agent_collect", return_value=None):
        with patch(
            "scripts.refresh_host_snapshot.build_host_snapshot",
            return_value=local_snapshot,
        ):
            snapshot = refresh_host_snapshot(output)

    assert snapshot["gpu"]["devices"][0]["name"] == "NVIDIA GeForce RTX 3050"
