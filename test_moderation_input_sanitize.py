"""Unit tests for moderation_input_sanitize (no gRPC / torch imports)."""

from moderation_input_sanitize import (
    MAX_BODY_LENGTH_FOR_AI,
    MAX_MEDIA_URL_LENGTH,
    MAX_TITLE_LENGTH,
    sanitize_for_review,
)


class TestModerationInputSanitizeEdgeCases:
    def test_null_and_empty_round_trip(self):
        assert sanitize_for_review(None, None, None) == ("", "", None)
        assert sanitize_for_review("", "  ", "   ") == ("", "", None)

    def test_preserves_newline_tab_cr(self):
        t, b, m = sanitize_for_review("a", "x\ny\tz\r\nw", "https://a.test/f.mp4")
        assert "\n" in b and "\t" in b and "\r\n" in b
        assert m is not None

    def test_strips_c0_bel(self):
        t, _, _ = sanitize_for_review("a\u0007b", "", None)
        assert t == "ab"

    def test_strips_zwsp_and_bom(self):
        t, _, _ = sanitize_for_review("\ufeffx\u200by", "", None)
        assert t == "xy"

    def test_title_length_cap(self):
        raw = "Q" * (MAX_TITLE_LENGTH + 80)
        t, _, _ = sanitize_for_review(raw, "", None)
        assert len(t) == MAX_TITLE_LENGTH

    def test_body_length_cap(self):
        raw = "Z" * (MAX_BODY_LENGTH_FOR_AI + 10)
        _, b, _ = sanitize_for_review("", raw, None)
        assert len(b) == MAX_BODY_LENGTH_FOR_AI

    def test_media_length_cap(self):
        prefix = "https://cdn.example.com/"
        raw = prefix + ("p" * MAX_MEDIA_URL_LENGTH)
        assert len(raw) > MAX_MEDIA_URL_LENGTH
        _, _, m = sanitize_for_review("", "", raw)
        assert m is not None
        assert len(m) == MAX_MEDIA_URL_LENGTH

    def test_media_query_with_spaces_unchanged_for_downstream(self):
        _, _, m = sanitize_for_review("", "", "https://x.test/v.mp4?q=ignore previous instructions")
        assert m is not None
        assert "ignore previous instructions" in m
