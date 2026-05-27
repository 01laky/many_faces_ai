"""In-process RPC metrics (AI-UP6). Prometheus text when prometheus_client is installed."""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[tuple[str, ...], int] = defaultdict(int)
_histograms: dict[str, list[float]] = defaultdict(list)

HEALTH_SCHEMA_VERSION = 1


def increment(name: str, **labels: str) -> None:
	key = (name, *sorted(f"{k}={v}" for k, v in labels.items()))
	with _lock:
		_counters[key] += 1


def observe_duration(name: str, seconds: float, **labels: str) -> None:
	increment(f"{name}_total", **labels)
	key = name
	with _lock:
		_histograms[key].append(seconds)


def snapshot() -> dict[str, int]:
	with _lock:
		return {"_".join(k): v for k, v in _counters.items()}


def reset_for_tests() -> None:
	with _lock:
		_counters.clear()
		_histograms.clear()


def render_prometheus_text() -> str:
	lines: list[str] = []
	with _lock:
		for key, value in sorted(_counters.items()):
			name = key[0]
			label_part = ",".join(key[1:])
			if label_part:
				lines.append(f"{name}{{{label_part}}} {value}")
			else:
				lines.append(f"{name} {value}")
	return "\n".join(lines) + ("\n" if lines else "")
