"""Optional shared-secret auth for AI gRPC worker RPCs (BSH3-G3 / AIH1-A4/A7)."""

from __future__ import annotations

import os
import secrets

import grpc

METADATA_KEY = "x-ai-worker-token"
ENV_VAR = "AI_WORKER_EXPECTED_TOKEN"
HEALTHCHECK_REQUIRES_TOKEN_ENV = "MFAI_HEALTHCHECK_REQUIRES_TOKEN"


def expected_token_from_env() -> str:
    """Return trimmed expected token from environment (empty when auth is disabled)."""
    return os.getenv(ENV_VAR, "").strip()


def healthcheck_requires_token() -> bool:
    return os.getenv(HEALTHCHECK_REQUIRES_TOKEN_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class WorkerAuthInterceptor(grpc.ServerInterceptor):
    """Enforces ``AI_WORKER_EXPECTED_TOKEN`` on application RPCs; HealthCheck policy configurable."""

    def __init__(
        self,
        expected_token: str,
        *,
        require_healthcheck_token: bool | None = None,
    ) -> None:
        self._expected_token = expected_token.strip()
        self._require_healthcheck_token = (
            healthcheck_requires_token()
            if require_healthcheck_token is None
            else require_healthcheck_token
        )

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

    def _token_ok(self, metadata: dict[str, str]) -> bool:
        provided = metadata.get(METADATA_KEY)
        if not provided or not self._expected_token:
            return False
        return secrets.compare_digest(provided, self._expected_token)

    def intercept_service(self, continuation, handler_call_details):
        if not self._expected_token:
            return continuation(handler_call_details)

        method = handler_call_details.method or ""
        metadata = self._metadata_dict(handler_call_details.invocation_metadata)
        is_healthcheck = method.endswith("/HealthCheck")

        if is_healthcheck and not self._require_healthcheck_token:
            return continuation(handler_call_details)

        if not self._token_ok(metadata):
            return grpc.unary_unary_rpc_method_handler(self._deny_unary)

        return continuation(handler_call_details)

    @staticmethod
    def _deny_unary(_request, context):
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            "invalid or missing x-ai-worker-token",
        )
