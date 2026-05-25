#!/usr/bin/env python3
"""
ai_model_service.py - Multilingual conversational AI service

Model inference runs through Ollama by default (override with OLLAMA_MODEL).
"""

import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime

from utils.env import env_float, env_int, ollama_base_url
from utils.log_redaction import redact_sensitive

logger = logging.getLogger(__name__)

# Override in Docker via OLLAMA_MODEL.
DEFAULT_MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"
DEFAULT_MAX_NEW_TOKENS = 256
# Safety cap even when backend requests more.
DEFAULT_MAX_NEW_TOKENS_CAP = 384


def _thread_count() -> int:
	raw = os.getenv("OMP_NUM_THREADS") or os.getenv("MFAI_CONTAINER_CPUS") or "4"
	try:
		return max(1, int(float(raw)))
	except ValueError:
		return 4


_THINK_TAG_OPEN = "<" + "think" + ">"
_THINK_TAG_CLOSE = "</" + "think" + ">"
_THINK_BLOCK_RE = re.compile(
	re.escape(_THINK_TAG_OPEN) + r".*?" + re.escape(_THINK_TAG_CLOSE),
	re.DOTALL | re.IGNORECASE,
)
_THINK_OPEN_RE = re.compile(re.escape(_THINK_TAG_OPEN) + r".*", re.DOTALL | re.IGNORECASE)
_INVENTED_JSON_FENCE_RE = re.compile(
	r"```(?:json)?\s*\{[\s\S]*?(?:system_time|__typename)[\s\S]*?\}\s*```",
	re.IGNORECASE,
)


_PARROT_CLOSING_RE = re.compile(
	r"\s*(?:"
	r"M[aá]m sa dobre,?\s*ďakujem\.?\s*(?:A ty\??)?|"
	r"I am doing well,?\s*thank you\.?\s*(?:And you\??)?"
	r")\s*$",
	re.IGNORECASE,
)


def _last_user_message_from_messages(messages: list[dict]) -> str:
	for msg in reversed(messages):
		if msg.get("role") == "user":
			content = msg.get("content")
			if isinstance(content, str) and content.strip():
				return content.strip()
	return ""


def _user_asked_about_wellbeing(user_message: str) -> bool:
	u = user_message.lower()
	return any(
		phrase in u
		for phrase in (
			"ako sa máš",
			"ako sa mas",
			"ako sa máte",
			"how are you",
			"how r u",
			"how are u",
		)
	)


def _trim_parroted_closing(text: str, last_user_message: str) -> str:
	"""Drop the stock wellbeing sign-off unless the user asked how you are."""
	if not text or _user_asked_about_wellbeing(last_user_message):
		return text
	cleaned = text.strip()
	while True:
		next_text = _PARROT_CLOSING_RE.sub("", cleaned).strip()
		if next_text == cleaned:
			break
		cleaned = next_text
	return cleaned if cleaned else text.strip()


def _strip_thinking_artifacts(text: str) -> str:
	"""Remove chain-of-thought blocks that must not appear in chat UI."""
	if not text:
		return text
	cleaned = _THINK_BLOCK_RE.sub("", text)
	cleaned = _THINK_OPEN_RE.sub("", cleaned)
	return cleaned.strip()


def _strip_invented_json_fences(text: str) -> str:
	"""Drop hallucinated ```json blocks (e.g. fake system_time / __typename)."""
	cleaned = _INVENTED_JSON_FENCE_RE.sub("", text).strip()
	return re.sub(r"\n{3,}", "\n\n", cleaned)


LOCALE_NAMES = {
	"en": "English",
	"sk": "Slovak",
	"cz": "Czech",
}


def _normalize_response_locale(response_locale: str | None) -> tuple[str, str]:
	code = (response_locale or "").strip().lower() or "en"
	if code not in LOCALE_NAMES:
		if response_locale and str(response_locale).strip():
			logger.warning("Unknown response_locale=%r, defaulting to en", response_locale)
		code = "en"
	return code, LOCALE_NAMES[code]


def _response_language_block(locale_code: str, locale_name: str) -> str:
	return (
		"## Response language (mandatory)\n"
		f"- The operator's admin UI locale is: **{locale_name}** (code `{locale_code}`).\n"
		f"- You MUST write every reply entirely in **{locale_name}**, regardless of:\n"
		"  - the language of the user's latest message,\n"
		"  - the language of earlier messages in the conversation history,\n"
		"  - the language of JSON field names in operator statistics.\n"
		"- Do not mix languages in one reply unless the user explicitly asks for a translation comparison.\n"
		f"- If you cannot answer, say so briefly in **{locale_name}**.\n"
	)


