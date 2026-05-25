"""Tests for optional AI worker gRPC token auth (BSH3-G3)."""

from __future__ import annotations

import grpc
import pytest

from utils.grpc_worker_auth import METADATA_KEY, WorkerAuthInterceptor


class _FakeContext:
	def __init__(self) -> None:
		self.code = None
		self.details = None

	def abort(self, code, details):
		self.code = code
		self.details = details
		raise RuntimeError("aborted")


class _FakeCallDetails:
	def __init__(self, method: str, metadata=None):
		self.method = method
		self.invocation_metadata = metadata or ()


def test_interceptor_allows_healthcheck_without_token():
	interceptor = WorkerAuthInterceptor("secret")
	called = {"value": False}

	def continuation(_details):
		called["value"] = True
		return "handler"

	result = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/HealthCheck"),
	)
	assert result == "handler"
	assert called["value"] is True


def test_interceptor_rejects_missing_token_on_application_rpc():
	interceptor = WorkerAuthInterceptor("secret")

	def continuation(_details):
		raise AssertionError("should not reach application handler")

	handler = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate"),
	)
	context = _FakeContext()
	with pytest.raises(RuntimeError):
		handler.unary_unary(None, context)
	assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_interceptor_accepts_matching_token():
	interceptor = WorkerAuthInterceptor("secret")
	metadata = ((METADATA_KEY, "secret"),)

	def continuation(_details):
		return "handler"

	result = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate", metadata=metadata),
	)
	assert result == "handler"
