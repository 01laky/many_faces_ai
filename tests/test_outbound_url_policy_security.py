"""AIH1-T-B* — outbound URL policy and fetch limits."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from utils.env import DEFAULT_OLLAMA_BASE_URL, ollama_base_url, validate_ollama_base_url_hardened
from utils.http_json import DEFAULT_MAX_RESPONSE_BYTES, fetch_public_stats_body
from utils.outbound_url_policy import validate_public_fetch_url
from utils.validate_worker_env import WorkerEnvValidationError, validate_worker_env


def test_aih1_t_b01_https_public_url_allowed():
    ok, reason = validate_public_fetch_url("https://example.com/stats.json")
    assert ok is True
    assert reason == ""


def test_aih1_t_b02_loopback_http_allowed_in_dev():
    ok, reason = validate_public_fetch_url("http://127.0.0.1:8080/stats")
    assert ok is True
    assert reason == ""


def test_aih1_t_b03_metadata_ip_rejected():
    ok, reason = validate_public_fetch_url("http://169.254.169.254/latest/meta-data/")
    assert ok is False
    assert reason


def test_aih1_t_b04_private_ipv4_https_rejected():
    ok, reason = validate_public_fetch_url("https://10.0.0.5/internal")
    assert ok is False
    assert reason == "private_or_local_host"


def test_aih1_t_b05_javascript_scheme_rejected():
    ok, reason = validate_public_fetch_url("javascript:alert(1)")
    assert ok is False
    assert reason == "invalid_scheme"


def test_aih1_t_b06_file_scheme_rejected():
    ok, reason = validate_public_fetch_url("file:///etc/passwd")
    assert ok is False
    assert reason == "invalid_scheme"


@patch("utils.http_json.urllib.request.build_opener")
def test_aih1_t_b07_response_over_max_bytes(mock_build_opener):
    mock_opener = MagicMock()
    response = MagicMock()
    response.read.return_value = b"x" * (DEFAULT_MAX_RESPONSE_BYTES + 1)
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    mock_opener.open.return_value = response
    mock_build_opener.return_value = mock_opener

    body, error = fetch_public_stats_body(
        "http://127.0.0.1/stats",
        allow_insecure_tls_for_host=lambda _h: True,
    )
    assert body == ""
    assert error == "response too large"


@patch("utils.http_json.urllib.request.build_opener")
def test_aih1_t_b08_redirect_to_private_not_followed(mock_build_opener):
    import urllib.error

    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.HTTPError(
        url="https://example.com/stats",
        code=302,
        msg="Found",
        hdrs=None,
        fp=None,
    )
    mock_build_opener.return_value = mock_opener

    body, error = fetch_public_stats_body(
        "https://example.com/stats",
        allow_insecure_tls_for_host=lambda _h: False,
    )
    assert body == ""
    assert error


def test_aih1_t_b09_disallowed_ollama_host_in_hardened_validate():
    with patch.dict(
        os.environ,
        {"OLLAMA_BASE_URL": "http://evil.example.com:11434"},
        clear=False,
    ):
        ok, reason = validate_ollama_base_url_hardened()
        assert ok is False
        assert "allow-list" in reason


def test_aih1_t_e01_hardened_insecure_grpc_without_flag():
    env = {
        "MFAI_REQUIRE_WORKER_AUTH": "1",
        "AI_WORKER_EXPECTED_TOKEN": "tok",
        "GRPC_TLS_CERT_FILE": "",
        "GRPC_TLS_KEY_FILE": "",
        "MFAI_ALLOW_INSECURE_GRPC": "",
        "OLLAMA_BASE_URL": DEFAULT_OLLAMA_BASE_URL,
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(WorkerEnvValidationError, match="MFAI_ALLOW_INSECURE_GRPC"):
            validate_worker_env()


def test_aih1_t_e03_default_ollama_base_url():
    with patch.dict(os.environ, {}, clear=True):
        assert "11434" in ollama_base_url()
