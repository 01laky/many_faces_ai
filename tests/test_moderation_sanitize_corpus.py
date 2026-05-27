"""AI-UP17 / AIH1-D7 — shared moderation sanitize corpus parity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moderation_input_sanitize import sanitize_for_review

_CORPUS = (
	Path(__file__).resolve().parents[2] / "docs" / "fixtures" / "moderation_sanitize_vectors.json"
)


@pytest.fixture(scope="module")
def corpus_vectors():
	if not _CORPUS.is_file():
		pytest.skip(f"corpus missing: {_CORPUS}")
	data = json.loads(_CORPUS.read_text(encoding="utf-8"))
	return data["vectors"]


def test_ai_up17_u1_corpus_vectors_sanitize(corpus_vectors):
	for vector in corpus_vectors:
		title, body, media = sanitize_for_review(
			vector.get("title") or "",
			vector.get("body") or "",
			vector.get("mediaUrl"),
		)
		assert isinstance(title, str)
		assert isinstance(body, str)
		if vector.get("expectStrippedOrdinals"):
			assert "\u200b" not in title
		if vector.get("expectControlCharsStripped"):
			assert "\x00" not in body
