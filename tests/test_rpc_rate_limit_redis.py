"""TRACK-AIH1-REDIS — distributed RPC rate limit via a shared Redis fixed-window counter.

Uses an injected in-memory fake redis client, so no real Redis server is required.
"""

from __future__ import annotations

from utils.rpc_rate_limit import check_rpc_rate_limit, reset_rpc_rate_limit_for_tests


class FakeRedis:
	"""Minimal stand-in implementing only the incr/expire surface the limiter uses."""

	def __init__(self) -> None:
		self.counts: dict[str, int] = {}
		self.expires: dict[str, int] = {}
		self.fail = False

	def incr(self, key: str) -> int:
		if self.fail:
			raise RuntimeError("redis down")
		self.counts[key] = self.counts.get(key, 0) + 1
		return self.counts[key]

	def expire(self, key: str, secs: int) -> bool:
		self.expires[key] = secs
		return True


def test_allows_up_to_limit_then_rejects(monkeypatch):
	reset_rpc_rate_limit_for_tests()
	monkeypatch.setenv("AIH1_RPC_RATE_PER_MIN", "3")
	r = FakeRedis()

	for _ in range(3):
		assert check_rpc_rate_limit("Generate", redis_client=r) == (True, "")

	allowed, reason = check_rpc_rate_limit("Generate", redis_client=r)
	assert allowed is False
	assert reason == "rate_limit_exceeded"


def test_sets_ttl_once_on_the_first_hit(monkeypatch):
	reset_rpc_rate_limit_for_tests()
	monkeypatch.setenv("AIH1_RPC_RATE_PER_MIN", "5")
	r = FakeRedis()

	check_rpc_rate_limit("Generate", redis_client=r)
	check_rpc_rate_limit("Generate", redis_client=r)

	# Exactly one window key, TTL set to the 60s window, and only on the first increment.
	assert len(r.expires) == 1
	assert next(iter(r.expires.values())) == 60


def test_buckets_are_per_method(monkeypatch):
	reset_rpc_rate_limit_for_tests()
	monkeypatch.setenv("AIH1_RPC_RATE_PER_MIN", "1")
	r = FakeRedis()

	assert check_rpc_rate_limit("Generate", redis_client=r)[0] is True
	assert check_rpc_rate_limit("Generate", redis_client=r)[0] is False  # second Generate blocked
	assert check_rpc_rate_limit("ReviewContent", redis_client=r)[0] is True  # separate counter


def test_disabled_when_no_limit_env_does_not_touch_redis(monkeypatch):
	reset_rpc_rate_limit_for_tests()
	monkeypatch.delenv("AIH1_RPC_RATE_PER_MIN", raising=False)
	r = FakeRedis()

	for _ in range(50):
		assert check_rpc_rate_limit("Generate", redis_client=r) == (True, "")

	assert r.counts == {}  # the limiter short-circuits before any Redis call


def test_redis_outage_fails_open(monkeypatch):
	reset_rpc_rate_limit_for_tests()
	monkeypatch.setenv("AIH1_RPC_RATE_PER_MIN", "1")
	r = FakeRedis()
	r.fail = True

	# Even though we are past the limit, a Redis error must allow the call (never hard-block inference).
	assert check_rpc_rate_limit("Generate", redis_client=r) == (True, "")
