"""Ollama embeddings helper (AI-UP15)."""

from __future__ import annotations

import json
import logging
import os
from urllib import error, request

from utils.env import env_int, ollama_base_url
from utils.model_routing import PROFILE_EMBED, resolve_model

logger = logging.getLogger(__name__)


def embed_texts(
	texts: list[str], model: str | None = None
) -> tuple[list[list[float]], str, str | None]:
	batch_max = env_int("OLLAMA_EMBED_MAX_BATCH", 8)
	char_max = env_int("OLLAMA_EMBED_MAX_CHARS", 8000)
	clean = [(t or "").strip()[:char_max] for t in texts if (t or "").strip()]
	if not clean:
		return [], "", "texts required"
	if len(clean) > batch_max:
		return [], "", f"batch exceeds {batch_max}"

	model_name = resolve_model(PROFILE_EMBED, model)
	vectors: list[list[float]] = []
	for text in clean:
		vec, err = _embed_one(text, model_name)
		if err:
			return [], model_name, err
		vectors.append(vec)
	return vectors, model_name, None


def _embed_one(text: str, model_name: str) -> tuple[list[float], str | None]:
	url = f"{ollama_base_url()}/api/embeddings"
	# 7B-perf O1: keep the embedding model resident on the dedicated PC so repeated
	# RAG indexing/query batches do not pay a cold-load each time. Default "-1"
	# (never evict); overridable via OLLAMA_KEEP_ALIVE to match the chat model.
	payload = json.dumps(
		{
			"model": model_name,
			"prompt": text,
			"keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "-1"),
		}
	).encode("utf-8")
	req = request.Request(
		url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
	)
	timeout = env_int("OLLAMA_TIMEOUT_SECONDS", 120)
	try:
		with request.urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode("utf-8"))
	except error.URLError as exc:
		logger.info("embed request failed: %s", type(exc).__name__)
		return [], "embeddings unavailable"
	if not isinstance(data, dict):
		return [], "invalid embed response"
	embedding = data.get("embedding")
	if not isinstance(embedding, list):
		return [], "missing embedding vector"
	return [float(x) for x in embedding], None
