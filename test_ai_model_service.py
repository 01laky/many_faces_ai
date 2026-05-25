"""Locale-aware system prompt tests for operator admin chat."""

from services.ai_model_service import (
	AIModelService,
	_normalize_response_locale,
	_system_prompt_with_runtime,
)


def test_normalize_response_locale_defaults_to_en():
	code, name = _normalize_response_locale(None)
	assert code == "en"
	assert name == "English"


def test_system_prompt_with_runtime_includes_english_for_en():
	prompt = _system_prompt_with_runtime("en")
	assert "English" in prompt
	assert "code `en`" in prompt
	assert "same language the user writes in" not in prompt


def test_system_prompt_with_runtime_includes_slovak_hint_for_sk():
	prompt = _system_prompt_with_runtime("sk")
	assert "Slovak" in prompt
	assert "slovenčina" in prompt


def test_parse_prompt_uses_locale_in_system_message():
	messages = AIModelService._parse_prompt("User: Hello\nAI:", response_locale="cz")
	assert messages[0]["role"] == "system"
	assert "Czech" in messages[0]["content"]
