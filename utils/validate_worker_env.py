"""Startup validation for hardened AI worker profiles (AIH1-A1/A2)."""

from __future__ import annotations

import os
from pathlib import Path

from utils.env import validate_ollama_base_url_hardened


class WorkerEnvValidationError(Exception):
	"""Raised when required security env is missing or invalid."""


def is_truthy(name: str) -> bool:
	return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def is_hardened_profile() -> bool:
	return is_truthy("MFAI_REQUIRE_WORKER_AUTH") or is_truthy("MFAI_HARDENED_PROFILE")


def validate_worker_env() -> None:
	errors: list[str] = []
	if is_hardened_profile():
		if not os.getenv("AI_WORKER_EXPECTED_TOKEN", "").strip():
			errors.append("AI_WORKER_EXPECTED_TOKEN is required when MFAI_REQUIRE_WORKER_AUTH=1")
		cert = os.getenv("GRPC_TLS_CERT_FILE", "").strip()
		key = os.getenv("GRPC_TLS_KEY_FILE", "").strip()
		if cert or key:
			if not (cert and key and Path(cert).is_file() and Path(key).is_file()):
				errors.append("GRPC_TLS_CERT_FILE and GRPC_TLS_KEY_FILE must be readable files")
		elif not is_truthy("MFAI_ALLOW_INSECURE_GRPC"):
			errors.append(
				"MFAI_ALLOW_INSECURE_GRPC=1 is required when TLS creds are absent in hardened profile"
			)
		ok, reason = validate_ollama_base_url_hardened()
		if not ok:
			errors.append(reason)
	if errors:
		raise WorkerEnvValidationError("; ".join(errors))
