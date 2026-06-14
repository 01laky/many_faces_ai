"""Edge-case tests for services.host_profile_snapshot (build + write).

Previously the host-scope snapshot builder/writer had no direct coverage — the host-refresh test mocks
``scripts.refresh_host_snapshot.build_host_snapshot`` rather than exercising this module.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from services.host_profile_collector import SCHEMA_VERSION
from services.host_profile_snapshot import build_host_snapshot, write_host_snapshot


def test_write_host_snapshot_rejects_wrong_schema(tmp_path):
	out = tmp_path / "snap.json"
	with pytest.raises(ValueError):
		write_host_snapshot(out, {"schemaVersion": SCHEMA_VERSION + 99})
	assert not out.exists()


def test_write_host_snapshot_writes_sorted_json_with_trailing_newline(tmp_path):
	out = tmp_path / "nested" / "snap.json"  # parent dirs are created
	snapshot = {"schemaVersion": SCHEMA_VERSION, "b": 2, "a": 1}

	write_host_snapshot(out, snapshot)

	text = out.read_text(encoding="utf-8")
	assert text.endswith("\n")
	assert text.index('"a"') < text.index('"b"')  # sort_keys=True
	assert json.loads(text) == snapshot


@patch("services.host_profile_snapshot._looks_like_container_id", return_value=False)
@patch("services.host_profile_snapshot.collect_host_hardware_snapshot")
def test_build_host_snapshot_marks_real_host_and_strips_ai_runtime(mock_collect, _mock_container):
	mock_collect.return_value = {"hostname": "my-host", "detection": {}, "aiRuntime": {"x": 1}}

	profile = build_host_snapshot()

	assert profile["scope"] == "host"
	assert profile["detection"]["capturedOnHost"] is True
	assert "aiRuntime" not in profile  # live AI block is not part of a host-scope hardware snapshot


@patch("services.host_profile_snapshot._looks_like_container_id", return_value=True)
@patch("services.host_profile_snapshot.collect_host_hardware_snapshot")
def test_build_host_snapshot_marks_container(mock_collect, _mock_container):
	mock_collect.return_value = {"hostname": "abc123", "detection": {"insideDocker": True}}

	profile = build_host_snapshot()

	assert profile["scope"] == "container"
	assert "capturedOnHost" not in profile["detection"]
