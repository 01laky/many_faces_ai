"""
Edge-case tests for the 7B operator-AI performance work (operator-ai-7b-performance-v1).

Covers:
  O1  — keep_alive default flips from "30m" to "-1" when env unset.
  O11 — per-call temperature/stop applied to Ollama options; absent => worker defaults.
  O19 — per-call model override used for a call without mutating instance state.
  O4  — true streaming yields multiple non-final deltas then a final is_final chunk;
        a mid-stream error collapses to one terminal error chunk; a streaming-unavailable
        failure falls back to the old chunked-generate behaviour.
  O19 — pull_helper_model: disabled (empty env) => no pull; absent => /api/pull; present => no pull.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
# The generated stubs live in proto/; the *_grpc module does a bare `import health_pb2`,
# so proto/ must be importable directly (mirrors server.py bootstrap).
sys.path.insert(0, str(_ROOT / "proto"))

from handlers.rpc_handlers import RpcHandlers  # noqa: E402
from services.ai_model_service import AIModelService, _keep_alive  # noqa: E402
from utils import metrics as metrics_util  # noqa: E402
from utils.grpc_errors import GENERATION_FAILED  # noqa: E402
from utils.model_routing import _PROFILE_ENV, PROFILE_HELPER, resolve_model  # noqa: E402
from utils.ollama_circuit_breaker import get_ollama_circuit_breaker  # noqa: E402


@pytest.fixture(autouse=True)
def reset_metrics_and_breaker():
	metrics_util.reset_for_tests()
	get_ollama_circuit_breaker().__init__()
	yield
	metrics_util.reset_for_tests()


@pytest.fixture
def pb2():
	import health_pb2

	return health_pb2


@pytest.fixture
def handlers(pb2):
	return RpcHandlers(
		ai_service=None, health_pb2=pb2, host_profile_collector=lambda _m: {"ok": True}
	)


@pytest.fixture
def ctx():
	c = MagicMock()
	c.time_remaining.return_value = 30.0
	c.invocation_metadata.return_value = (("x-trace-id", "trace-7b"),)
	return c


def _service() -> AIModelService:
	"""A service instance with model availability stubbed out (no real Ollama)."""
	svc = AIModelService(model_name="test-7b")
	# _ensure_loaded() calls _ensure_ollama_ready(); short-circuit it so generate()/
	# generate_stream() reach the payload-building code without a live server.
	svc._ensure_loaded = lambda: None  # type: ignore[method-assign]
	return svc


class _FakeAI:
	"""
	Minimal ready AIModelService stand-in. We use a real class (not MagicMock)
	because RpcHandlers._ai getter calls the ref if it is callable — a MagicMock
	is callable and would return a child mock instead of itself (see _ready_ai in
	the roadmap edge tests for the same convention).
	"""

	model_name = "test-7b"

	def __init__(self, *, generate_text="reply", stream=None, stream_exc=None):
		self._generate_text = generate_text
		self._stream = stream
		self._stream_exc = stream_exc
		self.generate_kwargs = None
		self.generate_calls = 0

	def is_loading(self) -> bool:
		return False

	def is_unavailable(self) -> bool:
		return False

	def is_loaded(self) -> bool:
		return True

	def load_error(self):
		return None

	def generate(self, *_args, **kwargs):
		self.generate_calls += 1
		self.generate_kwargs = kwargs
		return self._generate_text

	def generate_stream(self, *_args, **_kwargs):
		if self._stream_exc is not None:
			# Either raise immediately (before any delta) or yield-then-raise,
			# depending on the configured exception shape.
			if callable(self._stream_exc):
				yield from self._stream_exc()
				return
			raise self._stream_exc
		yield from self._stream or []


class TestO1KeepAlive:
	def test_o1_u1_keep_alive_default_is_minus_one(self, monkeypatch):
		monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
		assert _keep_alive() == "-1"

	def test_o1_u2_keep_alive_in_generate_payload(self, monkeypatch):
		monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
		svc = _service()
		captured = {}

		def fake_post(path, payload, *, rpc_deadline_seconds=None):
			captured["path"] = path
			captured["payload"] = payload
			return {"message": {"content": "ok"}}

		svc._ollama_post_json = fake_post  # type: ignore[method-assign]
		svc.generate("User: hi")
		assert captured["payload"]["keep_alive"] == "-1"

	def test_o1_u3_keep_alive_env_override_respected(self, monkeypatch):
		monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "30m")
		assert _keep_alive() == "30m"


class TestO11PerCallSampling:
	def test_o11_u1_temperature_and_stop_applied(self, monkeypatch):
		svc = _service()
		captured = {}

		def fake_post(path, payload, *, rpc_deadline_seconds=None):
			captured["payload"] = payload
			return {"message": {"content": "ok"}}

		svc._ollama_post_json = fake_post  # type: ignore[method-assign]
		svc.generate("User: hi", temperature=0.0, stop=["\n\n", "###"])
		opts = captured["payload"]["options"]
		assert opts["temperature"] == 0.0
		assert opts["stop"] == ["\n\n", "###"]

	def test_o11_u2_absent_uses_worker_defaults(self, monkeypatch):
		monkeypatch.delenv("OLLAMA_TEMPERATURE", raising=False)
		svc = _service()
		captured = {}

		def fake_post(path, payload, *, rpc_deadline_seconds=None):
			captured["payload"] = payload
			return {"message": {"content": "ok"}}

		svc._ollama_post_json = fake_post  # type: ignore[method-assign]
		svc.generate("User: hi")
		opts = captured["payload"]["options"]
		# Worker default temperature (0.35) preserved; no stop key injected.
		assert opts["temperature"] == pytest.approx(0.35)
		assert "stop" not in opts

	def test_o11_u3_negative_temperature_ignored(self):
		svc = _service()
		opts = svc._ollama_options(64, temperature=-1.0, stop=[])
		# Negative temp treated as "not provided" -> default kept; empty stop dropped.
		assert opts["temperature"] == pytest.approx(0.35)
		assert "stop" not in opts

	def test_o11_u4_handler_reads_optional_fields(self, handlers, pb2, ctx):
		# temperature unset -> None; stop empty -> []; model unset -> None.
		req = pb2.GenerateRequest(prompt="hi")
		temperature, stop, model = handlers._generation_overrides(req)
		assert temperature is None
		assert stop == []
		assert model is None
		# now set them
		req2 = pb2.GenerateRequest(prompt="hi", temperature=0.1, stop=["x"], model="helper")
		temperature, stop, model = handlers._generation_overrides(req2)
		assert temperature == pytest.approx(0.1)
		assert stop == ["x"]
		assert model == "helper"

	def test_o11_u5_handler_threads_overrides_into_generate(self, handlers, pb2, ctx):
		fake = _FakeAI(generate_text="reply")
		handlers._ai = fake
		req = pb2.GenerateRequest(prompt="hi", temperature=0.0, stop=["###"], model="helper")
		handlers.generate(req, ctx)
		kwargs = fake.generate_kwargs
		assert kwargs["temperature"] == pytest.approx(0.0)
		assert kwargs["stop"] == ["###"]
		assert kwargs["model"] == "helper"


class TestO19ModelOverride:
	def test_o19_u1_per_call_model_used_not_instance_default(self):
		svc = _service()
		captured = {}

		def fake_post(path, payload, *, rpc_deadline_seconds=None):
			captured["payload"] = payload
			return {"message": {"content": "ok"}}

		svc._ollama_post_json = fake_post  # type: ignore[method-assign]
		svc.generate("User: hi", model="tiny-helper")
		assert captured["payload"]["model"] == "tiny-helper"
		# Instance default must be untouched.
		assert svc.model_name == "test-7b"

	def test_o19_u2_empty_model_falls_back_to_default(self):
		svc = _service()
		captured = {}

		def fake_post(path, payload, *, rpc_deadline_seconds=None):
			captured["payload"] = payload
			return {"message": {"content": "ok"}}

		svc._ollama_post_json = fake_post  # type: ignore[method-assign]
		svc.generate("User: hi", model="   ")
		assert captured["payload"]["model"] == "test-7b"

	def test_o19_u3_helper_profile_env_mapping(self, monkeypatch):
		assert _PROFILE_ENV[PROFILE_HELPER] == "OLLAMA_MODEL_HELPER"
		monkeypatch.setenv("OLLAMA_MODEL_HELPER", "qwen2.5:0.5b")
		assert resolve_model(PROFILE_HELPER) == "qwen2.5:0.5b"


class TestO4Streaming:
	def test_o4_u1_yields_deltas_then_final(self, handlers, pb2, ctx):
		handlers._ai = _FakeAI(stream=["Hello", " ", "world"])
		req = pb2.GenerateRequest(prompt="hi")
		chunks = list(handlers.generate_stream(req, ctx))
		non_final = [c for c in chunks if not c.is_final]
		assert [c.text_delta for c in non_final] == ["Hello", " ", "world"]
		assert chunks[-1].is_final is True
		assert chunks[-1].finish_reason == "stop"
		assert chunks[-1].error == ""

	def test_o4_u2_mid_stream_error_one_terminal_chunk(self, handlers, pb2, ctx):
		def exploding_stream():
			yield "partial"
			raise RuntimeError("boom mid-stream")

		handlers._ai = _FakeAI(stream_exc=exploding_stream)
		req = pb2.GenerateRequest(prompt="hi")
		chunks = list(handlers.generate_stream(req, ctx))
		# one partial delta + exactly one terminal error chunk
		assert chunks[0].text_delta == "partial"
		terminals = [c for c in chunks if c.is_final]
		assert len(terminals) == 1
		assert terminals[0].error == "boom mid-stream"
		assert terminals[0].error_code == GENERATION_FAILED

	def test_o4_u3_streaming_unavailable_falls_back_to_chunked(self, handlers, pb2, ctx):
		fake = _FakeAI(
			generate_text="Full chunked answer text here",
			stream_exc=RuntimeError("streaming unsupported"),
		)
		handlers._ai = fake
		req = pb2.GenerateRequest(prompt="hi")
		chunks = list(handlers.generate_stream(req, ctx))
		reassembled = "".join(c.text_delta for c in chunks)
		assert reassembled == "Full chunked answer text here"
		assert chunks[-1].is_final is True
		# No error surfaced — the fallback produced a clean answer.
		assert all(c.error == "" for c in chunks)
		assert fake.generate_calls == 1

	def test_o4_u4_service_generate_stream_parses_ndjson(self, monkeypatch):
		svc = _service()
		# Simulate Ollama NDJSON lines: two content deltas then a done marker.
		lines = [
			b'{"message":{"content":"Hel"}}\n',
			b'{"message":{"content":"lo"}}\n',
			b'{"message":{"content":""},"done":true}\n',
		]

		class FakeResp:
			def __enter__(self):
				return self

			def __exit__(self, *a):
				return False

			def __iter__(self):
				return iter(lines)

		monkeypatch.setattr(
			"services.ai_model_service.urllib.request.urlopen",
			lambda *a, **k: FakeResp(),
		)
		out = list(svc.generate_stream("User: hi"))
		assert out == ["Hel", "lo"]


class TestO19PullHelperModel:
	def _load_module(self):
		path = _ROOT / "scripts" / "pull_helper_model.py"
		spec = importlib.util.spec_from_file_location("pull_helper_model_test", path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod

	def test_o19_pull_u1_empty_env_no_pull(self, monkeypatch):
		monkeypatch.delenv("OLLAMA_MODEL_HELPER", raising=False)
		mod = self._load_module()
		with patch.object(mod, "_post_json") as post:
			rc = mod.main()
		assert rc == 0
		post.assert_not_called()

	def test_o19_pull_u2_absent_triggers_pull(self, monkeypatch):
		monkeypatch.setenv("OLLAMA_MODEL_HELPER", "qwen2.5:0.5b")
		mod = self._load_module()
		calls = []

		def fake_post(path, payload, timeout):
			calls.append((path, payload))
			if path == "/api/show":
				return 404, None  # absent
			return 200, {"status": "success"}

		with patch.object(mod, "_post_json", side_effect=fake_post):
			rc = mod.main()
		assert rc == 0
		paths = [p for p, _ in calls]
		assert "/api/show" in paths
		assert "/api/pull" in paths

	def test_o19_pull_u3_present_no_pull(self, monkeypatch):
		monkeypatch.setenv("OLLAMA_MODEL_HELPER", "qwen2.5:0.5b")
		mod = self._load_module()
		calls = []

		def fake_post(path, payload, timeout):
			calls.append(path)
			if path == "/api/show":
				return 200, {"model": "present"}
			return 200, None

		with patch.object(mod, "_post_json", side_effect=fake_post):
			rc = mod.main()
		assert rc == 0
		assert calls == ["/api/show"]  # never pulled

	def test_o19_pull_u4_errors_never_fail(self, monkeypatch):
		monkeypatch.setenv("OLLAMA_MODEL_HELPER", "qwen2.5:0.5b")
		mod = self._load_module()
		with patch.object(mod, "_post_json", side_effect=OSError("network down")):
			rc = mod.main()
		assert rc == 0  # best-effort: container must still start
