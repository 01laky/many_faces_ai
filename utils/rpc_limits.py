"""Servicer-level RPC limits (AIH1-C1/C2)."""

from __future__ import annotations

MAX_PROMPT_CHARS = 32_000
MAX_NEW_TOKENS_DEFAULT = 50
MAX_NEW_TOKENS_CAP = 384
MIN_NEW_TOKENS = 1


def clamp_max_new_tokens(value: int) -> int:
	if value <= 0:
		return MAX_NEW_TOKENS_DEFAULT
	return min(value, MAX_NEW_TOKENS_CAP)
