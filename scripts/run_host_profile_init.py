#!/usr/bin/env python3
"""One-shot host profile collection before ai-demo-dev starts (compose init service)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.host_profile_collector import _is_valid_host_snapshot  # noqa: E402
from services.host_profile_snapshot import build_host_snapshot, write_host_snapshot  # noqa: E402

WINDOWS_POWERSHELL_IMAGE = os.getenv(
    "HOST_PROFILE_WINDOWS_INIT_IMAGE",
    "mcr.microsoft.com/powershell:5.1-windowsservercore-ltsc2019",
)
POWERSHELL_EXE_REL = Path("Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
HOST_C_ROOTS = (
    "/mnt/c",
    "/run/desktop/mnt/host/c",
)


def _snapshot_path() -> Path:
    return Path(os.getenv("HOST_PROFILE_SNAPSHOT", "/out/host_profile_injected.json"))


def _powershell_candidates() -> list[Path]:
    configured = os.getenv("HOST_PROFILE_WINDOWS_POWERSHELL", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    for root in HOST_C_ROOTS:
        candidates.append(Path(root) / POWERSHELL_EXE_REL)
    return candidates


def _read_mountinfo() -> str:
    for path in ("/proc/self/mountinfo", "/proc/mounts"):
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def _windows_repo_root_from_mountinfo() -> str | None:
    configured = os.getenv("MFAI_REPO_ROOT_WINDOWS", "").strip()
    if configured:
        return configured.rstrip("\\/")
    mountinfo = _read_mountinfo()
    if not mountinfo:
        return None
    for line in mountinfo.splitlines():
        if " /workspace " not in f" {line} ":
            continue
        source = ""
        if " - " in line:
            right = line.split(" - ", 1)[1]
            parts = right.split()
            if len(parts) >= 2:
                source = parts[1]
        else:
            match = re.search(r"(/(?:mnt|c|run/desktop/mnt/host/c)[^\s]+many_faces_ai)", line)
            if match:
                source = match.group(1)
        if not source:
            continue
        normalized = source.replace("\\", "/")
        if normalized.startswith("/run/desktop/mnt/host/c/"):
            rel = normalized[len("/run/desktop/mnt/host/c/") :]
            return str(PureWindowsPath("C:/") / PureWindowsPath(rel))
        if normalized.startswith("/mnt/c/"):
            rel = normalized[len("/mnt/c/") :]
            return str(PureWindowsPath("C:/") / PureWindowsPath(rel))
    return None


def _validate_snapshot(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and _is_valid_host_snapshot(payload)


def _try_host_agent(timeout: float = 8.0) -> bool:
    base = (os.getenv("HOST_PROFILE_AGENT_URL") or "http://host.docker.internal:9765").rstrip("/")
    if not base:
        return False
    request = urllib.request.Request(
        f"{base}/v1/collect",
        data=b"{}",
        headers={"Content-Type": "application/json", "User-Agent": "many-faces-ai-init"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return False
    return isinstance(body, dict) and body.get("ok") is True


def _run_windows_powershell_script(win_root: str, output: Path) -> bool:
    ps1 = str(PureWindowsPath(win_root) / "scripts" / "collect_windows_host_profile.ps1")
    out = str(PureWindowsPath(win_root) / ".host-profile-snapshot.d" / "host_profile_injected.json")
    for powershell in _powershell_candidates():
        if not powershell.is_file():
            continue
        try:
            completed = subprocess.run(
                [
                    str(powershell),
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    ps1,
                    "-OutputPath",
                    out,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if completed.returncode == 0 and _validate_snapshot(output):
            print(f"Windows host profile collected via {powershell}")
            return True
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
    return False


def _run_windows_docker_powershell(win_root: str, output: Path) -> bool:
    sock = Path("/var/run/docker.sock")
    if not sock.is_socket():
        return False
    docker = os.getenv("DOCKER_BIN", "docker")
    try:
        completed = subprocess.run(
            [
                docker,
                "run",
                "--rm",
                "--platform",
                "windows/amd64",
                "-v",
                f"{win_root}:C:\\workspace",
                WINDOWS_POWERSHELL_IMAGE,
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "C:\\workspace\\scripts\\collect_windows_host_profile.ps1",
                "-OutputPath",
                "C:\\workspace\\.host-profile-snapshot.d\\host_profile_injected.json",
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"Windows docker init failed: {exc}", file=sys.stderr)
        return False
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode != 0 and completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    return _validate_snapshot(output)


def _run_python_fallback(output: Path) -> bool:
    os.environ.setdefault("HOST_PROFILE_SCOPE", "host")
    snapshot = build_host_snapshot()
    write_host_snapshot(output, snapshot)
    return _validate_snapshot(output)


def main() -> int:
    output = _snapshot_path()
    output.parent.mkdir(parents=True, exist_ok=True)

    if _validate_snapshot(output):
        print(f"Host profile snapshot already valid at {output}")
        return 0

    print("Collecting host profile snapshot before ai-demo-dev starts...")
    if _try_host_agent() and _validate_snapshot(output):
        print(f"Host profile snapshot ready at {output} (host agent)")
        return 0

    win_root = _windows_repo_root_from_mountinfo()
    if win_root:
        print(f"Detected Windows workspace path: {win_root}")
        if _run_windows_powershell_script(win_root, output):
            print(f"Host profile snapshot ready at {output} (Windows PowerShell)")
            return 0
        if _run_windows_docker_powershell(win_root, output):
            print(f"Host profile snapshot ready at {output} (Windows init container)")
            return 0

    if _run_python_fallback(output) and _validate_snapshot(output):
        print(f"Host profile snapshot ready at {output} (local collector)")
        return 0

    print(
        "Host profile snapshot is missing or still container-scoped; ai-demo-dev will start anyway.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
