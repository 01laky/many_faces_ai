"""AIH1-T-D10/D11 — shared monorepo sanitize corpus parity."""

from __future__ import annotations

from moderation_input_sanitize import (
    MAX_BODY_LENGTH_FOR_AI,
    MAX_MEDIA_URL_LENGTH,
    MAX_TITLE_LENGTH,
    sanitize_for_review,
)
from tests.moderation_sanitize_vectors_loader import corpus_path, load_moderation_sanitize_vectors


def test_aih1_t_d11_corpus_file_exists():
    assert corpus_path().is_file()


def test_aih1_t_d10_d11_each_corpus_vector_sanitized_within_caps():
    for row in load_moderation_sanitize_vectors():
        vid = row.get("id", "?")
        title = row.get("title", "")
        body = row.get("body", "")
        media = row.get("mediaUrl")
        t, b, m = sanitize_for_review(title, body, media)
        assert len(t) <= MAX_TITLE_LENGTH, vid
        assert len(b) <= MAX_BODY_LENGTH_FOR_AI, vid
        if m is not None:
            assert len(m) <= MAX_MEDIA_URL_LENGTH, vid
        if row.get("expectStrippedOrdinals"):
            combined = t + b + (m or "")
            for ch in ("\u200b", "\u202e", "\u202a"):
                assert ch not in combined, vid
        if row.get("expectControlCharsStripped"):
            assert "\x00" not in (t + b), vid
