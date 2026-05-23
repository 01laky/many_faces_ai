"""urllib JSON helpers with configurable error policy."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse


def get_json(
    url: str,
    *,
    timeout: float,
    user_agent: str,
    allow_insecure_tls_for_host: Callable[[str], bool] | None = None,
) -> dict[str, Any] | None:
    host = urlparse(url).hostname or ""
    open_kw: dict[str, Any] = {"timeout": timeout}
    if allow_insecure_tls_for_host and allow_insecure_tls_for_host(host):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        open_kw["context"] = ctx

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, **open_kw) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    user_agent: str,
) -> dict[str, Any] | None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": user_agent},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None


def fetch_public_stats_body(
    absolute_url: str,
    *,
    allow_insecure_tls_for_host: Callable[[str], bool],
    timeout: float = 45.0,
) -> tuple[str, str]:
    """Return ``(json_body, error)`` — exactly one field is non-empty."""
    url = (absolute_url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return "", "absolute_url must be http(s)"

    host = urlparse(url).hostname or ""
    use_insecure_tls = allow_insecure_tls_for_host(host)
    open_kw: dict[str, Any] = {"timeout": timeout}
    if use_insecure_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        open_kw["context"] = ctx

    req = urllib.request.Request(url, headers={"User-Agent": "many-faces-ai-fetch-public-stats"})
    try:
        with urllib.request.urlopen(req, **open_kw) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return body, ""
    except urllib.error.HTTPError as exc:
        return "", f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        return "", str(exc)
