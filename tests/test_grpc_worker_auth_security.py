"""AIH1-T-A* — gRPC worker auth and TLS env validation."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import grpc
import pytest

from utils.grpc_worker_auth import METADATA_KEY, WorkerAuthInterceptor
from utils.validate_worker_env import WorkerEnvValidationError, validate_worker_env


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


def test_aih1_t_a01_missing_token_on_generate():
	interceptor = WorkerAuthInterceptor("secret")

	def continuation(_details):
		raise AssertionError("should not reach handler")

	handler = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate"),
	)
	context = _FakeContext()
	with pytest.raises(RuntimeError):
		handler.unary_unary(None, context)
	assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_aih1_t_a02_wrong_token():
	interceptor = WorkerAuthInterceptor("secret")
	metadata = ((METADATA_KEY, "wrong"),)

	def continuation(_details):
		raise AssertionError("should not reach handler")

	handler = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate", metadata=metadata),
	)
	context = _FakeContext()
	with pytest.raises(RuntimeError):
		handler.unary_unary(None, context)
	assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_aih1_t_a03_matching_token():
	interceptor = WorkerAuthInterceptor("secret")
	metadata = ((METADATA_KEY, "secret"),)

	def continuation(_details):
		return "handler"

	result = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate", metadata=metadata),
	)
	assert result == "handler"


def test_aih1_t_a04_healthcheck_without_token_when_auth_enabled():
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


def test_aih1_t_a05_empty_expected_token_skips_enforcement():
	interceptor = WorkerAuthInterceptor("")
	called = {"value": False}

	def continuation(_details):
		called["value"] = True
		return "handler"

	result = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate"),
	)
	assert result == "handler"
	assert called["value"] is True


def test_aih1_t_a06_hardened_missing_token_fails_startup():
	env = {
		"MFAI_REQUIRE_WORKER_AUTH": "1",
		"AI_WORKER_EXPECTED_TOKEN": "",
		"MFAI_ALLOW_INSECURE_GRPC": "1",
	}
	with patch.dict(os.environ, env, clear=False):
		with pytest.raises(WorkerEnvValidationError, match="AI_WORKER_EXPECTED_TOKEN"):
			validate_worker_env()


def test_aih1_t_a07_tls_env_missing_cert_files():
	env = {
		"MFAI_REQUIRE_WORKER_AUTH": "1",
		"AI_WORKER_EXPECTED_TOKEN": "tok",
		"GRPC_TLS_CERT_FILE": "/no/such/cert.pem",
		"GRPC_TLS_KEY_FILE": "/no/such/key.pem",
	}
	with patch.dict(os.environ, env, clear=False):
		with pytest.raises(WorkerEnvValidationError, match="GRPC_TLS"):
			validate_worker_env()


def test_aih1_t_a08_metadata_key_case_sensitive():
	interceptor = WorkerAuthInterceptor("secret")
	metadata = (("X-AI-Worker-Token", "secret"),)

	def continuation(_details):
		raise AssertionError("should not reach handler")

	handler = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/Generate", metadata=metadata),
	)
	context = _FakeContext()
	with pytest.raises(RuntimeError):
		handler.unary_unary(None, context)
	assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_aih1_t_a09b_healthcheck_requires_token_when_flag_set():
	interceptor = WorkerAuthInterceptor("secret", require_healthcheck_token=True)

	def continuation(_details):
		raise AssertionError("should not reach handler")

	handler = interceptor.intercept_service(
		continuation,
		_FakeCallDetails("/health.HealthService/HealthCheck"),
	)
	context = _FakeContext()
	with pytest.raises(RuntimeError):
		handler.unary_unary(None, context)
	assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_aih1_t_a09c_healthcheck_payload_has_no_secrets():
	from server import _model_status_payload

	payload = _model_status_payload()
	raw = json.dumps(payload)
	assert "AI_WORKER_EXPECTED_TOKEN" not in raw
	assert "x-ai-worker-token" not in raw.lower()
	assert "password" not in raw.lower()
