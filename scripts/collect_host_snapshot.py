#!/usr/bin/env python3
"""Collect host hardware snapshot on the physical machine before Docker starts ai-demo-dev."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("HOST_PROFILE_SCOPE", "host")

from services.host_profile_collector import SCHEMA_VERSION, collect_host_profile  # noqa: E402


def _build_snapshot() -> dict:
    profile = collect_host_profile()
    profile["scope"] = "host"
    detection = profile.setdefault("detection", {})
    detection["capturedOnHost"] = True
    detection["insideDocker"] = False
    profile.pop("aiRuntime", None)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write host hardware snapshot JSON for ai-demo-dev injection.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT / ".host-profile.snapshot.json"),
        help="Output path (default: many_faces_ai/.host-profile.snapshot.json)",
    )
    args = parser.parse_args()
    output = Path(args.output)
    snapshot = _build_snapshot()
    if snapshot.get("schemaVersion") != SCHEMA_VERSION:
        print("Unexpected schemaVersion in snapshot", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gpu_names = [device.get("name", "?") for device in snapshot.get("gpu", {}).get("devices", [])]
    gpu_label = ", ".join(gpu_names) if gpu_names else "none detected"
    print(f"Host profile snapshot written to {output}")
    print(f"  hostname: {snapshot.get('hostname')}")
    print(f"  scope: {snapshot.get('scope')}")
    print(f"  gpu: {gpu_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
