"""Build and persist host-scope hardware snapshots (no live Ollama block)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from services.host_profile_collector import (
	SCHEMA_VERSION,
	_looks_like_container_id,
	collect_host_hardware_snapshot,
)


def build_host_snapshot() -> dict[str, Any]:
	os.environ.setdefault("HOST_PROFILE_SCOPE", "host")
	profile = collect_host_hardware_snapshot()
	detection = profile.setdefault("detection", {})
	is_real_host = (
		detection.get("dockerDesktopWindowsHost") is True
		or detection.get("capturedOnWindowsHost") is True
		or (
			not _looks_like_container_id(str(profile.get("hostname", "")))
			and not detection.get("insideDocker")
		)
	)
	if is_real_host:
		profile["scope"] = "host"
		detection["capturedOnHost"] = True
	else:
		profile["scope"] = profile.get("scope") or "container"
	profile.pop("aiRuntime", None)
	return profile


def write_host_snapshot(output: Path, snapshot: dict[str, Any]) -> None:
	if snapshot.get("schemaVersion") != SCHEMA_VERSION:
		raise ValueError("Unexpected schemaVersion in host snapshot")
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
