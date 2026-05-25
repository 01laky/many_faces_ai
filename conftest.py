"""Shared pytest fixtures for ai_demo (hermetic gRPC tests)."""

import pytest


@pytest.fixture
def grpc_timeout_seconds() -> float:
	"""Default short timeout for mocked channel tests."""
	return 5.0
