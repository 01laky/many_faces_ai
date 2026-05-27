"""Search worker gRPC client stub (AI-UP5) — no direct Elasticsearch HTTP."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def search_worker_configured() -> bool:
	return bool(os.getenv("SEARCH_WORKER_GRPC_ADDRESS", "").strip())


def format_search_hits_for_prompt(search_hits_json: str) -> str:
	raw = (search_hits_json or "").strip()
	if not raw:
		return ""
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		logger.info("Invalid search_hits_json ignored")
		return ""
	items = (
		data if isinstance(data, list) else data.get("items") if isinstance(data, dict) else None
	)
	if not isinstance(items, list):
		return ""
	lines = ["# Search hits (cite only these ids)", ""]
	for item in items[:10]:
		if isinstance(item, dict):
			lines.append(f"- id={item.get('id')} title={item.get('title', '')}")
	return "\n".join(lines) + "\n\n"


def query_search_worker(_query: str, _face_index: str) -> list[dict[str, Any]]:
	"""Placeholder until many_faces_elastic proto client is wired."""
	if not search_worker_configured():
		return []
	logger.debug("search worker query skipped — client not implemented in v0.9.0 stub")
	return []
