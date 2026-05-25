"""AI-RA6…RA12 — ReviewContent classifier extraction."""

from services.content_review_classifier import (
	MODEL_VERSION,
	classify_media_signals,
	classify_text_signals,
	contains_term,
	review_content,
)


def test_ai_ra6_contains_term_requires_word_boundary():
	assert contains_term("this is spam content", "spam")
	assert not contains_term("escamoter", "scam")


def test_ai_ra7_classify_text_detects_policy_and_low_quality():
	flags = classify_text_signals("buy cheap followers now spam")
	assert "spam" in flags
	assert classify_text_signals("short") == ["low_quality"]


def test_ai_ra8_classify_media_flags_unsafe_and_unsupported():
	assert "unsafe_link" in classify_media_signals("ftp://bad.example/x.jpg")
	assert "unsupported_media" in classify_media_signals("https://cdn.example/noext")


def test_ai_ra9_review_content_approves_safe_blog():
	result = review_content(
		"Community update",
		"A normal update for the community.",
		None,
		"Blog",
	)
	assert result["decision"] == "approve"
	assert result["risk_level"] == "low"
	assert result["confidence"] == 0.86
	assert result["model_version"] == MODEL_VERSION
	assert result["trace_id"].startswith("ai-review-")


def test_ai_ra10_review_content_rejects_high_risk_reel():
	result = review_content(
		"Bad clip",
		"This contains hate speech and violence.",
		"https://cdn.example/clip.mp4",
		"Reel",
	)
	assert result["decision"] == "reject"
	assert result["risk_level"] == "high"
	assert result["confidence"] == 0.88
	assert "video_analysis_boundary" in result["flags"]


def test_ai_ra11_boundary_flags_do_not_alone_force_review():
	result = review_content("Title", "Enough body text here.", None, "Album")
	assert result["decision"] == "approve"
	assert "image_analysis_boundary" in result["flags"]


def test_ai_ra12_medium_risk_needs_human_review():
	result = review_content(
		"Promo",
		"Join our giveaway and free money scheme today for everyone.",
		None,
		"Blog",
	)
	assert result["decision"] == "needs_human_review"
	assert result["risk_level"] == "medium"
	assert result["confidence"] == 0.72
