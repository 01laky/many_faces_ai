"""Simple in-process RPC rate limit (AIH1-C4). Distributed limit: TRACK-AIH1-REDIS."""

from __future__ import annotations

import os
import time
from collections import deque


def _limit_per_minute() -> int | None:
	raw = os.getenv("AIH1_RPC_RATE_PER_MIN", "").strip()
	if not raw:
		return None
	try:
		value = int(raw)
	except ValueError:
		return None
	return value if value > 0 else None


_buckets: dict[str, deque[float]] = {}


def check_rpc_rate_limit(method: str) -> tuple[bool, str]:
	limit = _limit_per_minute()
	if limit is None:
		return True, ""
	now = time.monotonic()
	window_start = now - 60.0
	bucket = _buckets.setdefault(method, deque())
	while bucket and bucket[0] < window_start:
		bucket.popleft()
	if len(bucket) >= limit:
		return False, "rate_limit_exceeded"
	bucket.append(now)
	return True, ""


def reset_rpc_rate_limit_for_tests() -> None:
	_buckets.clear()