def _communication_rules(locale_code: str) -> str:
	rules = """## Communication rules
2. **Style:** Be friendly, clear, and concise — one or two short sentences for simple greetings. Do not prefix replies with your name (no "MFAI Assistant:").
3. **Code:** When showing code examples, use proper markdown code blocks with language specification.
4. **Honesty:** If you don't know something or are unsure, say so honestly. Don't make up facts.
5. **Platform statistics:** When operator statistics JSON is present, use ONLY these sources:
   - `dashboard.*` — totals (same as admin dashboard): usersCount, friendRequestsCount (pending only), messagesCount, facesCount, pagesCount, friendshipsCount, friendRequestsAcceptedCount, friendRequestsRejectedCount, userFollowsCount, userBlocksCount, messagesPendingRequestCount, notificationsCount, albumsCount, blogsCount, reelsCount, storiesCount, storyViewsCount, faceChatRoomsCount, faceChatRoomMembersCount, faceChatRoomMessagesCount, faceChatRoomJoinRequestsPendingCount, faceWallTicketsCount, faceWallTicketsByStatus (Active/Approved/Denied), faceWallTicketCommentsCount, faceWallTicketLikesCount, userFaceProfilesCount, userFaceProfileLikesCount, userFaceProfileCommentsCount, userFaceProfileReviewsCount, albumCommentsCount, blogCommentsCount, reelCommentsCount, storyCommentsCount, albumLikesCount, blogLikesCount, reelLikesCount, storyLikesCount, aiReviewJobsCount, contentModerationEventsCount, oauthClientsCount.
   - `timeseriesLast7Days.series` — daily counts for users/messages/stories over the last 7 UTC days (trends only).
   Quote exact numbers; if a field is absent, say you do not have it. Never invent fields.
6. **Date and time:** Use server time from Live context, NOT statistics JSON. One short sentence for clock questions. No fake JSON blocks.
7. **Formatting:** Prefer plain sentences. Avoid markdown JSON/code blocks unless the user asked for code or raw data.
8. **Thinking:** Never output internal reasoning, XML tags, or English planning text. Reply with only the final user-facing answer.
"""
	if locale_code == "sk":
		rules += (
			"9. **Slovak (sk):** Use standard Slovak (slovenčina), not Czech. "
			"Prefer *toto* (not *tohle*). Use correct grammar; do not mix Cyrillic letters.\n"
		)
	rules += """10. **No parroting:** Answer only the latest user message. Never append a stock closing such as "Mám sa dobre, ďakujem. A ty?" unless the user explicitly asked how you are.
11. **Stay on topic:** Do not invent phone numbers, emails, or APIs. If you lack data, say so briefly in the operator's response language.
12. **Many Faces / MFAI:** "Many faces" means this demo platform; user counts and totals come from the statistics JSON when attached, not from imagination.
"""
	return rules


def _system_prompt_with_runtime(response_locale: str | None = None) -> str:
	code, name = _normalize_response_locale(response_locale)
	now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
	return (
		f"{SYSTEM_PROMPT}\n\n"
		f"{_response_language_block(code, name)}\n\n"
		f"{_communication_rules(code)}\n\n"
		"## Live context (authoritative)\n"
		f"- Server time now: **{now}** — use for date/time questions in plain language.\n"
		"- Do not output JSON for clock/time unless the user explicitly asked for raw JSON.\n"
	)


def _extract_operator_stats_context(prompt: str) -> tuple[str | None, str]:
	"""Split the backend's prepended operator stats block from the chat prompt."""
	text = prompt.strip()
	separator = "\n\n---\n\n"
	if not text.startswith("[Operator platform statistics JSON") or separator not in text:
		return None, prompt

	stats_block, rest = text.split(separator, 1)
	return stats_block.strip(), rest.strip()


def _sanitize_assistant_reply(text: str, last_user_message: str = "") -> str:
	response = _strip_thinking_artifacts(text.strip())
	response = _strip_invented_json_fences(response)
	for prefix in ("MFAI Assistant:", "MFAI Assistant :"):
		if response.lower().startswith(prefix.lower()):
			response = response[len(prefix) :].strip()
	for marker in ["User:", "user:", "AI:", "ai:", "<|im_end|>", "<|endoftext|>"]:
		idx = response.find(marker)
		if idx > 0:
			response = response[:idx].strip()
	response = _trim_parroted_closing(response, last_user_message)
	return response if response else "..."


