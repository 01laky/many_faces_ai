#!/usr/bin/env python3
"""
pull_helper_model.py - 7B-perf O19 helper-model warm-up (best-effort).

WHY THIS EXISTS
---------------
The operator AI uses a small "helper" model (OLLAMA_MODEL_HELPER) for cheap
routing/gating decisions so the big 7B chat model is reserved for the
operator-visible synthesis. That helper model must exist in the Ollama model
store before the first request, otherwise the first routing call pays a
multi-second on-demand pull.

WHY IT IS SAFE TO RUN ON EVERY STARTUP
--------------------------------------
The Ollama model store lives on the HOST (the dedicated AI PC), NOT inside this
container — we talk to it over HTTP at OLLAMA_BASE_URL (default the docker host).
Because the store persists across container rebuilds/restarts, a model pulled
once stays pulled. So this script first asks Ollama whether the model is already
present (`/api/show`) and only issues a `/api/pull` when it is genuinely absent.
On a warm host this is a single cheap HTTP probe and no download.

BEST-EFFORT CONTRACT
--------------------
This runs from the container entrypoint *before* the worker starts. It must NEVER
fail the container: if the helper model is not configured, or Ollama is briefly
unreachable, or any other error occurs, we print a warning and exit 0. The worker
itself degrades gracefully when a model is missing.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Matches utils.env.DEFAULT_OLLAMA_BASE_URL — duplicated here so the script can run
# standalone in the entrypoint without importing the worker package.
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"


def _base_url() -> str:
	return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def _post_json(path: str, payload: dict, timeout: float) -> tuple[int, dict | None]:
	"""
	POST a JSON body to Ollama and return (http_status, parsed_body_or_None).

	A urllib HTTPError (e.g. 404 when the model is absent) is caught and surfaced
	as its status code so the caller can branch on "absent" vs "present" without
	the exception aborting the best-effort flow.
	"""
	body = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(
		f"{_base_url()}{path}",
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	try:
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			raw = resp.read().decode("utf-8", errors="replace")
			try:
				return resp.status, json.loads(raw)
			except json.JSONDecodeError:
				return resp.status, None
	except urllib.error.HTTPError as exc:
		return exc.code, None


def _model_present(model: str, timeout: float) -> bool:
	"""True when Ollama reports the model exists (HTTP 200 from /api/show)."""
	status, _ = _post_json("/api/show", {"name": model}, timeout)
	return status == 200


def _pull_model(model: str, timeout: float) -> bool:
	"""Pull the model (non-streaming). True on an HTTP 200 success."""
	status, _ = _post_json("/api/pull", {"name": model, "stream": False}, timeout)
	return status == 200


def main() -> int:
	model = os.getenv("OLLAMA_MODEL_HELPER", "").strip()
	if not model:
		# Helper model disabled — nothing to do. This is the common path on
		# deployments that have not opted into the small helper model.
		return 0

	# A pull can take a while on a cold host; an /api/show probe is fast.
	show_timeout = float(os.getenv("OLLAMA_HELPER_SHOW_TIMEOUT", "10"))
	pull_timeout = float(os.getenv("OLLAMA_HELPER_PULL_TIMEOUT", "600"))

	try:
		if _model_present(model, show_timeout):
			print(f"helper model '{model}' already present — skipping pull")
			return 0
		print(f"helper model '{model}' absent — pulling...")
		if _pull_model(model, pull_timeout):
			print(f"helper model '{model}' pulled successfully")
		else:
			print(f"warning: helper model '{model}' pull did not succeed (continuing)")
	except Exception as exc:  # noqa: BLE001 - best-effort: never fail the container
		print(f"warning: helper model warm-up skipped ({type(exc).__name__}: {exc})")
	# Always succeed: the worker must start regardless of helper-model state.
	return 0


if __name__ == "__main__":
	sys.exit(main())
