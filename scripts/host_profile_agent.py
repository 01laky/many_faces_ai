#!/usr/bin/env python3
"""Host-side HTTP agent: collects real hardware when ai-demo-dev starts in Docker."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("HOST_PROFILE_SCOPE", "host")

from services.host_profile_snapshot import build_host_snapshot, write_host_snapshot  # noqa: E402

DEFAULT_PORT = 9765
DEFAULT_SNAPSHOT = ROOT / ".host-profile-snapshot.d" / "host_profile_injected.json"


class HostProfileAgentHandler(BaseHTTPRequestHandler):
    snapshot_path: Path = DEFAULT_SNAPSHOT

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._send_json(200, {"ok": True, "service": "host-profile-agent"})
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/collect":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            snapshot = build_host_snapshot()
            write_host_snapshot(self.snapshot_path, snapshot)
        except OSError as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})
            return
        self._send_json(
            200,
            {
                "ok": True,
                "snapshot": snapshot,
                "outputPath": str(self.snapshot_path),
            },
        )

    def log_message(self, format: str, *args) -> None:
        if os.getenv("HOST_PROFILE_AGENT_VERBOSE") == "1":
            super().log_message(format, *args)


def main() -> int:
    port = int(os.getenv("HOST_PROFILE_AGENT_PORT", str(DEFAULT_PORT)))
    bind = os.getenv("HOST_PROFILE_AGENT_BIND", "127.0.0.1")
    snapshot_dir = os.getenv("HOST_PROFILE_SNAPSHOT_DIR")
    if snapshot_dir:
        HostProfileAgentHandler.snapshot_path = Path(snapshot_dir) / "host_profile_injected.json"
    else:
        HostProfileAgentHandler.snapshot_path = DEFAULT_SNAPSHOT

    server = ThreadingHTTPServer((bind, port), HostProfileAgentHandler)
    print(f"host-profile-agent listening on http://{bind}:{port}")
    print(f"  snapshot path: {HostProfileAgentHandler.snapshot_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("host-profile-agent stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
