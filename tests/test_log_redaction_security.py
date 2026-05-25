"""AIH1-T-F* — log redaction helper."""

from __future__ import annotations

import logging
from unittest.mock import patch

from utils.log_redaction import redact_sensitive


def test_aih1_t_f01_redacts_worker_token_in_log_helper():
	raw = "x-ai-worker-token: super-secret-value"
	assert "[REDACTED]" in redact_sensitive(raw)
	assert "super-secret-value" not in redact_sensitive(raw)


def test_aih1_t_f02_long_prompt_truncated_in_redaction():
	raw = "x" * 1000
	out = redact_sensitive(raw, max_len=100)
	assert len(out) == 100
	assert out.endswith("...")


def test_aih1_t_f03_review_content_log_line_has_no_raw_body(caplog):
	from server import HealthServiceServicer

	caplog.set_level(logging.INFO, logger="server")
	servicer = HealthServiceServicer()
	request = type(
		"Req",
		(),
		{
			"title": "SECRET_TITLE",
			"body": "SECRET_BODY",
			"media_url": "",
			"content_type": "Blog",
		},
	)()
	with patch.object(servicer, "ReviewContent", wraps=servicer.ReviewContent):
		servicer.ReviewContent(request, None)
	combined = " ".join(r.message for r in caplog.records)
	assert "SECRET_TITLE" not in combined
	assert "SECRET_BODY" not in combined
	assert "title_len=" in combined
