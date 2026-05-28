"""AI-UP17 / AIH1-D7 — shared moderation sanitize corpus parity."""

from __future__ import annotations

import pytest

from moderation_input_sanitize import sanitize_for_review
from tests.moderation_sanitize_vectors_loader import corpus_path, load_moderation_sanitize_vectors


@pytest.fixture(scope="module")
def corpus_vectors():
	if not corpus_path().is_file():
		pytest.skip(f"corpus missing: {corpus_path()}")
	return load_moderation_sanitize_vectors()


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
