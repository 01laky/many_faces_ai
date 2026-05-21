"""Build and persist host-scope hardware snapshots (no live Ollama block)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from services.host_profile_collector import SCHEMA_VERSION, collect_host_hardware_snapshot


def build_host_snapshot() -> dict[str, Any]:
    os.environ.setdefault("HOST_PROFILE_SCOPE", "host")
    profile = collect_host_hardware_snapshot()
    profile["scope"] = "host"
    detection = profile.setdefault("detection", {})
    detection["capturedOnHost"] = True
    detection["insideDocker"] = False
    profile.pop("aiRuntime", None)
    return profile


def write_host_snapshot(output: Path, snapshot: dict[str, Any]) -> None:
    if snapshot.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("Unexpected schemaVersion in host snapshot")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
