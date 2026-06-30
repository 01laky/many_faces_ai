"""
Shared Ollama model-pull helper (Phase 2 / D6 + D18).

WHY THIS EXISTS
---------------
The worker talks to an Ollama instance that runs on the HOST (the dedicated AI PC),
not inside this container — over HTTP at OLLAMA_BASE_URL. A model that is not present
in that host store makes the worker stay unavailable indefinitely. Two callers need to
make a model present without ever crashing:

  * scripts/pull_models.py — the container entrypoint pulls the chat + embed (+ helper)
    models *before* the server starts (D6), so a warm host is a single cheap probe.
  * AIModelService.warm_up() — the background readiness warm-up pulls as a safety net if
    the model is still absent, so a cold/missed entrypoint pull surfaces as an honest
    `phase="pulling"` health state instead of a silent indefinite "unavailable" (D18).

Both share this module so the "/api/show then /api/pull" convention lives in one place.
The host Ollama store persists across container rebuilds, so a model pulled once stays
pulled and subsequent starts only pay the fast /api/show probe.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def _post_json(base_url: str, path: str, payload: dict, timeout: float) -> int:
	"""POST JSON to Ollama and return the HTTP status (an HTTPError's code, not an exception)."""
	body = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(
		f"{base_url.rstrip('/')}{path}",
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	try:
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			return resp.status
	except urllib.error.HTTPError as exc:
		return exc.code


def model_present(base_url: str, model: str, timeout: float = 10.0) -> bool:
	"""True when Ollama reports the model exists (HTTP 200 from /api/show)."""
	if not model.strip():
		return False
	return _post_json(base_url, "/api/show", {"name": model.strip()}, timeout) == 200


def pull_model(base_url: str, model: str, timeout: float = 600.0) -> bool:
	"""Pull the model (non-streaming). True on an HTTP 200 success."""
	if not model.strip():
		return False
	return (
		_post_json(base_url, "/api/pull", {"name": model.strip(), "stream": False}, timeout) == 200
	)


def ensure_model_pulled(
	base_url: str,
	model: str,
	*,
	show_timeout: float = 10.0,
	pull_timeout: float = 600.0,
	log=print,
) -> bool:
	"""
	Make `model` present in the host Ollama store, best-effort. Returns True when the model
	is present afterwards (already there or freshly pulled), False otherwise. Never raises —
	a missing model or an unreachable Ollama is reported via the return value + a log line so
	callers (entrypoint script, background warm-up) can degrade gracefully.
	"""
	model = model.strip()
	if not model:
		return False
	try:
		if model_present(base_url, model, show_timeout):
			log(f"model '{model}' already present — skipping pull")
			return True
		log(f"model '{model}' absent — pulling (this can take minutes on a cold host)...")
		if pull_model(base_url, model, pull_timeout):
			log(f"model '{model}' pulled successfully")
			return True
		log(f"warning: model '{model}' pull did not succeed")
		return False
	except Exception as exc:  # noqa: BLE001 - best-effort: never fail the caller
		log(f"warning: model '{model}' pull skipped ({type(exc).__name__}: {exc})")
		return False
