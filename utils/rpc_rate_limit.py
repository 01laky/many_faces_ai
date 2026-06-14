"""RPC rate limit (AIH1-C4).

In-process per-minute counter by default. When ``AIH1_RPC_RATE_REDIS_URL`` is set, the limit becomes
**distributed** across worker instances via a shared Redis fixed-window counter (TRACK-AIH1-REDIS). The
``redis`` package is imported lazily and only when that URL is set, so the base worker keeps no hard Redis
dependency; if Redis is unreachable or the package is missing, the limiter degrades to in-process rather
than failing the RPC path.
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Any


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

# Lazily-resolved shared Redis client: None until first use, and whenever distributed mode is off.
_redis_client_cache: Any | None = None
_redis_resolved = False


def _resolve_redis_client() -> Any | None:
	"""Build a Redis client from ``AIH1_RPC_RATE_REDIS_URL`` once, lazily.

	Distributed rate limiting is opt-in: with no URL set (or the ``redis`` package missing / a bad URL)
	this returns ``None`` and the limiter falls back to the in-process counter.
	"""
	global _redis_client_cache, _redis_resolved
	if _redis_resolved:
		return _redis_client_cache
	_redis_resolved = True
	url = os.getenv("AIH1_RPC_RATE_REDIS_URL", "").strip()
	if not url:
		_redis_client_cache = None
		return None
	try:
		import redis  # lazy: only needed when distributed mode is enabled

		_redis_client_cache = redis.from_url(url)
	except Exception:
		_redis_client_cache = None
	return _redis_client_cache


def _check_redis(client: Any, method: str, limit: int) -> tuple[bool, str]:
	"""Fixed-window counter shared across instances: INCR a per-minute key, set the TTL on the first hit.

	Fails **open** (allows the call) on any Redis error so an outage never hard-blocks inference.
	"""
	try:
		window = int(time.time() // 60)
		key = f"aih1:rpc_rate:{method}:{window}"
		count = int(client.incr(key))
		if count == 1:
			client.expire(key, 60)
		if count > limit:
			return False, "rate_limit_exceeded"
		return True, ""
	except Exception:
		return True, ""


def _check_in_process(method: str, limit: int) -> tuple[bool, str]:
	now = time.monotonic()
	window_start = now - 60.0
	bucket = _buckets.setdefault(method, deque())
	while bucket and bucket[0] < window_start:
		bucket.popleft()
	if len(bucket) >= limit:
		return False, "rate_limit_exceeded"
	bucket.append(now)
	return True, ""


def check_rpc_rate_limit(method: str, *, redis_client: Any | None = None) -> tuple[bool, str]:
	"""Return ``(allowed, reason)``. Distributed when a Redis client is configured, else in-process.

	``redis_client`` is injectable for tests; in production it is resolved from the env once.
	"""
	limit = _limit_per_minute()
	if limit is None:
		return True, ""
	client = redis_client if redis_client is not None else _resolve_redis_client()
	if client is not None:
		return _check_redis(client, method, limit)
	return _check_in_process(method, limit)


def reset_redis_client_for_tests() -> None:
	global _redis_client_cache, _redis_resolved
	_redis_client_cache = None
	_redis_resolved = False


def reset_rpc_rate_limit_for_tests() -> None:
	_buckets.clear()
	reset_redis_client_for_tests()
