"""Optional shared-secret auth for AI gRPC worker RPCs (BSH3-G3)."""

from __future__ import annotations

import os

import grpc

METADATA_KEY = "x-ai-worker-token"
ENV_VAR = "AI_WORKER_EXPECTED_TOKEN"


def expected_token_from_env() -> str:
    """Return trimmed expected token from environment (empty when auth is disabled)."""
    return os.getenv(ENV_VAR, "").strip()


class WorkerAuthInterceptor(grpc.ServerInterceptor):
    """Enforces ``AI_WORKER_EXPECTED_TOKEN`` on application RPCs; HealthCheck stays public."""

    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token.strip()

    @staticmethod
    def _metadata_dict(raw) -> dict[str, str]:
        if not raw:
            return {}
        result: dict[str, str] = {}
        for entry in raw:
            if hasattr(entry, "key") and hasattr(entry, "value"):
                result[str(entry.key)] = str(entry.value)
            elif isinstance(entry, (tuple, list)) and len(entry) == 2:
                result[str(entry[0])] = str(entry[1])
        return result

    def intercept_service(self, continuation, handler_call_details):
        if not self._expected_token:
            return continuation(handler_call_details)

        method = handler_call_details.method or ""
        if method.endswith("/HealthCheck"):
            return continuation(handler_call_details)

        metadata = self._metadata_dict(handler_call_details.invocation_metadata)
        if metadata.get(METADATA_KEY) != self._expected_token:
            return grpc.unary_unary_rpc_method_handler(self._deny_unary)

        return continuation(handler_call_details)

    @staticmethod
    def _deny_unary(_request, context):
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            "invalid or missing x-ai-worker-token",
        )
