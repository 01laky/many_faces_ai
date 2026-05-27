"""Per-RPC usage accounting metadata (AI-UP14)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

_lock = threading.Lock()
_totals: dict[str, int] = {"requests": 0, "prompt_chars": 0, "completion_chars": 0}


@dataclass
class UsageRecord:
	rpc_name: str
	model_name: str
	duration_ms: float
	prompt_chars: int = 0
	completion_chars: int = 0
	prompt_tokens: int | None = None
	completion_tokens: int | None = None
	trace_id: str | None = None


class UsageTimer:
	def __init__(self, rpc_name: str, model_name: str) -> None:
		self.rpc_name = rpc_name
		self.model_name = model_name
		self._start = time.monotonic()

	def finish(
		self,
		prompt_chars: int = 0,
		completion_chars: int = 0,
		prompt_tokens: int | None = None,
		completion_tokens: int | None = None,
		trace_id: str | None = None,
	) -> UsageRecord:
		duration_ms = (time.monotonic() - self._start) * 1000.0
		record = UsageRecord(
			rpc_name=self.rpc_name,
			model_name=self.model_name,
			duration_ms=duration_ms,
			prompt_chars=prompt_chars,
			completion_chars=completion_chars,
			prompt_tokens=prompt_tokens,
			completion_tokens=completion_tokens,
			trace_id=trace_id,
		)
		with _lock:
			_totals["requests"] += 1
			_totals["prompt_chars"] += prompt_chars
			_totals["completion_chars"] += completion_chars
		return record


def usage_summary() -> dict[str, int]:
	with _lock:
		return dict(_totals)


def reset_for_tests() -> None:
	with _lock:
		_totals.clear()
		_totals.update({"requests": 0, "prompt_chars": 0, "completion_chars": 0})
