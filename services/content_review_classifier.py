"""Deterministic content moderation classifiers for ReviewContent RPC."""

from __future__ import annotations

import re
import uuid
from typing import TypedDict

TEXT_POLICY_TERMS = {
	"spam": {"spam", "giveaway", "free money", "cheap followers"},
	"scam": {"scam", "crypto doubling", "wire transfer", "investment guaranteed"},
	"phishing": {"phishing", "password reset link", "verify your account", "login now"},
	"hate": {"hate", "slur", "racist"},
	"harassment": {"harass", "bully", "doxx"},
	"adult": {"adult", "porn", "nsfw", "sexual"},
	"violence": {"violence", "kill", "weapon", "blood"},
	"self_harm": {"self harm", "suicide", "hurt myself"},
	"copyright": {"pirated", "leaked movie", "copyright bypass"},
}

SUPPORTED_MEDIA_EXTENSIONS = {
	".jpg",
	".jpeg",
	".png",
	".webp",
	".gif",
	".mp4",
	".webm",
	".mov",
}

MODEL_VERSION = "qwen-advisory-classifier-v2"
BOUNDARY_FLAGS = frozenset({"image_analysis_boundary", "video_analysis_boundary"})
HIGH_RISK_FLAGS = frozenset({"hate", "adult", "violence", "self_harm", "unsafe_link"})
VALID_DECISIONS = frozenset({"approve", "reject", "needs_human_review"})
VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})


class ContentReviewResult(TypedDict):
	decision: str
	confidence: float
	risk_level: str
	flags: list[str]
	reason: str
	user_message: str
	model_version: str
	trace_id: str


def contains_term(text: str, term: str) -> bool:
	return bool(re.search(rf"(^|[^a-z0-9]){re.escape(term)}([^a-z0-9]|$)", text))


def classify_text_signals(text: str) -> list[str]:
	flags: list[str] = []
	for flag, terms in TEXT_POLICY_TERMS.items():
		if any(contains_term(text, term) for term in terms):
			flags.append(flag)
	if len(text.strip()) < 12:
		flags.append("low_quality")
	return sorted(set(flags))


def classify_media_signals(media_url: str) -> list[str]:
	if not media_url:
		return []
	flags: list[str] = []
	lowered = media_url.lower()
	if not (lowered.startswith("http://") or lowered.startswith("https://")):
		flags.append("unsafe_link")
	path = lowered.split("?", 1)[0].split("#", 1)[0]
	if "." not in path or not any(path.endswith(ext) for ext in SUPPORTED_MEDIA_EXTENSIONS):
		flags.append("unsupported_media")
	return sorted(set(flags))


def normalize_review_result(result: ContentReviewResult) -> ContentReviewResult:
	"""Defensive bounds on classifier output (AIH1-D5)."""
	decision = result["decision"]
	if decision not in VALID_DECISIONS:
		decision = "needs_human_review"
	try:
		confidence = float(result["confidence"])
	except (TypeError, ValueError):
		confidence = 0.5
	confidence = max(0.0, min(1.0, confidence))
	risk = result["risk_level"]
	if risk not in VALID_RISK_LEVELS:
		risk = "medium"
	flags = [f for f in result["flags"] if isinstance(f, str) and f.strip()]
	return ContentReviewResult(
		decision=decision,
		confidence=confidence,
		risk_level=risk,
		flags=sorted(set(flags)),
		reason=str(result["reason"])[:2000],
		user_message=str(result["user_message"])[:500],
		model_version=str(result["model_version"])[:64] or MODEL_VERSION,
		trace_id=str(result["trace_id"])[:128],
	)


def review_content(
	title: str,
	body: str,
	media_url: str | None,
	content_type: str,
) -> ContentReviewResult:
	text = f"{title} {body}".lower()
	flags = [*classify_text_signals(text), *classify_media_signals(media_url or "")]
	if content_type == "Album":
		flags.append("image_analysis_boundary")
	elif content_type == "Reel":
		flags.append("video_analysis_boundary")
	flags = sorted(set(flags))

	policy_flags = [f for f in flags if f not in BOUNDARY_FLAGS]
	risk_level = "low"
	decision = "approve"
	confidence = 0.86
	reason = "No obvious policy, media, or quality issue was detected by the classifier fallback."
	user_message = "Your content is waiting for final review."

	if policy_flags:
		risk_level = "high" if any(flag in HIGH_RISK_FLAGS for flag in policy_flags) else "medium"
		decision = "reject" if risk_level == "high" else "needs_human_review"
		confidence = 0.88 if risk_level == "high" else 0.72
		reason = f"Potential moderation flags detected: {', '.join(sorted(set(policy_flags)))}."
		user_message = "Your content needs changes before it can be published."

	return ContentReviewResult(
		decision=decision,
		confidence=confidence,
		risk_level=risk_level,
		flags=flags,
		reason=reason,
		user_message=user_message,
		model_version=MODEL_VERSION,
		trace_id=f"ai-review-{uuid.uuid4().hex}",
	)


def review_content_normalized(
	title: str,
	body: str,
	media_url: str | None,
	content_type: str,
) -> ContentReviewResult:
	return normalize_review_result(review_content(title, body, media_url, content_type))
