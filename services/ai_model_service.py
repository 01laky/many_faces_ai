#!/usr/bin/env python3
"""
ai_model_service.py - Service for communicating with the local AI model (DistilGPT-2)

This module provides the AIModelService class, which:
- Loads the free DistilGPT-2 model from Hugging Face (no API key required)
- Runs locally on CPU, no external service
- Provides generate() for text completion / continuation generation

Model: distilgpt2
- Small version of GPT-2 (~82M parameters), suitable for demo and development
- License: Apache 2.0
- Languages: primarily English
"""

import logging

logger = logging.getLogger(__name__)

# Default model settings
DEFAULT_MODEL_NAME = "distilgpt2"
DEFAULT_MAX_NEW_TOKENS = 50
DEFAULT_DO_SAMPLE = True
DEFAULT_TEMPERATURE = 0.7


class AIModelService:
    """
    Service for working with the local AI model (DistilGPT-2).

    The model is loaded lazily (on first generate() call) so the server
    starts quickly and memory is used only when the model is actually needed.

    Usage:
        service = AIModelService()
        text = service.generate("The weather today is")
        # -> e.g. "The weather today is nice and sunny."
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        do_sample: bool = DEFAULT_DO_SAMPLE,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        """
        Initialize the service (does not load the model yet).

        Args:
            model_name: Hugging Face model name (default distilgpt2).
            max_new_tokens: Maximum number of tokens to generate per request.
            do_sample: If True, next-token selection is random (for diversity).
            temperature: Generation "randomness" (higher = more creative, lower = more consistent).
        """
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._do_sample = do_sample
        self._temperature = temperature
        # Pipeline is created on first generate() call
        self._pipeline = None

    def _get_pipeline(self):
        """
        Return the text-generation pipeline; on first call, load the model from Hugging Face.

        The model is downloaded to cache (~/.cache/huggingface) and reused from disk
        on subsequent runs. Runs on CPU without GPU.
        """
        if self._pipeline is None:
            logger.info("Loading AI model: %s (first request)", self._model_name)
            try:
                from transformers import pipeline

                self._pipeline = pipeline(
                    "text-generation",
                    model=self._model_name,
                    # No tokenizer= needed – pipeline uses the model default
                )
                logger.info("AI model %s loaded successfully.", self._model_name)
            except Exception as e:
                logger.exception("Failed to load model %s: %s", self._model_name, e)
                raise
        return self._pipeline

    def generate(
        self,
        prompt: str,
        max_new_tokens: int | None = None,
        do_sample: bool | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Generate text continuation for the given prompt.

        Args:
            prompt: Initial text (prompt) from which the model generates further.
            max_new_tokens: Max number of new tokens (if None, value from __init__ is used).
            do_sample: Whether to use random token selection (if None, from __init__).
            temperature: Generation temperature (if None, from __init__).

        Returns:
            Generated string: prompt + continuation. On model failure, returns at least prompt
            or empty string and logs the error.
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt in generate(), returning empty string.")
            return ""

        max_tok = max_new_tokens if max_new_tokens is not None else self._max_new_tokens
        do_samp = do_sample if do_sample is not None else self._do_sample
        temp = temperature if temperature is not None else self._temperature

        try:
            pipe = self._get_pipeline()
            # pipeline returns a list of dicts, each with key 'generated_text'
            out = pipe(
                prompt,
                max_new_tokens=max_tok,
                do_sample=do_samp,
                temperature=temp,
                pad_token_id=pipe.model.config.eos_token_id,
                num_return_sequences=1,
            )
            if out and len(out) > 0 and "generated_text" in out[0]:
                return out[0]["generated_text"].strip()
            # Fallback if output structure differs
            return prompt
        except Exception as e:
            logger.exception("Error generating text: %s", e)
            return ""

    def is_loaded(self) -> bool:
        """Return True if the model has already been loaded into memory."""
        return self._pipeline is not None
