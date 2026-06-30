"""
Phase 2 — worker startup readiness + model-pull tests (D6/D7/D8/D18/D19).

These pin the deterministic surface of the background warm-up: the model is "ready" ONLY after a
real generation succeeds (not merely that /api/show returned), "loading" while warming/pulling, and
"unavailable" on a failed warm-up — plus the best-effort multi-model pull and the time-to-ready metric.
All Ollama HTTP is stubbed; nothing here talks to a real Ollama.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import services.ai_model_service as ams
from services import ollama_pull
from services.ai_model_service import (
	READINESS_LOADING,
	READINESS_NOT_STARTED,
	AIModelService,
)
from utils import metrics


def _svc() -> AIModelService:
	return AIModelService(model_name="test-model")


# ── D7 — honest readiness: ready only after a real generation ────────────────────────────────────


def test_warm_up_reports_ready_only_after_a_real_generate(monkeypatch):
	svc = _svc()
	monkeypatch.setattr(ams, "model_present", lambda *a, **k: True)
	seen: list[str] = []

	def fake_post(self, path, payload, **kw):
		seen.append(path)
		return {"response": "ok"}

	monkeypatch.setattr(AIModelService, "_ollama_post_json", fake_post)
	metrics.reset_for_tests()

	assert svc.warm_up() is True
	assert svc.is_loaded() is True
	assert svc.is_loading() is False
	assert svc.is_unavailable() is False
	assert svc.readiness_phase() == "ready"
	assert svc.time_to_ready_seconds() is not None
	# The readiness probe must be a REAL generation, not a bare /api/show.
	assert "/api/generate" in seen
	# D19 — time-to-ready was recorded.
	assert any("ai_model_time_to_ready_seconds" in name for name in metrics.snapshot())


def test_warm_up_failure_reports_unavailable_not_ready(monkeypatch):
	svc = _svc()
	monkeypatch.setattr(ams, "model_present", lambda *a, **k: True)

	def boom(self, path, payload, **kw):
		raise RuntimeError("Ollama HTTP 500: model failed to load")

	monkeypatch.setattr(AIModelService, "_ollama_post_json", boom)

	assert svc.warm_up() is False
	assert svc.is_loaded() is False
	assert svc.is_loading() is False
	assert svc.is_unavailable() is True
	assert svc.readiness_phase() == "failed"
	assert "model failed to load" in (svc.load_error() or "")


def test_is_loaded_is_false_while_loading_even_if_weights_exist(monkeypatch):
	# A model whose weights exist on disk but whose warm-up has not finished must NOT report ready —
	# the old /api/show-only check would have wrongly said ready here.
	svc = _svc()
	monkeypatch.setattr(AIModelService, "_ollama_model_available", lambda self: True)
	svc._set_readiness(READINESS_LOADING, "warming")
	assert svc.is_loaded() is False
	assert svc.is_loading() is True
	assert svc.is_unavailable() is False


def test_not_started_falls_back_to_live_probe(monkeypatch):
	# No warm-up kicked off (lazy/legacy path) → is_loaded()/is_unavailable() use the live /api/show probe.
	svc = _svc()
	assert svc._readiness_state() == READINESS_NOT_STARTED
	monkeypatch.setattr(AIModelService, "_ollama_model_available", lambda self: True)
	assert svc.is_loaded() is True


# ── D18 — warm-up pulls as a safety net and reports a "pulling" phase ─────────────────────────────


def test_warm_up_pulls_when_model_absent(monkeypatch):
	svc = _svc()
	monkeypatch.setattr(ams, "model_present", lambda *a, **k: False)
	pulled: list[str] = []
	phases: list[str] = []

	def fake_pull(base_url, model, **kw):
		# At pull time the worker must already be reporting the "pulling" phase (honest loading state).
		phases.append(svc.readiness_phase())
		pulled.append(model)
		return True

	monkeypatch.setattr(ams, "ensure_model_pulled", fake_pull)
	monkeypatch.setattr(
		AIModelService, "_ollama_post_json", lambda self, p, pl, **kw: {"response": "ok"}
	)

	assert svc.warm_up() is True
	assert pulled == ["test-model"]
	assert phases == ["pulling"]
	assert svc.is_loaded() is True


# ── D8 — background warm-up is non-blocking + idempotent ──────────────────────────────────────────


def test_start_background_warmup_is_idempotent_and_non_blocking(monkeypatch):
	svc = _svc()
	runs: list[int] = []

	def fake_warm(self):
		runs.append(1)
		return True

	monkeypatch.setattr(AIModelService, "warm_up", fake_warm)
	svc.start_background_warmup()
	# State flips to loading synchronously (before the thread runs), so the server reports loading at once.
	assert svc.is_loading() is True
	svc.start_background_warmup()  # second call must be a no-op

	deadline = time.monotonic() + 2.0
	while not runs and time.monotonic() < deadline:
		time.sleep(0.01)
	assert runs == [1]


# ── D6 — best-effort multi-model pull helper ──────────────────────────────────────────────────────


def test_ensure_model_pulled_skips_when_already_present(monkeypatch):
	monkeypatch.setattr(ollama_pull, "_post_json", lambda base, path, payload, timeout: 200)
	logs: list[str] = []
	assert ollama_pull.ensure_model_pulled("http://x", "m", log=logs.append) is True
	assert any("already present" in line for line in logs)


def test_ensure_model_pulled_pulls_when_absent(monkeypatch):
	status = {"/api/show": 404, "/api/pull": 200}
	monkeypatch.setattr(
		ollama_pull, "_post_json", lambda base, path, payload, timeout: status[path]
	)
	logs: list[str] = []
	assert ollama_pull.ensure_model_pulled("http://x", "m", log=logs.append) is True
	assert any("pulled successfully" in line for line in logs)


def test_ensure_model_pulled_never_raises_when_unreachable(monkeypatch):
	def boom(*a, **k):
		raise OSError("connection refused")

	monkeypatch.setattr(ollama_pull, "_post_json", boom)
	assert ollama_pull.ensure_model_pulled("http://x", "m", log=lambda *_: None) is False


def test_ensure_model_pulled_empty_model_is_noop():
	assert ollama_pull.ensure_model_pulled("http://x", "  ") is False


# ── D6 — pull_models script resolves chat + embed (+ helper) and de-duplicates ────────────────────


def _load_pull_models():
	path = Path(__file__).resolve().parent.parent / "scripts" / "pull_models.py"
	spec = importlib.util.spec_from_file_location("pull_models_under_test", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_pull_models_pulls_chat_and_embed_dedup_and_skips_unset_helper(monkeypatch):
	monkeypatch.setenv("OLLAMA_MODEL", "chat-model")
	monkeypatch.setenv("OLLAMA_MODEL_EMBED", "embed-model")
	monkeypatch.delenv("OLLAMA_MODEL_HELPER", raising=False)
	pm = _load_pull_models()
	pulled: list[str] = []
	monkeypatch.setattr(pm, "ensure_model_pulled", lambda base, model, **kw: pulled.append(model))

	assert pm.main() == 0
	# Chat + embed pulled; helper skipped because OLLAMA_MODEL_HELPER is unset.
	assert pulled == ["chat-model", "embed-model"]


def test_pull_models_includes_helper_and_dedups_shared_names(monkeypatch):
	monkeypatch.setenv("OLLAMA_MODEL", "shared")
	monkeypatch.setenv("OLLAMA_MODEL_EMBED", "shared")  # coincides with chat → pulled once
	monkeypatch.setenv("OLLAMA_MODEL_HELPER", "helper-model")
	pm = _load_pull_models()
	pulled: list[str] = []
	monkeypatch.setattr(pm, "ensure_model_pulled", lambda base, model, **kw: pulled.append(model))

	assert pm.main() == 0
	assert pulled == ["shared", "helper-model"]


# ── D8+D18+D19 — health payload surfaces phase + time-to-ready, tolerant of old AI doubles ────────


def test_health_payload_includes_phase_and_time_to_ready(monkeypatch):
	from handlers.rpc_handlers import RpcHandlers

	svc = _svc()
	monkeypatch.setattr(ams, "model_present", lambda *a, **k: True)
	monkeypatch.setattr(
		AIModelService, "_ollama_post_json", lambda self, p, pl, **kw: {"response": "ok"}
	)
	svc.warm_up()

	payload = RpcHandlers(lambda: svc, None, lambda *_: {})._model_status_payload()
	assert payload["ready"] is True
	assert payload["phase"] == "ready"
	assert isinstance(payload["timeToReadySeconds"], (int, float))


def test_health_payload_tolerates_old_ai_double_without_phase():
	from handlers.rpc_handlers import RpcHandlers

	class OldFake:
		model_name = "m"

		def is_loaded(self):
			return True

		def is_loading(self):
			return False

		def is_unavailable(self):
			return False

		def load_error(self):
			return None

	payload = RpcHandlers(lambda: OldFake(), None, lambda *_: {})._model_status_payload()
	assert payload["ready"] is True
	# An AI double without readiness_phase / time_to_ready_seconds must not break the payload.
	assert "phase" not in payload
	assert "timeToReadySeconds" not in payload
