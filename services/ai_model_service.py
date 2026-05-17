#!/usr/bin/env python3
"""
ai_model_service.py - Multilingual conversational AI service

Model: Qwen/Qwen3-4B-Instruct-2507 by default (override with MFAI_AI_MODEL_NAME).
For faster local dev in Docker, compose often sets Qwen2.5-1.5B-Instruct (~3× smaller).
"""

import logging
import os
import threading

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

# Override in Docker via MFAI_AI_MODEL_NAME (compose defaults to 0.5B for CPU RAM).
DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 200
# Safety cap even when backend requests more (CPU Docker is slow with large values).
DEFAULT_MAX_NEW_TOKENS_CAP = 512

def _thread_count() -> int:
    raw = os.getenv("OMP_NUM_THREADS") or os.getenv("MFAI_CONTAINER_CPUS") or "4"
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return 4


_threads = _thread_count()
torch.set_num_threads(_threads)
if hasattr(torch, "set_num_interop_threads"):
    torch.set_num_interop_threads(max(1, _threads // 2))


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


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
- **AI/ML:** Python, PyTorch, Hugging Face Transformers, gRPC, language models
- **DevOps:** Docker, docker-compose, PostgreSQL, Seq logging, CI/CD
- **General programming:** algorithms, data structures, design patterns, REST API design, database design

## Communication rules
1. **Language:** Always respond in the same language the user writes in. If the user writes in Slovak, respond in Slovak. If in English, respond in English. If in Czech, respond in Czech.
2. **Style:** Be friendly, clear, and concise. Use short paragraphs and bullet points when appropriate.
3. **Code:** When showing code examples, use proper markdown code blocks with language specification.
4. **Honesty:** If you don't know something or are unsure, say so honestly. Don't make up facts.
5. **Helpfulness:** Proactively suggest related information or next steps when relevant.
6. **Formatting:** Use markdown formatting (bold, lists, code blocks) to make responses readable.

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
    Multilingual conversational AI service backed by a local Qwen instruct model.
    """

    _load_lock = threading.Lock()

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or os.getenv("MFAI_AI_MODEL_NAME", DEFAULT_MODEL_NAME)
        self._tokenizer = None
        self._model = None
        self._loading = False
        self._load_error: str | None = None
        self._device = (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self._local_files_only = _env_truthy("MFAI_LOCAL_FILES_ONLY") or _env_truthy("HF_HUB_OFFLINE")
        self._fast_generation = _env_truthy("MFAI_FAST_GENERATION", "1")
        cap_raw = os.getenv("MFAI_MAX_NEW_TOKENS_CAP", str(DEFAULT_MAX_NEW_TOKENS_CAP))
        try:
            self._max_new_tokens_cap = max(32, int(cap_raw))
        except ValueError:
            self._max_new_tokens_cap = DEFAULT_MAX_NEW_TOKENS_CAP

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_loading(self) -> bool:
        return self._loading and self._model is None and self._load_error is None

    def is_unavailable(self) -> bool:
        return self._load_error is not None and self._model is None

    def load_error(self) -> str | None:
        return self._load_error

    def preload(self) -> None:
        """Eager-load weights (e.g. background thread on server start)."""
        self._ensure_loaded()

    def _ensure_loaded(self):
        with self._load_lock:
            if self._model is not None:
                return
            if self._load_error is not None:
                raise RuntimeError(f"MODEL_LOAD_FAILED: {self._load_error}")
            self._loading = True
            self._load_error = None
            try:
                load_threads = max(1, min(2, _thread_count()))
                torch.set_num_threads(load_threads)
                logger.info(
                    "Loading AI model: %s (device=%s, load_threads=%s, local_only=%s)",
                    self._model_name,
                    self._device,
                    load_threads,
                    self._local_files_only,
                )
                tok_kw = {"trust_remote_code": True, "local_files_only": self._local_files_only}
                self._tokenizer = AutoTokenizer.from_pretrained(self._model_name, **tok_kw)
                dtype = torch.float16 if self._device in {"cuda", "mps"} else torch.float32
                model_kw = {
                    "dtype": dtype,
                    "trust_remote_code": True,
                    "low_cpu_mem_usage": True,
                    "local_files_only": self._local_files_only,
                }
                self._model = AutoModelForCausalLM.from_pretrained(self._model_name, **model_kw)
                self._model.to(self._device)
                self._model.eval()
                logger.info("AI model %s loaded successfully on %s.", self._model_name, self._device)
            except Exception as exc:
                self._load_error = str(exc)
                logger.exception("AI model load failed: %s", exc)
                raise
            finally:
                self._loading = False
                torch.set_num_threads(_threads)

    @staticmethod
    def _parse_prompt(prompt: str) -> list[dict]:
        """Convert the 'User: …\\nAI: …' prompt from the backend into chat messages."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for line in prompt.strip().splitlines():
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
        return messages

    def _cap_max_tokens(self, max_new_tokens: int | None) -> int:
        requested = max_new_tokens or DEFAULT_MAX_NEW_TOKENS
        return min(max(1, requested), self._max_new_tokens_cap)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int | None = None,
    ) -> str:
        if not prompt or not prompt.strip():
            return ""

        self._ensure_loaded()
        tok = self._tokenizer
        max_tok = self._cap_max_tokens(max_new_tokens)

        messages = self._parse_prompt(prompt)
        if len(messages) <= 1:
            messages.append({"role": "user", "content": prompt.strip()})

        try:
            input_text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            input_ids = tok.encode(input_text, return_tensors="pt").to(self._device)

            # Shorter context = faster prefill on CPU
            max_context = int(os.getenv("MFAI_MAX_CONTEXT_TOKENS", "1200"))
            if input_ids.shape[-1] > max_context:
                input_ids = input_ids[:, -max_context:]

            gen_kw: dict = {
                "max_new_tokens": max_tok,
                "pad_token_id": tok.eos_token_id,
            }
            if self._fast_generation:
                gen_kw["do_sample"] = False
            else:
                gen_kw.update(
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    repetition_penalty=1.15,
                )

            with torch.no_grad():
                output_ids = self._model.generate(input_ids, **gen_kw)

            new_tokens = output_ids[:, input_ids.shape[-1] :]
            response = tok.decode(new_tokens[0], skip_special_tokens=True).strip()

            for marker in ["User:", "user:", "AI:", "ai:", "<|im_end|>", "<|endoftext|>"]:
                idx = response.find(marker)
                if idx > 0:
                    response = response[:idx].strip()

            return response if response else "..."
        except Exception as e:
            logger.exception("Error generating text: %s", e)
            return ""

    def is_loaded(self) -> bool:
        return self._model is not None
