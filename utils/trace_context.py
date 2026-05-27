"""gRPC trace metadata propagation (AI-UP6)."""

from __future__ import annotations

import logging
from contextvars import ContextVar

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_trace_from_metadata(metadata: tuple[tuple[str, str], ...] | None) -> None:
	if not metadata:
		return
	for key, value in metadata:
		k = key.lower()
		if k == "x-trace-id" and value:
			_trace_id.set(value)
		elif k == "x-correlation-id" and value:
			_correlation_id.set(value)


def trace_id() -> str | None:
	return _trace_id.get()


def correlation_id() -> str | None:
	return _correlation_id.get()


def log_extra() -> dict[str, str]:
	extra: dict[str, str] = {}
	tid = trace_id()
	cid = correlation_id()
	if tid:
		extra["trace_id"] = tid
	if cid:
		extra["correlation_id"] = cid
	return extra


class TraceContextFilter(logging.Filter):
	def filter(self, record: logging.LogRecord) -> bool:
		for k, v in log_extra().items():
			setattr(record, k, v)
		return True
