"""gRPC RPC handler implementations (AI-UP2 Phase B)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Any

from moderation_input_sanitize import sanitize_for_review
from services.chat_risk_scorer import score_chat_message
from services.embed_text import embed_texts
from services.explain_decision import explain_decision
from services.face_context_snapshot import build_face_context_snapshot
from services.operator_stats_prompt import (
	compose_operator_chat_prompt as _compose_operator_chat_prompt,
)
from services.operator_stats_prompt import (
	stats_context_prefix as _stats_context_prefix,
)
from services.public_stats_fetcher import fetch_public_stats
from services.report_templates import generate_report_markdown
from services.review_orchestrator import review_content_full
from services.search_worker_client import format_search_hits_for_prompt
from utils import grpc_errors as err
from utils.metrics import HEALTH_SCHEMA_VERSION, increment, observe_duration
from utils.ollama_circuit_breaker import circuit_breaker_disabled, get_ollama_circuit_breaker
from utils.rpc_limits import MAX_PROMPT_CHARS, clamp_max_new_tokens
from utils.rpc_rate_limit import check_rpc_rate_limit
from utils.trace_context import log_extra, set_trace_from_metadata
from utils.usage_accounting import UsageTimer

logger = logging.getLogger(__name__)


class RpcHandlers:
	def __init__(self, ai_service, health_pb2, host_profile_collector) -> None:
		self._ai_ref = ai_service
		self._pb2 = health_pb2
		self._collect_host_profile = host_profile_collector

	@property
	def _ai(self):
		if callable(self._ai_ref):
			return self._ai_ref()
		return self._ai_ref

	@_ai.setter
	def _ai(self, value) -> None:
		self._ai_ref = value

	def _rate_limited(self, method: str) -> tuple[bool, str]:
		return check_rpc_rate_limit(method)

	def _model_status_payload(self) -> dict[str, Any]:
		if self._ai is None:
			return {
				"schemaVersion": HEALTH_SCHEMA_VERSION,
				"ready": False,
				"loading": False,
				"unavailable": True,
				"modelName": None,
			}
		payload = {
			"schemaVersion": HEALTH_SCHEMA_VERSION,
			"ready": self._ai.is_loaded(),
			"loading": self._ai.is_loading(),
			"unavailable": self._ai.is_unavailable(),
			"modelName": self._ai.model_name,
		}
		load_err = self._ai.load_error()
		if load_err:
			payload["error"] = load_err[:200]
		return payload

	def health_check(self, _request, _context):
		increment("ai_grpc_requests_total", rpc="HealthCheck", status="ok")
		return self._pb2.HealthCheckResponse(
			status="success",
			message=json.dumps(self._model_status_payload()),
		)

	def get_host_profile(self, _request, _context):
		try:
			model_name = self._ai.model_name if self._ai is not None else None
			profile = self._collect_host_profile(model_name)
			if not profile:
				return self._pb2.HostProfileResponse(error="host profile unavailable")
			return self._pb2.HostProfileResponse(json_body=json.dumps(profile, ensure_ascii=False))
		except Exception:
			logger.debug("GetHostProfile failed", exc_info=True)
			return self._pb2.HostProfileResponse(error="host profile unavailable")

	def _check_ollama_ready(self) -> tuple[bool, str, str]:
		if self._ai is None:
			return False, "AIModelService not available", err.SERVICE_UNAVAILABLE
		if not circuit_breaker_disabled():
			breaker = get_ollama_circuit_breaker()
			if not breaker.allow_request():
				increment("ai_ollama_circuit_state", state="open")
				return False, "Ollama circuit breaker open", err.OLLAMA_CIRCUIT_OPEN
		if self._ai.is_loading():
			return False, "AI model is loading", err.MODEL_LOADING
		if self._ai.is_unavailable():
			return False, "AI model unavailable", err.OLLAMA_UNAVAILABLE
		return True, "", ""

	def _compose_full_prompt(self, request) -> tuple[str, str | None]:
		prompt = (request.prompt or "").strip()
		stats_block = ""
		if request.HasField("stats_context_json"):
			js = (request.stats_context_json or "").strip()
			if js:
				stats_block = _stats_context_prefix(js)
		search_block = ""
		if request.HasField("search_hits_json"):
			search_block = format_search_hits_for_prompt(request.search_hits_json or "")
		response_locale = None
		if request.HasField("response_locale"):
			rl = (request.response_locale or "").strip()
			if rl:
				response_locale = rl
		full = stats_block + search_block + prompt
		return full, response_locale

	def generate(self, request, context):
		start = time.monotonic()
		ok, rate_err = self._rate_limited("Generate")
		if not ok:
			increment("ai_grpc_requests_total", rpc="Generate", status="rate_limited")
			return self._pb2.GenerateResponse(text="", error=rate_err, error_code=err.RATE_LIMITED)

		set_trace_from_metadata(getattr(context, "invocation_metadata", lambda: None)())
		if not (request.prompt or "").strip():
			return self._pb2.GenerateResponse(
				text="", error="prompt is required", error_code=err.PROMPT_REQUIRED
			)
		full_prompt, response_locale = self._compose_full_prompt(request)
		if len(full_prompt) > MAX_PROMPT_CHARS:
			return self._pb2.GenerateResponse(
				text="", error="prompt too long", error_code=err.PROMPT_TOO_LONG
			)

		ready, msg, code = self._check_ollama_ready()
		if not ready:
			return self._pb2.GenerateResponse(text="", error=msg, error_code=code)

		max_new_tokens = clamp_max_new_tokens(
			request.max_new_tokens if request.max_new_tokens > 0 else 0
		)
		timer = UsageTimer("Generate", self._ai.model_name)
		try:
			text = self._ai.generate(
				full_prompt,
				max_new_tokens=max_new_tokens,
				response_locale=response_locale,
				rpc_deadline_seconds=context.time_remaining(),
			)
			if not circuit_breaker_disabled():
				get_ollama_circuit_breaker().record_success()
			record = timer.finish(prompt_chars=len(full_prompt), completion_chars=len(text or ""))
			logger.info(
				"Generate ok duration_ms=%.1f",
				record.duration_ms,
				extra=log_extra(),
			)
			increment("ai_grpc_requests_total", rpc="Generate", status="ok")
			observe_duration(
				"ai_grpc_request_duration_seconds", time.monotonic() - start, rpc="Generate"
			)
			return self._pb2.GenerateResponse(text=text)
		except RuntimeError as exc:
			err_text = str(exc)
			if not circuit_breaker_disabled():
				get_ollama_circuit_breaker().record_failure()
			if "MODEL_LOADING" in err_text:
				return self._pb2.GenerateResponse(
					text="",
					error="AI model is loading",
					error_code=err.MODEL_LOADING,
				)
			if "MODEL_LOAD_FAILED" in err_text:
				return self._pb2.GenerateResponse(
					text="",
					error="AI model failed to load",
					error_code=err.MODEL_LOAD_FAILED,
				)
			logger.exception("Generate failed")
			return self._pb2.GenerateResponse(
				text="", error="generation failed", error_code=err.GENERATION_FAILED
			)

	def generate_stream(self, request, context) -> Iterator[Any]:
		response = self.generate(request, context)
		text = response.text or ""
		if response.error:
			yield self._pb2.GenerateStreamChunk(
				text_delta="",
				is_final=True,
				error=response.error,
				error_code=response.error_code or "",
			)
			return
		chunk_size = 24
		for i in range(0, max(len(text), 1), chunk_size):
			part = text[i : i + chunk_size]
			is_final = i + chunk_size >= len(text)
			yield self._pb2.GenerateStreamChunk(text_delta=part, is_final=is_final)
		if not text:
			yield self._pb2.GenerateStreamChunk(text_delta="", is_final=True)

	def fetch_public_stats(self, request, _context):
		body, error = fetch_public_stats(request.absolute_url or "")
		if error:
			return self._pb2.FetchPublicStatsResponse(error=error)
		return self._pb2.FetchPublicStatsResponse(json_body=body)

	def operator_stats_chat(self, request, context):
		increment("ai_grpc_requests_total", rpc="OperatorStatsChat", status="deprecated")
		logger.warning("OperatorStatsChat is deprecated — use backend map-reduce + Generate")
		ok, rate_err = self._rate_limited("OperatorStatsChat")
		if not ok:
			return self._pb2.GenerateResponse(text="", error=rate_err, error_code=err.RATE_LIMITED)
		stats_json = ""
		if request.fetch_live_public_snapshot:
			u = (request.public_stats_absolute_url or "").strip()
			if not u:
				return self._pb2.GenerateResponse(
					text="", error="public_stats_absolute_url is required"
				)
			fr = self.fetch_public_stats(self._pb2.FetchPublicStatsRequest(absolute_url=u), context)
			if fr.error:
				return self._pb2.GenerateResponse(text="", error=fr.error)
			stats_json = (fr.json_body or "").strip()
		user_msg = (request.user_message or "").strip()
		if not user_msg:
			return self._pb2.GenerateResponse(text="", error="user_message is required")
		composed = _compose_operator_chat_prompt(request.history_text or "", user_msg)
		if len(composed) > MAX_PROMPT_CHARS:
			return self._pb2.GenerateResponse(
				text="", error="prompt too long", error_code=err.PROMPT_TOO_LONG
			)
		inner = self._pb2.GenerateRequest(
			prompt=composed, max_new_tokens=clamp_max_new_tokens(request.max_new_tokens)
		)
		if stats_json:
			inner.stats_context_json = stats_json
		return self.generate(inner, context)

	def review_content(self, request, _context):
		ok, rate_err = self._rate_limited("ReviewContent")
		if not ok:
			return self._pb2.ContentReviewResponse(
				decision="needs_human_review",
				confidence=0.5,
				risk_level="medium",
				flags=["rate_limit"],
				reason=rate_err,
				user_message="Content review is temporarily unavailable.",
				model_version="",
				trace_id="",
			)

		content_type = (request.content_type or "").strip()
		title, body, media_url = sanitize_for_review(
			request.title or "", request.body or "", request.media_url or None
		)

		def llm_generate(prompt: str, max_new_tokens: int = 256) -> str:
			if self._ai is None:
				return ""
			return self._ai.generate(prompt, max_new_tokens=max_new_tokens)

		result = review_content_full(
			title,
			body,
			media_url,
			content_type,
			llm_generate=llm_generate if self._ai is not None else None,
		)
		path = result.get("decision_path", "rules")
		logger.info(
			"ReviewContent decision=%s title_len=%d body_len=%d content_type=%s path=%s",
			result["decision"],
			len(title),
			len(body),
			content_type,
			path,
			extra=log_extra(),
		)
		increment("ai_review_content_decisions_total", decision=result["decision"], path=path)
		resp = self._pb2.ContentReviewResponse(
			decision=result["decision"],
			confidence=result["confidence"],
			risk_level=result["risk_level"],
			flags=result["flags"],
			reason=result["reason"],
			user_message=result["user_message"],
			model_version=result["model_version"],
			trace_id=result["trace_id"],
		)
		if result.get("auto_approve_eligible"):
			resp.auto_approve_eligible = True
		if result.get("policy_hint"):
			resp.policy_hint = str(result["policy_hint"])
		if result.get("decision_path"):
			resp.decision_path = str(result["decision_path"])
		return resp

	def build_face_context_snapshot(self, request, _context):
		formatted, schema_version, warnings, error = build_face_context_snapshot(
			request.snapshot_json or ""
		)
		if error:
			return self._pb2.FaceContextSnapshotResponse(error=error)
		return self._pb2.FaceContextSnapshotResponse(
			formatted_context=formatted,
			schema_version=schema_version,
			warnings=warnings,
		)

	def chat_risk_score(self, request, _context):
		result = score_chat_message(request.message_text or "", request.channel_type or "")
		return self._pb2.ChatRiskScoreResponse(
			risk_score=result.risk_score,
			action=result.action,
			flags=result.flags,
			safe_user_hint=result.safe_user_hint,
			model_version=result.model_version,
		)

	def generate_report(self, request, context):
		md, report_json, error = generate_report_markdown(
			request.report_type or "",
			request.report_locale or "en",
			request.input_json or "",
		)
		if error:
			return self._pb2.GenerateReportResponse(error=error)
		# Optional LLM polish when service available and max_new_tokens > 0
		if self._ai is not None and request.max_new_tokens > 0:
			polish = self.generate(
				self._pb2.GenerateRequest(
					prompt=f"Polish this report in markdown:\n\n{md}",
					max_new_tokens=request.max_new_tokens,
				),
				context,
			)
			if polish.text:
				md = polish.text
		return self._pb2.GenerateReportResponse(
			report_markdown=md,
			report_json=report_json,
			schema_version="report-v1",
		)

	def embed_text(self, request, _context):
		vectors, model_name, error = embed_texts(
			list(request.texts), request.model if request.HasField("model") else None
		)
		if error:
			return self._pb2.EmbedTextResponse(error=error)
		out = []
		for vec in vectors:
			out.append(self._pb2.EmbeddingVector(values=vec, dimensions=len(vec)))
		return self._pb2.EmbedTextResponse(vectors=out, model_version=model_name)

	def explain_decision(self, request, _context):
		data, error = explain_decision(request.trace_id or "", request.decision_snapshot_json or "")
		if error or data is None:
			return self._pb2.ExplainDecisionResponse(error=error or "explain failed")
		return self._pb2.ExplainDecisionResponse(
			path=data["path"],
			flags=data["flags"],
			reason=data["reason"],
			sanitized_excerpt=data["sanitized_excerpt"],
			model_version=data["model_version"],
		)
