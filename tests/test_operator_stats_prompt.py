"""AI-RA13…RA16 — operator stats prompt wire contract."""

from services.operator_stats_prompt import (
    allow_insecure_tls_for_host,
    compose_operator_chat_prompt,
    stats_context_prefix,
)


def test_ai_ra13_stats_context_prefix_includes_separator():
    prefix = stats_context_prefix('{"dashboard":{"usersCount":7}}')
    assert prefix.startswith("[Operator platform statistics JSON")
    assert '"usersCount":7' in prefix
    assert prefix.endswith("\n\n---\n\n")


def test_ai_ra14_compose_prompt_appends_latest_user_turn():
    composed = compose_operator_chat_prompt("User: hi\nAI: hello", "Summarize")
    assert composed == "User: hi\nAI: hello\nUser: Summarize\nAI:"


def test_ai_ra15_compose_prompt_preserves_trailing_history_newline():
    composed = compose_operator_chat_prompt("User: hi\nAI: hello\n", "Next")
    assert composed == "User: hi\nAI: hello\nUser: Next\nAI:"


def test_ai_ra16_insecure_tls_bypass_is_loopback_only():
    assert allow_insecure_tls_for_host("localhost")
    assert allow_insecure_tls_for_host("127.0.0.1")
    assert allow_insecure_tls_for_host("::1")
    assert not allow_insecure_tls_for_host("api.example.com")
    assert not allow_insecure_tls_for_host("localhost.example.com")
