"""HTTP fetch of public stats JSON for operator chat."""

from __future__ import annotations

import logging

from services.operator_stats_prompt import allow_insecure_tls_for_host
from utils.http_json import fetch_public_stats_body

logger = logging.getLogger(__name__)


def fetch_public_stats(absolute_url: str) -> tuple[str, str]:
	"""Return ``(json_body, error)`` — exactly one field is non-empty."""
	body, error = fetch_public_stats_body(
		absolute_url,
		allow_insecure_tls_for_host=allow_insecure_tls_for_host,
	)
	if error and not body:
		logger.warning("FetchPublicStats failed: %s", error)
	return body, error
