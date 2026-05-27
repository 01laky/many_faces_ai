"""ReviewContent orchestration — rules, media pass, optional LLM (AI-UP1, UP8, UP16)."""

from __future__ import annotations

import os
from collections.abc import Callable

from services.content_review_classifier import (
	BOUNDARY_FLAGS,
	HIGH_RISK_FLAGS,
	ContentReviewResult,
	normalize_review_result,
	review_content,
)
from services.llm_content_review_classifier import llm_moderation_enabled, review_with_llm
from services.media_url_pass import media_url_flags

RULES_AUTO_THRESHOLD = float(os.getenv("MODERATION_RULES_AUTO_THRESHOLD", "0.88"))


class FullReviewResult(ContentReviewResult, total=False):
	decision_path: str
	auto_approve_eligible: bool
	policy_hint: str


def review_content_full(
	title: str,
	body: str,
	media_url: str | None,
	content_type: str,
	*,
	llm_generate: Callable[[str, int], str] | None = None,
) -> FullReviewResult:
	media_flags = media_url_flags(media_url)
	base = review_content(title, body, media_url, content_type)
	flags = sorted({*base["flags"], *media_flags})
	result: ContentReviewResult = normalize_review_result({**base, "flags": flags})

	decision_path = "rules"
	if _should_invoke_llm(result) and llm_generate is not None:
		llm_result = review_with_llm(
			title,
			body,
			media_url,
			content_type,
			flags,
			generate_fn=lambda p, max_new_tokens=256: llm_generate(p, max_new_tokens),
		)
		if llm_result is not None:
			result = llm_result
			decision_path = "llm"

	auto_eligible, policy_hint = _auto_approve_fields(result, flags)
	out: FullReviewResult = dict(result)
	out["decision_path"] = decision_path
	out["auto_approve_eligible"] = auto_eligible
	out["policy_hint"] = policy_hint
	return out


def _should_invoke_llm(base: ContentReviewResult) -> bool:
	if not llm_moderation_enabled():
		return False
	if base["decision"] == "reject" and base["confidence"] >= RULES_AUTO_THRESHOLD:
		return False
	if base["decision"] == "needs_human_review":
		return True
	boundary_only = all(f in BOUNDARY_FLAGS for f in base["flags"]) if base["flags"] else False
	return boundary_only


def _auto_approve_fields(result: ContentReviewResult, flags: list[str]) -> tuple[bool, str]:
	if result["decision"] != "approve":
		return False, ""
	if any(f in HIGH_RISK_FLAGS for f in flags):
		return False, ""
	if any(f in BOUNDARY_FLAGS for f in flags):
		return False, "boundary_media_pending"
	min_conf = float(os.getenv("AUTO_APPROVE_MIN_CONFIDENCE", "0.95"))
	if result["confidence"] < min_conf:
		return False, "confidence_below_threshold"
	return True, "rules_high_confidence"
