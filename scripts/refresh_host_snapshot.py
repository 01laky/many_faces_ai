#!/usr/bin/env python3
"""Refresh host hardware snapshot (container entrypoint + host agent)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.host_profile_snapshot import build_host_snapshot, write_host_snapshot  # noqa: E402


def _agent_collect_url() -> str | None:
    base = (os.getenv("HOST_PROFILE_AGENT_URL") or "http://host.docker.internal:9765").rstrip("/")
    if not base:
        return None
    return f"{base}/v1/collect"


def _try_agent_collect(output: Path, timeout: float = 8.0) -> dict | None:
    url = _agent_collect_url()
    if not url:
        return None
    request = urllib.request.Request(
        url,
        data=b"{}",
        headers={"Content-Type": "application/json", "User-Agent": "many-faces-ai-refresh"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None
    if not isinstance(body, dict) or body.get("ok") is not True:
        return None
    snapshot = body.get("snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    if output.is_file():
        try:
            loaded = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return loaded if isinstance(loaded, dict) else None
    return None


def refresh_host_snapshot(output: Path) -> dict:
    """Return a host-scope snapshot, preferring the host-side agent when reachable."""
    agent_snapshot = _try_agent_collect(output)
    if agent_snapshot is not None and agent_snapshot.get("scope") == "host":
        write_host_snapshot(output, agent_snapshot)
        return agent_snapshot

    os.environ.setdefault("HOST_PROFILE_SCOPE", "host")
    snapshot = build_host_snapshot()
    write_host_snapshot(output, snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh host profile snapshot JSON.")
    parser.add_argument(
        "-o",
        "--output",
        default=os.getenv("HOST_PROFILE_INJECTED_PATH", "/app/injected/host_profile_injected.json"),
    )
    args = parser.parse_args()
    output = Path(args.output)
    snapshot = refresh_host_snapshot(output)
    gpu_names = [device.get("name", "?") for device in snapshot.get("gpu", {}).get("devices", [])]
    gpu_label = ", ".join(gpu_names) if gpu_names else "none detected"
    print(f"Host profile snapshot written to {output}")
    print(f"  hostname: {snapshot.get('hostname')}")
    print(f"  scope: {snapshot.get('scope')}")
    print(f"  gpu: {gpu_label}")
    return 0 if snapshot.get("scope") == "host" else 1


if __name__ == "__main__":
    raise SystemExit(main())
