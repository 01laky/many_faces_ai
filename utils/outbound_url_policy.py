"""Outbound URL validation for FetchPublicStats (AIH1-B1) — mirrors backend OutboundUrlAllowlist."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse


def _is_truthy(name: str) -> bool:
	return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def allow_http_loopback() -> bool:
	if _is_truthy("MFAI_ALLOW_HTTP_LOOPBACK"):
		return True
	return not (_is_truthy("MFAI_HARDENED_PROFILE") or _is_truthy("MFAI_REQUIRE_WORKER_AUTH"))


def _parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
	try:
		return ipaddress.ip_address(host)
	except ValueError:
		return None


def _is_loopback_host(host: str) -> bool:
	lowered = host.lower()
	if lowered in ("localhost", "localhost.localdomain"):
		return True
	ip = _parse_ip(lowered)
	return bool(ip and ip.is_loopback)


def _is_blocked_public_https_host(host: str) -> bool:
	lowered = host.lower().strip(".")
	if lowered in ("localhost", "localhost.localdomain"):
		return True
	if lowered.endswith(".local") or lowered.endswith(".internal"):
		return True
	ip = _parse_ip(lowered)
	if ip is None:
		return False
	if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
		return True
	if isinstance(ip, ipaddress.IPv4Address) and ip.packed[0] == 169 and ip.packed[1] == 254:
		return True
	return False


def validate_public_fetch_url(url: str) -> tuple[bool, str]:
	"""Return ``(ok, rejection_reason)`` — empty reason when ok."""
	raw = (url or "").strip()
	if not raw:
		return False, "empty"

	parsed = urlparse(raw)
	scheme = (parsed.scheme or "").lower()
	if scheme not in ("http", "https"):
		return False, "invalid_scheme"

	if parsed.username or parsed.password:
		return False, "userinfo_forbidden"

	host = parsed.hostname or ""
	if not host:
		return False, "missing_host"

	if scheme == "http":
		if not allow_http_loopback():
			return False, "non_https"
		if not _is_loopback_host(host):
			return False, "http_only_loopback"
		return True, ""

	if _is_blocked_public_https_host(host):
		return False, "private_or_local_host"
	return True, ""