SYSTEM_PROMPT = """You are MFAI Assistant – an intelligent, friendly and knowledgeable AI assistant built into the MFAI Demo application.

## Your identity
- Your name is **MFAI Assistant**. When asked who you are, introduce yourself by this name.
- You were created as part of the MFAI Demo project – a full-stack demo application showcasing modern web technologies with AI integration.
- You run locally on the user's machine as a private AI – no data is sent to external cloud APIs.

## About the MFAI Demo project
The application you are part of consists of these components:
- **Frontend (fe_demo)** – React + TypeScript + Vite application for end users (port 8081)
- **Admin panel (admin_demo)** – React + TypeScript + Vite admin panel where this chat lives (port 8082)
- **Backend API (be_demo)** – ASP.NET Core (.NET 10) REST API with SignalR for real-time chat (port 8000)
- **AI Service (ai_demo)** – Python gRPC server running a local Qwen model (port 50051)
- **Database** – PostgreSQL for data storage (port 5432)
- **Logger** – Seq for centralized logging, Dozzle for Docker log viewing
- Everything runs in Docker containers orchestrated by docker-compose.

## Technology knowledge
You have solid knowledge of these technologies and can help with questions about them:
- **Frontend:** React, TypeScript, Vite, Material UI, React Router, React Query, Axios, SignalR client
- **Backend:** C#, ASP.NET Core, Entity Framework Core, SignalR, gRPC, JWT authentication
- **AI/ML:** Python, Ollama, local language models, gRPC
- **DevOps:** Docker, docker-compose, PostgreSQL, Seq logging, CI/CD
- **General programming:** algorithms, data structures, design patterns, REST API design, database design

## Example topics you can help with
- Explaining how the MFAI Demo application works
- Answering programming questions (React, C#, Python, SQL, etc.)
- Helping debug issues in the codebase
- Explaining software architecture concepts
- General knowledge questions
- Writing or reviewing code snippets
- Explaining AI/ML concepts
"""


