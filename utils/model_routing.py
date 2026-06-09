"""Ollama model profile routing (AI-UP7)."""

from __future__ import annotations

from utils.env import env_str

DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"

PROFILE_CHAT = "chat"
PROFILE_MODERATION = "moderation"
PROFILE_RISK = "risk"
PROFILE_VISION = "vision"
PROFILE_EMBED = "embed"
# 7B-perf O19: small CPU-resident helper model for cheap routing/gating decisions
# (the backend routes those calls here via the per-call model override) so the big
# 7B chat model is reserved for operator-visible synthesis.
PROFILE_HELPER = "helper"

_PROFILE_ENV = {
	PROFILE_CHAT: "OLLAMA_MODEL_CHAT",
	PROFILE_MODERATION: "OLLAMA_MODEL_MODERATION",
	PROFILE_RISK: "OLLAMA_MODEL_RISK",
	PROFILE_VISION: "OLLAMA_MODEL_VISION",
	PROFILE_EMBED: "OLLAMA_MODEL_EMBED",
	PROFILE_HELPER: "OLLAMA_MODEL_HELPER",
}


def resolve_model(profile: str, explicit: str | None = None) -> str:
	if explicit and explicit.strip():
		return explicit.strip()
	env_key = _PROFILE_ENV.get(profile)
	if env_key:
		val = env_str(env_key, "")
		if val:
			return val
	fallback = env_str("OLLAMA_MODEL", "")
	return fallback or DEFAULT_MODEL


def active_models_summary() -> dict[str, str]:
	return {profile: resolve_model(profile) for profile in _PROFILE_ENV}
