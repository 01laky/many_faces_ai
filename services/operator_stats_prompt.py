"""Operator stats chat prompt helpers (wire contract with backend + AIModelService)."""


def stats_context_prefix(stats_json: str) -> str:
    """Return the backend statistics block prepended to operator chat prompts."""
    return (
        "[Operator platform statistics JSON — authoritative DB snapshot at snapshotUtc. "
        "Use dashboard.* for totals and timeseriesLast7Days.series for 7-day daily trends. "
        "NOT for clock/time — use Live context server time. Do NOT invent fields.]\n"
        + stats_json
        + "\n\n---\n\n"
    )


def compose_operator_chat_prompt(history_text: str, user_message: str) -> str:
    """Build the transcript shape consumed by AIModelService._parse_prompt."""
    parts: list[str] = []
    if history_text.strip():
        parts.append(history_text.strip())
        parts.append("\n")
    parts.append("User: ")
    parts.append(user_message)
    parts.append("\nAI:")
    return "".join(parts)


def allow_insecure_tls_for_host(host: str) -> bool:
    """Only local dev loopback hosts may bypass certificate validation for stats fetches."""
    return host.lower() in ("localhost", "127.0.0.1", "::1")
