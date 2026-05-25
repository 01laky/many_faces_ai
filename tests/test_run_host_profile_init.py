"""Tests for compose init host profile collection."""

from __future__ import annotations

import json
from unittest.mock import patch

from scripts import run_host_profile_init as init


def test_windows_repo_root_from_mountinfo():
	mountinfo = (
		"123 122 0:1 /Users/dev/_mfai_demo/many_faces_ai /workspace rw,relatime - "
		"fake /run/desktop/mnt/host/c/Users/dev/_mfai_demo/many_faces_ai rw\n"
	)
	with patch.object(init, "_read_mountinfo", return_value=mountinfo):
		assert (
			init._windows_repo_root_from_mountinfo() == "C:\\Users\\dev\\_mfai_demo\\many_faces_ai"
		)


def test_main_keeps_valid_existing_snapshot(tmp_path, monkeypatch):
	output = tmp_path / "host_profile_injected.json"
	snapshot = {
		"schemaVersion": 1,
		"scope": "host",
		"hostname": "WIN-PC",
		"os": {"family": "Windows", "version": "1", "arch": "amd64", "displayName": "Windows"},
		"cpu": {"logicalCores": 8, "physicalCores": 4, "modelName": "Ryzen"},
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
		"detection": {"capturedOnWindowsHost": True},
	}
	output.write_text(json.dumps(snapshot), encoding="utf-8")
	monkeypatch.setenv("HOST_PROFILE_SNAPSHOT", str(output))
	assert init.main() == 0
