"""Chat message risk scoring (AI-UP4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.content_review_classifier import classify_text_signals

MODEL_VERSION = "chat-risk-v1"
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)
PI_PATTERNS = (
	"ignore previous instructions",
	"system prompt",
	"you are now",
	"disregard all",
)


@dataclass
class ChatRiskResult:
	risk_score: float
	action: str
	flags: list[str]
	safe_user_hint: str
	model_version: str


def score_chat_message(message_text: str, channel_type: str) -> ChatRiskResult:
	text = (message_text or "").strip()
	flags: list[str] = list(classify_text_signals(text.lower()))
	lower = text.lower()

	if URL_PATTERN.search(text):
		flags.append("external_link")
	for pat in PI_PATTERNS:
		if pat in lower:
			flags.append("pi_pattern")
			break
	if channel_type not in ("dm", "chat_room", ""):
		flags.append("unknown_channel")

	flags = sorted(set(flags))
	score = _score_from_flags(flags)

	if any(f in flags for f in ("hate", "violence", "self_harm", "scam", "phishing")):
		action = "block"
		hint = "Message blocked by safety policy."
	elif score >= 0.55 or "external_link" in flags or "pi_pattern" in flags or "spam" in flags:
		action = "flag"
		hint = "Message flagged for review."
	else:
		action = "allow"
		hint = ""

	return ChatRiskResult(
		risk_score=score,
		action=action,
		flags=flags,
		safe_user_hint=hint,
		model_version=MODEL_VERSION,
	)


def _score_from_flags(flags: list[str]) -> float:
	if not flags:
		return 0.05
	weights = {
		"spam": 0.35,
		"harassment": 0.5,
		"external_link": 0.45,
		"pi_pattern": 0.6,
		"low_quality": 0.2,
	}
	return min(1.0, max(weights.get(f, 0.25) for f in flags))
