"""Environment variable parsing shared across AI worker modules."""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"

HARDENED_OLLAMA_HOSTS = frozenset(
    {
        "127.0.0.1",
        "localhost",
        "host.docker.internal",
        "ollama",
        "ai-ollama",
    }
)


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def env_int_optional(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def validate_ollama_base_url_hardened() -> tuple[bool, str]:
    """AIH1-E6 / AIH1-T-B09 — reject disallowed Ollama hosts in hardened profile."""
    url = ollama_base_url()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "OLLAMA_BASE_URL must use http or https"
    host = (parsed.hostname or "").lower()
    if host not in HARDENED_OLLAMA_HOSTS:
        return False, f"OLLAMA_BASE_URL host '{host}' not in hardened allow-list"
    return True, ""