class AIModelService:
	"""
	Multilingual conversational AI service backed by Ollama.
	"""

	def __init__(self, model_name: str | None = None):
		self._model_name = model_name or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL_NAME
		self._load_error: str | None = None
		self._ollama_base_url = ollama_base_url()
		self._ollama_timeout_seconds = env_int("OLLAMA_TIMEOUT_SECONDS", 300)
		cap_raw = os.getenv("MFAI_MAX_NEW_TOKENS_CAP", str(DEFAULT_MAX_NEW_TOKENS_CAP))
		try:
			self._max_new_tokens_cap = max(32, int(cap_raw))
		except ValueError:
			self._max_new_tokens_cap = DEFAULT_MAX_NEW_TOKENS_CAP

	@property
	def model_name(self) -> str:
		return self._model_name

	def is_loading(self) -> bool:
		return False

	def is_unavailable(self) -> bool:
		self._ollama_model_available()
		return self._load_error is not None

	def load_error(self) -> str | None:
		return self._load_error

	def preload(self) -> None:
		"""Verify that the configured Ollama model is available."""
		self._ensure_loaded()

	def _ensure_loaded(self):
		self._ensure_ollama_ready()

	def _ollama_post_json(
		self,
		path: str,
		payload: dict,
		*,
		rpc_deadline_seconds: float | None = None,
	) -> dict:
		body = json.dumps(payload).encode("utf-8")
		req = urllib.request.Request(
			f"{self._ollama_base_url}{path}",
			data=body,
			headers={"Content-Type": "application/json"},
			method="POST",
		)
		timeout = self._ollama_timeout_seconds
		if rpc_deadline_seconds is not None and rpc_deadline_seconds > 0:
			timeout = min(timeout, rpc_deadline_seconds)
		try:
			with urllib.request.urlopen(req, timeout=timeout) as resp:
				return json.loads(resp.read().decode("utf-8"))
		except urllib.error.HTTPError as exc:
			detail = redact_sensitive(exc.read().decode("utf-8", errors="replace"))
			raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc

	def _ollama_model_available(self) -> bool:
		try:
			self._ollama_post_json("/api/show", {"model": self._model_name})
			self._load_error = None
			return True
		except Exception as exc:
			self._load_error = str(exc)
			return False

	def _ensure_ollama_ready(self) -> None:
		if not self._ollama_model_available():
			raise RuntimeError(
				f"MODEL_LOAD_FAILED: Ollama model '{self._model_name}' is not ready at "
				f"{self._ollama_base_url}: {self._load_error}"
			)

	def _ollama_options(self, max_new_tokens: int) -> dict:
		options = {
			"num_ctx": env_int("OLLAMA_NUM_CTX", 4096),
			"num_predict": max_new_tokens,
			"num_thread": env_int("OLLAMA_NUM_THREAD", _thread_count()),
			"temperature": env_float("OLLAMA_TEMPERATURE", 0.35),
			"top_p": env_float("OLLAMA_TOP_P", 0.9),
			"top_k": env_int("OLLAMA_TOP_K", 40),
			"repeat_penalty": env_float("OLLAMA_REPEAT_PENALTY", 1.15),
		}
		for option_name, env_name in {
			"num_gpu": "OLLAMA_NUM_GPU",
			"num_batch": "OLLAMA_NUM_BATCH",
		}.items():
			raw = os.getenv(env_name)
			if raw is None or not raw.strip():
				continue
			try:
				options[option_name] = int(raw)
			except ValueError:
				logger.warning("Ignoring invalid %s=%r", env_name, raw)
		return options

	def _generate_ollama(
		self,
		messages: list[dict],
		max_new_tokens: int,
		*,
		rpc_deadline_seconds: float | None = None,
	) -> str:
		payload = {
			"model": self._model_name,
			"messages": messages,
			"stream": False,
			"keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
			"options": self._ollama_options(max_new_tokens),
		}
		data = self._ollama_post_json(
			"/api/chat",
			payload,
			rpc_deadline_seconds=rpc_deadline_seconds,
		)
		message = data.get("message") if isinstance(data, dict) else None
		if isinstance(message, dict):
			return str(message.get("content") or "")
		return str(data.get("response") or "") if isinstance(data, dict) else ""

	@staticmethod
	def _parse_prompt(prompt: str, response_locale: str | None = None) -> list[dict]:
		"""Convert the 'User: …\\nAI: …' prompt from the backend into chat messages."""
		stats_context, prompt_without_stats = _extract_operator_stats_context(prompt)
		messages = [{"role": "system", "content": _system_prompt_with_runtime(response_locale)}]
		for line in prompt_without_stats.strip().splitlines():
			line = line.strip()
			if not line:
				continue
			if line.lower().startswith("user:"):
				text = line[5:].strip()
				if text:
					messages.append({"role": "user", "content": text})
			elif line.lower().startswith("ai:"):
				text = line[3:].strip()
				if text:
					messages.append({"role": "assistant", "content": text})
		if stats_context:
			stats_message = {
				"role": "system",
				"content": (
					"Authoritative read-only operator platform statistics for the next user question. "
					"Use exact values from this JSON when answering statistics questions. "
					"If the user asks about any platform metric, prefer dashboard.* totals and "
					"timeseriesLast7Days.series trends from this context. Do not invent fields.\n\n"
					f"{stats_context}"
				),
			}
			last_user_idx = next(
				(i for i in range(len(messages) - 1, 0, -1) if messages[i].get("role") == "user"),
				len(messages),
			)
			messages.insert(last_user_idx, stats_message)
		return messages

	def _cap_max_tokens(self, max_new_tokens: int | None) -> int:
		requested = max_new_tokens or DEFAULT_MAX_NEW_TOKENS
		return min(max(1, requested), self._max_new_tokens_cap)

	def generate(
		self,
		prompt: str,
		max_new_tokens: int | None = None,
		response_locale: str | None = None,
		rpc_deadline_seconds: float | None = None,
	) -> str:
		if not prompt or not prompt.strip():
			return ""

		self._ensure_loaded()
		max_tok = self._cap_max_tokens(max_new_tokens)

		messages = self._parse_prompt(prompt, response_locale=response_locale)
		if len(messages) <= 1:
			messages.append({"role": "user", "content": prompt.strip()})

		try:
			response = self._generate_ollama(
				messages,
				max_tok,
				rpc_deadline_seconds=rpc_deadline_seconds,
			)
			last_user = _last_user_message_from_messages(messages)
			return _sanitize_assistant_reply(response, last_user)
		except Exception as e:
			logger.exception("Error generating text: %s", redact_sensitive(str(e)))
			return ""

	def is_loaded(self) -> bool:
		return self._ollama_model_available()
