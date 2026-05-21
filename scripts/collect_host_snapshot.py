#!/usr/bin/env python3
"""Collect host hardware snapshot on the physical machine (debug/standalone)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.host_profile_snapshot import build_host_snapshot, write_host_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write host hardware snapshot JSON for ai-demo-dev injection.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT / ".host-profile-snapshot.d" / "host_profile_injected.json"),
        help="Output path (default: many_faces_ai/.host-profile-snapshot.d/host_profile_injected.json)",
    )
    args = parser.parse_args()
    output = Path(args.output)
    snapshot = build_host_snapshot()
    write_host_snapshot(output, snapshot)
    gpu_names = [device.get("name", "?") for device in snapshot.get("gpu", {}).get("devices", [])]
    gpu_label = ", ".join(gpu_names) if gpu_names else "none detected"
    print(f"Host profile snapshot written to {output}")
    print(f"  hostname: {snapshot.get('hostname')}")
    print(f"  scope: {snapshot.get('scope')}")
    print(f"  gpu: {gpu_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
