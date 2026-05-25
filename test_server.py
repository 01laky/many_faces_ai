#!/usr/bin/env python3
"""
test_server.py - Unit tests for AI Demo gRPC server

Tests the HealthService gRPC methods using pytest and grpcio-testing.
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

from services.operator_stats_prompt import allow_insecure_tls_for_host

pytestmark = pytest.mark.grpc

# Repo root (ai_demo) on path: `proto` package + `server` module
_APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)

try:
	import grpc  # noqa: F401 - availability check, used in TestServerIntegration
	import grpc_testing  # noqa: F401 - availability check

	import server

	health_pb2 = server.health_pb2
	health_pb2_grpc = server.health_pb2_grpc
	HealthServiceServicer = server.HealthServiceServicer
except ImportError as e:
	pytest.skip(f"Skipping gRPC tests: {e}", allow_module_level=True)


class TestHealthServiceServicer:
	"""Test suite for HealthServiceServicer"""

	@pytest.fixture
	def servicer(self):
		"""Create HealthServiceServicer instance"""
		return HealthServiceServicer()

	@pytest.fixture
	def mock_context(self):
		"""Create mock gRPC context"""
		context = MagicMock()
		context.code = lambda: None
		context.details = lambda: None
		return context

	def test_health_check_returns_success(self, servicer, mock_context):
		"""Test that HealthCheck returns success response"""
		# Arrange
		request = health_pb2.HealthCheckRequest()

		# Act
		response = servicer.HealthCheck(request, mock_context)

		# Assert
		assert response is not None
		assert response.status == "success"
		payload = json.loads(response.message)
		assert isinstance(payload, dict)
		assert "ready" in payload and "loading" in payload and "unavailable" in payload
		assert "modelName" in payload

	def test_health_check_request_type(self, servicer, mock_context):
		"""Test that HealthCheck accepts HealthCheckRequest"""
		# Arrange
		request = health_pb2.HealthCheckRequest()

		# Act
		response = servicer.HealthCheck(request, mock_context)

		# Assert
		assert isinstance(response, health_pb2.HealthCheckResponse)

	def test_health_check_multiple_calls(self, servicer, mock_context):
		"""Test that HealthCheck can be called multiple times"""
		# Arrange
		request = health_pb2.HealthCheckRequest()

		# Act - call multiple times
		response1 = servicer.HealthCheck(request, mock_context)
		response2 = servicer.HealthCheck(request, mock_context)
		response3 = servicer.HealthCheck(request, mock_context)

		# Assert
		assert response1.status == "success"
		assert response2.status == "success"
		assert response3.status == "success"
		assert response1.message == response2.message == response3.message

	def test_review_content_returns_structured_approval_recommendation(
		self, servicer, mock_context
	):
		"""Test baseline content moderation response shape for safe content"""
		request = health_pb2.ContentReviewRequest(
			content_type="Blog",
			content_id=42,
			moderation_version=1,
			face_id=1,
			title="Community update",
			body="A normal update for the community.",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert response.decision == "approve"
		assert response.risk_level == "low"
		assert 0 <= response.confidence <= 1
		assert response.model_version == "qwen-advisory-classifier-v2"
		assert response.trace_id.startswith("ai-review-")
		assert response.error == ""

	def test_review_content_flags_unsafe_content(self, servicer, mock_context):
		"""Test baseline moderation detects unsafe terms and recommends rejection"""
		request = health_pb2.ContentReviewRequest(
			content_type="Reel",
			content_id=43,
			moderation_version=1,
			face_id=1,
			title="Adult spam",
			body="This looks like adult scam content.",
			media_url="javascript:alert(1)",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert response.decision == "reject"
		assert response.risk_level == "high"
		assert "adult" in response.flags
		assert "scam" in response.flags
		assert "unsafe_link" in response.flags
		assert "video_analysis_boundary" in response.flags

	def test_review_content_flags_media_metadata_issues(self, servicer, mock_context):
		"""Test classifier fallback catches unsupported media without unsafe rendering"""
		request = health_pb2.ContentReviewRequest(
			content_type="Album",
			content_id=44,
			moderation_version=1,
			face_id=1,
			title="Gallery",
			body="Normal photos from a community event.",
			media_url="https://cdn.example.com/download.bin",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert response.decision == "needs_human_review"
		assert response.risk_level == "medium"
		assert "unsupported_media" in response.flags
		assert "image_analysis_boundary" in response.flags

	def test_review_content_image_boundary_does_not_block_clean_album(self, servicer, mock_context):
		request = health_pb2.ContentReviewRequest(
			content_type="Album",
			content_id=51,
			moderation_version=1,
			face_id=1,
			title="Summer photos",
			body="Photos from our verified community event at the park.",
			media_url="https://cdn.example.com/photo.jpg",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert "image_analysis_boundary" in response.flags
		assert response.decision == "approve"

	def test_review_content_adds_video_boundary_for_reel(self, servicer, mock_context):
		request = health_pb2.ContentReviewRequest(
			content_type="Reel",
			content_id=53,
			moderation_version=1,
			face_id=1,
			title="Community reel",
			body="Short clip from the weekend meetup.",
			media_url="https://cdn.example.com/clip.mp4",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert "video_analysis_boundary" in response.flags
		assert response.decision == "approve"

	def test_review_content_handles_empty_title_and_body(self, servicer, mock_context):
		request = health_pb2.ContentReviewRequest(
			content_type="Blog",
			content_id=52,
			moderation_version=1,
			face_id=1,
			title="",
			body="",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert response.trace_id.startswith("ai-review-")
		assert response.decision in ("approve", "needs_human_review", "reject")
		assert response.error == ""

	def test_review_content_flags_low_quality_input(self, servicer, mock_context):
		"""Test classifier fallback sends sparse content to human review"""
		request = health_pb2.ContentReviewRequest(
			content_type="Blog",
			content_id=45,
			moderation_version=1,
			face_id=1,
			title="Hi",
			body="",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert response.decision == "needs_human_review"
		assert "low_quality" in response.flags

	def test_review_content_sanitizes_inputs_before_keyword_classification(
		self, servicer, mock_context
	):
		"""Zero-width characters must not break substring-based policy terms."""
		zw = "\u200b"
		request = health_pb2.ContentReviewRequest(
			content_type="Blog",
			content_id=99,
			moderation_version=1,
			face_id=1,
			title=f"sp{zw}am",
			body="giveaway content that is long enough for the classifier.",
			creator_id="user-1",
		)

		response = servicer.ReviewContent(request, mock_context)

		assert "spam" in response.flags

	def test_ai_model_service_defaults_to_ollama_model_with_env_override(self, monkeypatch):
		"""Test configured Ollama model defaults without calling Ollama."""
		from services.ai_model_service import DEFAULT_MODEL_NAME, AIModelService

		assert DEFAULT_MODEL_NAME == "qwen2.5:7b-instruct-q4_K_M"

		monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
		service = AIModelService()
		assert service._model_name == "qwen2.5:7b-instruct-q4_K_M"

	def test_ai_model_service_ollama_backend_uses_chat_options(self, monkeypatch):
		"""Ollama mode should keep gRPC surface but call Ollama with resource options."""
		from services.ai_model_service import AIModelService

		monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
		monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
		monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")
		monkeypatch.setenv("OLLAMA_NUM_THREAD", "8")
		monkeypatch.setenv("OLLAMA_NUM_GPU", "20")
		monkeypatch.setenv("OLLAMA_NUM_BATCH", "128")

		service = AIModelService()
		calls = []

		def fake_post(path: str, payload: dict, **kwargs) -> dict:
			calls.append((path, payload))
			if path == "/api/show":
				return {"model": payload["model"]}
			if path == "/api/chat":
				return {"message": {"content": "42"}}
			raise AssertionError(path)

		monkeypatch.setattr(service, "_ollama_post_json", fake_post)

		assert service.model_name == "qwen2.5:7b-instruct-q4_K_M"
		assert service.generate("User: How many users are registered?\nAI:", 12) == "42"

		chat_payload = next(payload for path, payload in calls if path == "/api/chat")
		assert chat_payload["model"] == "qwen2.5:7b-instruct-q4_K_M"
		assert chat_payload["stream"] is False
		assert chat_payload["options"]["num_ctx"] == 4096
		assert chat_payload["options"]["num_thread"] == 8
		assert chat_payload["options"]["num_gpu"] == 20
		assert chat_payload["options"]["num_batch"] == 128


class TestModerationInputSanitize:
	def test_sanitize_strips_bidi_and_zero_width(self):
		from moderation_input_sanitize import sanitize_for_review

		t, b, m = sanitize_for_review("A\u200bB", "x", " https://a.test/x.jpg\u200b ")
		assert t == "AB"
		assert b == "x"
		assert m == "https://a.test/x.jpg"


class TestGenerateWithStatsContext:
	"""Edge cases for Generate + stats_context_json (operator admin chat)."""

	@pytest.fixture
	def servicer(self):
		return HealthServiceServicer()

	@pytest.fixture
	def mock_context(self):
		context = MagicMock()
		context.code = lambda: None
		context.details = lambda: None
		return context

	def test_generate_returns_error_when_ai_service_unavailable(
		self, servicer, mock_context, monkeypatch
	):
		monkeypatch.setattr(server, "_ai_service", None)
		req = health_pb2.GenerateRequest(prompt="User: x\nAI:", max_new_tokens=10)
		req.stats_context_json = '{"usersCount":1}'
		resp = servicer.Generate(req, mock_context)
		assert resp.text == ""
		assert "AIModelService not available" in resp.error

	def test_generate_prepends_stats_context_json_before_prompt(
		self, servicer, mock_context, monkeypatch
	):
		mock_ai = MagicMock()
		mock_ai.generate = MagicMock(return_value="ok")
		monkeypatch.setattr(server, "_ai_service", mock_ai)
		req = health_pb2.GenerateRequest(prompt="User: hi\nAI:", max_new_tokens=12)
		req.stats_context_json = '{"usersCount":3}'
		resp = servicer.Generate(req, mock_context)
		assert resp.error == ""
		assert resp.text == "ok"
		mock_ai.generate.assert_called_once()
		full_prompt = mock_ai.generate.call_args[0][0]
		assert "Operator platform statistics JSON" in full_prompt
		assert '"usersCount":3' in full_prompt
		assert full_prompt.endswith("User: hi\nAI:")

	def test_generate_passes_response_locale_to_model(self, servicer, mock_context, monkeypatch):
		mock_ai = MagicMock()
		mock_ai.generate = MagicMock(return_value="ok")
		monkeypatch.setattr(server, "_ai_service", mock_ai)
		req = health_pb2.GenerateRequest(prompt="User: hi\nAI:", max_new_tokens=12)
		req.response_locale = "en"
		resp = servicer.Generate(req, mock_context)
		assert resp.error == ""
		mock_ai.generate.assert_called_once()
		assert mock_ai.generate.call_args.kwargs.get("response_locale") == "en"

	def test_parse_prompt_preserves_operator_stats_context(self):
		prompt = (
			"[Operator platform statistics JSON — authoritative DB snapshot at snapshotUtc. "
			"Use dashboard.* for totals.]\n"
			'{"dashboard":{"usersCount":42},"timeseriesLast7Days":{"series":[]}}\n\n'
			"---\n\n"
			"User: How many users are registered?\n"
			"AI:"
		)

		ai_model_service = pytest.importorskip("services.ai_model_service")
		messages = ai_model_service.AIModelService._parse_prompt(prompt)

		stats_messages = [
			msg
			for msg in messages
			if msg["role"] == "system" and '"usersCount":42' in msg["content"]
		]
		assert len(stats_messages) == 1
		assert messages[-2] is stats_messages[0]
		assert messages[-1] == {"role": "user", "content": "How many users are registered?"}

	def test_generate_stats_context_whitespace_only_behaves_like_absent(
		self, servicer, mock_context, monkeypatch
	):
		mock_ai = MagicMock()
		mock_ai.generate = MagicMock(return_value="y")
		monkeypatch.setattr(server, "_ai_service", mock_ai)
		req = health_pb2.GenerateRequest(prompt="User: z\nAI:", max_new_tokens=10)
		req.stats_context_json = "   \n\t  "
		resp = servicer.Generate(req, mock_context)
		assert resp.error == ""
		assert mock_ai.generate.call_args[0][0] == "User: z\nAI:"

	def test_generate_rejects_empty_prompt(self, servicer, mock_context, monkeypatch):
		mock_ai = MagicMock()
		mock_ai.generate = MagicMock(return_value="should-not-run")
		monkeypatch.setattr(server, "_ai_service", mock_ai)
		req = health_pb2.GenerateRequest(prompt="", max_new_tokens=10)
		resp = servicer.Generate(req, mock_context)
		assert resp.text == ""
		assert "prompt is required" in resp.error
		mock_ai.generate.assert_not_called()

	def test_generate_rejects_whitespace_only_prompt(self, servicer, mock_context, monkeypatch):
		mock_ai = MagicMock()
		monkeypatch.setattr(server, "_ai_service", mock_ai)
		req = health_pb2.GenerateRequest(prompt="  \n\t  ", max_new_tokens=10)
		resp = servicer.Generate(req, mock_context)
		assert resp.text == ""
		assert "prompt is required" in resp.error
		mock_ai.generate.assert_not_called()

	def test_stats_context_prefix_keeps_backend_separator_contract(self):
		from services.operator_stats_prompt import stats_context_prefix

		prefix = stats_context_prefix('{"dashboard":{"usersCount":7}}')

		assert prefix.startswith("[Operator platform statistics JSON")
		assert '"usersCount":7' in prefix
		assert prefix.endswith("\n\n---\n\n")


class TestFetchPublicStats:
	@pytest.fixture
	def servicer(self):
		return HealthServiceServicer()

	@pytest.fixture
	def mock_context(self):
		return MagicMock()

	def test_rejects_non_http_scheme(self, servicer, mock_context):
		req = health_pb2.FetchPublicStatsRequest(absolute_url="ftp://example.com/x")
		resp = servicer.FetchPublicStats(req, mock_context)
		assert resp.json_body == ""
		assert "http" in resp.error.lower()

	def test_rejects_javascript_url(self, servicer, mock_context):
		req = health_pb2.FetchPublicStatsRequest(absolute_url="javascript:alert(1)")
		resp = servicer.FetchPublicStats(req, mock_context)
		assert resp.json_body == ""
		assert resp.error

	def test_rejects_empty_and_whitespace_url(self, servicer, mock_context):
		for url in ("", "   ", "\t"):
			req = health_pb2.FetchPublicStatsRequest(absolute_url=url)
			resp = servicer.FetchPublicStats(req, mock_context)
			assert resp.json_body == ""
			assert resp.error.lower() in ("empty", "absolute_url must be http(s)")

	def test_insecure_tls_bypass_is_loopback_only(self):
		assert allow_insecure_tls_for_host("localhost")
		assert allow_insecure_tls_for_host("127.0.0.1")
		assert allow_insecure_tls_for_host("::1")
		assert not allow_insecure_tls_for_host("api.example.com")
		assert not allow_insecure_tls_for_host("localhost.example.com")


class TestOperatorStatsChat:
	@pytest.fixture
	def servicer(self):
		return HealthServiceServicer()

	@pytest.fixture
	def mock_context(self):
		return MagicMock()

	def test_requires_user_message(self, servicer, mock_context):
		req = health_pb2.OperatorStatsChatRequest(
			user_message="   ",
			history_text="",
			fetch_live_public_snapshot=False,
			public_stats_absolute_url="",
			max_new_tokens=50,
		)
		resp = servicer.OperatorStatsChat(req, mock_context)
		assert resp.text == ""
		assert "user_message" in resp.error.lower()

	def test_live_mode_requires_public_stats_url(self, servicer, mock_context):
		req = health_pb2.OperatorStatsChatRequest(
			user_message="Summarize",
			history_text="",
			fetch_live_public_snapshot=True,
			public_stats_absolute_url="",
			max_new_tokens=50,
		)
		resp = servicer.OperatorStatsChat(req, mock_context)
		assert resp.text == ""
		assert "public_stats_absolute_url" in resp.error.lower()

	def test_offline_live_fetch_returns_error_not_crash(self, servicer, mock_context):
		req = health_pb2.OperatorStatsChatRequest(
			user_message="Hello",
			history_text="",
			fetch_live_public_snapshot=True,
			public_stats_absolute_url="http://127.0.0.1:9/stats-unreachable",
			max_new_tokens=50,
		)
		resp = servicer.OperatorStatsChat(req, mock_context)
		assert resp.text == ""
		assert resp.error

	def test_compose_prompt_preserves_existing_history_and_latest_user_turn(self):
		from services.operator_stats_prompt import compose_operator_chat_prompt

		composed = compose_operator_chat_prompt("User: hi\nAI: hello", "Summarize")

		assert composed == "User: hi\nAI: hello\nUser: Summarize\nAI:"

	def test_compose_prompt_does_not_add_extra_newline_when_history_already_has_one(self):
		from services.operator_stats_prompt import compose_operator_chat_prompt

		composed = compose_operator_chat_prompt("User: hi\nAI: hello\n", "Next")

		assert composed == "User: hi\nAI: hello\nUser: Next\nAI:"


class TestServerIntegration:
	"""Integration tests for gRPC server"""

	def test_health_service_registration(self):
		"""Test that HealthService can be registered on server"""
		# Arrange
		from concurrent import futures

		import grpc

		server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

		# Act
		health_pb2_grpc.add_HealthServiceServicer_to_server(HealthServiceServicer(), server)

		# Assert - no exception should be raised
		assert server is not None


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
