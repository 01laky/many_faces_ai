"""AI-RA1…RA5 — shared env parsing."""

from __future__ import annotations

import pytest

from utils.env import DEFAULT_OLLAMA_BASE_URL, env_float, env_int, env_int_optional, ollama_base_url


def test_ai_ra1_env_int_uses_default_when_unset(monkeypatch):
	monkeypatch.delenv("TEST_INT", raising=False)
	assert env_int("TEST_INT", 42) == 42


def test_ai_ra2_env_int_parses_valid_value(monkeypatch):
	monkeypatch.setenv("TEST_INT", "7")
	assert env_int("TEST_INT", 42) == 7


def test_ai_ra3_env_int_falls_back_on_invalid(monkeypatch):
	monkeypatch.setenv("TEST_INT", "not-a-number")
	assert env_int("TEST_INT", 42) == 42


def test_ai_ra4_env_int_optional_returns_none_when_empty(monkeypatch):
	monkeypatch.setenv("TEST_OPT", "")
	assert env_int_optional("TEST_OPT") is None


@pytest.mark.parametrize(
	("raw", "expected"),
	[
		(None, DEFAULT_OLLAMA_BASE_URL),
		("http://ollama:11434/", "http://ollama:11434"),
	],
)
def test_ai_ra5_ollama_base_url_strips_trailing_slash(monkeypatch, raw, expected):
	if raw is None:
		monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
	else:
		monkeypatch.setenv("OLLAMA_BASE_URL", raw)
	assert ollama_base_url() == expected


def test_env_float_parses_and_falls_back(monkeypatch):
	monkeypatch.setenv("TEST_FLOAT", "0.5")
	assert env_float("TEST_FLOAT", 0.1) == pytest.approx(0.5)
	monkeypatch.setenv("TEST_FLOAT", "bad")
	assert env_float("TEST_FLOAT", 0.1) == pytest.approx(0.1)
