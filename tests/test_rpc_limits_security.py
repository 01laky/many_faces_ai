"""AIH1-T-C* — RPC prompt and token limits."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from utils.rpc_limits import MAX_NEW_TOKENS_CAP, MAX_PROMPT_CHARS, clamp_max_new_tokens
from utils.rpc_rate_limit import check_rpc_rate_limit, reset_rpc_rate_limit_for_tests


def test_aih1_t_c01_empty_generate_prompt():
	import health_pb2

	from server import HealthServiceServicer

	servicer = HealthServiceServicer()
	context = MagicMock()
	context.time_remaining.return_value = 30.0
	context.invocation_metadata.return_value = ()
	request = health_pb2.GenerateRequest(prompt="   ")
	response = servicer.Generate(request, context)
	assert response.error == "prompt is required"


def test_aih1_t_c02_prompt_over_max_length():
	from server import HealthServiceServicer

	servicer = HealthServiceServicer()
	context = MagicMock()
	request = MagicMock(prompt="x" * (MAX_PROMPT_CHARS + 1))
	request.HasField.return_value = False
	request.max_new_tokens = 0
	with patch("server._ai_service", MagicMock()):
		response = servicer.Generate(request, context)
	assert response.error == "prompt too long"


def test_aih1_t_c03_max_new_tokens_clamped():
	assert clamp_max_new_tokens(9999) == MAX_NEW_TOKENS_CAP


def test_aih1_t_c04_max_new_tokens_zero_uses_default():
	assert clamp_max_new_tokens(0) == 50


def test_aih1_t_c05_rate_limit_exceeded():
	reset_rpc_rate_limit_for_tests()
	with patch.dict(os.environ, {"AIH1_RPC_RATE_PER_MIN": "1"}, clear=False):
		ok, _ = check_rpc_rate_limit("Generate")
		assert ok is True
		ok, reason = check_rpc_rate_limit("Generate")
		assert ok is False
		assert reason == "rate_limit_exceeded"
	reset_rpc_rate_limit_for_tests()
