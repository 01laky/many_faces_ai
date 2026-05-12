#!/usr/bin/env python3
"""
ai_model_service.py - Multilingual conversational AI service

Model: Qwen/Qwen3-4B-Instruct-2507 by default
- Instruction-tuned, multilingual, open-weight Qwen3 model
- Supports English, Slovak, Czech, and other languages
- Runs locally with Hugging Face Transformers, no API key required
- Can be overridden with MFAI_AI_MODEL_NAME for smaller or larger Qwen variants
- License: Apache 2.0
"""

import logging
import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "Qwen/Qwen3-4B-Instruct-2507"
DEFAULT_MAX_NEW_TOKENS = 200

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

    Uses the model's built-in chat template to produce natural multi-turn
    conversation in any language the user writes in.
    The model is loaded lazily on the first generate() call.
    """

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or os.getenv("MFAI_AI_MODEL_NAME", DEFAULT_MODEL_NAME)
        self._tokenizer = None
        self._model = None
        self._loading = False
        self._device = (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if self._loading:
            raise RuntimeError("MODEL_LOADING")
        self._loading = True
        try:
            logger.info("Loading AI model: %s (first request)", self._model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_name, trust_remote_code=True
            )
            dtype = torch.float16 if self._device in {"cuda", "mps"} else torch.float32
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_name, torch_dtype=dtype, trust_remote_code=True
            ).to(self._device)
            self._model.eval()
            logger.info("AI model %s loaded successfully on %s.", self._model_name, self._device)
        except Exception:
            self._loading = False
            raise

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

    def generate(
        self,
        prompt: str,
        max_new_tokens: int | None = None,
    ) -> str:
        if not prompt or not prompt.strip():
            return ""

        self._ensure_loaded()
        tok = self._tokenizer
        max_tok = max_new_tokens or DEFAULT_MAX_NEW_TOKENS

        messages = self._parse_prompt(prompt)
        if len(messages) <= 1:
            messages.append({"role": "user", "content": prompt.strip()})

        try:
            input_text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            input_ids = tok.encode(input_text, return_tensors="pt").to(self._device)

            # Trim to fit context window
            if input_ids.shape[-1] > 1800:
                input_ids = input_ids[:, -1800:]

            with torch.no_grad():
                output_ids = self._model.generate(
                    input_ids,
                    max_new_tokens=max_tok,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    repetition_penalty=1.15,
                    pad_token_id=tok.eos_token_id,
                )

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
