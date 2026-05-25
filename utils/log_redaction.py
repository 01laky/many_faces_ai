"""Scrub secrets and truncate long strings before logging (AIH1-F1)."""

from __future__ import annotations

import re

_TOKEN_LIKE = re.compile(
	r"(x-ai-worker-token\s*[:=]\s*)(\S+)|"
	r"(Bearer\s+)([A-Za-z0-9\-_.=]+)|"
	r"(access_token\s*[:=]\s*)(\S+)",
	re.IGNORECASE,
)


def _redact_match(match: re.Match[str]) -> str:
	prefix = match.group(1) or match.group(3) or match.group(5) or ""
	return f"{prefix}[REDACTED]"


def redact_sensitive(text: str, max_len: int = 500) -> str:
	if not text:
		return ""
	scrubbed = _TOKEN_LIKE.sub(_redact_match, text)
	if len(scrubbed) <= max_len:
		return scrubbed
	return scrubbed[: max_len - 3] + "..."
