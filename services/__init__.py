# services/__init__.py
# AI Demo services package.
# Exposes AIModelService for text generation using the local AI model.

from services.ai_model_service import AIModelService

__all__ = ["AIModelService"]
