"""Load shared moderation sanitize vectors from monorepo fixtures (AIH1-D7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

_CORPUS_REL = Path("docs") / "fixtures" / "moderation_sanitize_vectors.json"


class SanitizeVector(TypedDict, total=False):
	id: str
	title: str
	body: str
	mediaUrl: str | None
	notes: str
	expectStrippedOrdinals: bool
	expectControlCharsStripped: bool


def _corpus_candidates() -> list[Path]:
	"""Monorepo submodule layout (parents[2]) and standalone AI repo (parents[1])."""
	here = Path(__file__).resolve()
	return [
		here.parents[2] / _CORPUS_REL,
		here.parents[1] / _CORPUS_REL,
	]


def corpus_path() -> Path:
	for path in _corpus_candidates():
		if path.is_file():
			return path
	return _corpus_candidates()[0]


def load_moderation_sanitize_vectors() -> list[SanitizeVector]:
	data: dict[str, Any] = json.loads(corpus_path().read_text(encoding="utf-8"))
	vectors = data.get("vectors")
	if not isinstance(vectors, list):
		raise ValueError("moderation_sanitize_vectors.json: missing vectors array")
	return vectors
