"""Ollama circuit breaker (AI-UP13)."""

from __future__ import annotations

import os
import threading
import time

from utils.env import env_int


class OllamaCircuitBreaker:
	def __init__(self) -> None:
		self._lock = threading.Lock()
		self._failures = 0
		self._open_until = 0.0
		self._threshold = env_int("OLLAMA_CB_FAILURE_THRESHOLD", 5)
		self._open_seconds = env_int("OLLAMA_CB_OPEN_SECONDS", 60)

	def state(self) -> str:
		now = time.monotonic()
		with self._lock:
			if now < self._open_until:
				return "open"
			if self._failures > 0:
				return "half_open"
			return "closed"

	def allow_request(self) -> bool:
		return self.state() != "open"

	def record_success(self) -> None:
		with self._lock:
			self._failures = 0
			self._open_until = 0.0

	def record_failure(self) -> None:
		with self._lock:
			self._failures += 1
			if self._failures >= self._threshold:
				self._open_until = time.monotonic() + float(self._open_seconds)
				self._failures = 0


_breaker: OllamaCircuitBreaker | None = None


def get_ollama_circuit_breaker() -> OllamaCircuitBreaker:
	global _breaker
	if _breaker is None:
		_breaker = OllamaCircuitBreaker()
	return _breaker


def circuit_breaker_disabled() -> bool:
	return os.getenv("OLLAMA_CB_DISABLED", "").strip().lower() in ("1", "true", "yes")
