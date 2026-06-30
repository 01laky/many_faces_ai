#!/usr/bin/env python3
"""
pull_models.py - Phase 2 / D6 startup model warm-up (best-effort).

WHY THIS EXISTS
---------------
The operator AI needs THREE models present in the host Ollama store before it can serve:
the main chat model (the 7B that writes operator-visible answers), the embedding model
(the skill router's retrieval plane), and the small CPU helper model (cheap routing/gating).
Previously only the helper model was pulled at startup (scripts/pull_helper_model.py), so on
a fresh AI host the chat + embed models were missing and the worker stayed unavailable
indefinitely until someone ran `ollama pull` by hand.

This script pulls all configured models (chat, embed, helper) at container start, before the
worker process begins, resolving each model name from the same OLLAMA_MODEL_* env the worker
uses (utils.model_routing). Models are de-duplicated so a shared name is pulled once.

WHY IT IS SAFE TO RUN ON EVERY STARTUP
--------------------------------------
The Ollama store lives on the HOST and persists across container rebuilds, so a model pulled
once stays pulled. Each entry first probes /api/show and only /api/pull's when genuinely
absent — a warm host is a few cheap HTTP probes and no download.

BEST-EFFORT CONTRACT
--------------------
Runs from the entrypoint *before* the worker starts and must NEVER fail the container: any
unreachable Ollama / missing model / error prints a warning and the script still exits 0. The
worker's own background warm-up (AIModelService.warm_up) is the safety net — it re-pulls a
still-absent model and reports an honest `loading`/`pulling` health state — so a missed pull
here degrades to "AI starting up", never a crash.
"""

from __future__ import annotations

import os
import sys

# Allow running standalone from the entrypoint: add the app root so `utils`/`services` import.
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
	sys.path.insert(0, _APP_DIR)

from services.ollama_pull import ensure_model_pulled  # noqa: E402
from utils.model_routing import (  # noqa: E402
	PROFILE_CHAT,
	PROFILE_EMBED,
	PROFILE_HELPER,
	resolve_model,
)


def _base_url() -> str:
	# Matches utils.env.DEFAULT_OLLAMA_BASE_URL — resolved here without importing the worker package.
	return os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")


def main() -> int:
	base_url = _base_url()
	show_timeout = float(os.getenv("OLLAMA_PULL_SHOW_TIMEOUT", "10"))
	pull_timeout = float(os.getenv("OLLAMA_PULL_TIMEOUT", "600"))

	# Resolve the model name behind each profile (chat falls back to OLLAMA_MODEL; helper is
	# only pulled when explicitly configured so deployments that opt out pull nothing extra).
	wanted: list[str] = [resolve_model(PROFILE_CHAT), resolve_model(PROFILE_EMBED)]
	if os.getenv("OLLAMA_MODEL_HELPER", "").strip():
		wanted.append(resolve_model(PROFILE_HELPER))

	# De-duplicate while preserving order (chat + embed may coincide on some single-model setups).
	seen: set[str] = set()
	models = [m for m in wanted if m.strip() and not (m in seen or seen.add(m))]

	print(
		f"pull_models: ensuring {len(models)} model(s) present at {base_url}: {', '.join(models)}"
	)
	for model in models:
		ensure_model_pulled(
			base_url,
			model,
			show_timeout=show_timeout,
			pull_timeout=pull_timeout,
		)
	# Always succeed: the worker must start regardless of model-store state.
	return 0


if __name__ == "__main__":
	sys.exit(main())
