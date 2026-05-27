"""Media URL metadata pass for ReviewContent (AI-UP8 phase 1)."""

from __future__ import annotations

from urllib.parse import urlparse

from utils.outbound_url_policy import validate_public_fetch_url


def media_url_flags(media_url: str | None) -> list[str]:
	url = (media_url or "").strip()
	if not url:
		return []
	flags: list[str] = []
	ok, reason = validate_public_fetch_url(url)
	if not ok:
		flags.append("suspicious_media_url")
		if reason:
			flags.append(reason)
		return sorted(set(flags))

	parsed = urlparse(url)
	path = (parsed.path or "").lower()
	if path.endswith((".zip", ".exe", ".dmg", ".apk")):
		flags.append("unknown_content_type")
	return sorted(set(flags))
