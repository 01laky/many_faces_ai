"""Load shared moderation sanitize vectors from monorepo fixtures (AIH1-D7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class SanitizeVector(TypedDict, total=False):
    id: str
    title: str
    body: str
    mediaUrl: str | None
    notes: str
    expectStrippedOrdinals: bool
    expectControlCharsStripped: bool


def monorepo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def corpus_path() -> Path:
    return monorepo_root() / "docs" / "fixtures" / "moderation_sanitize_vectors.json"


def load_moderation_sanitize_vectors() -> list[SanitizeVector]:
    data: dict[str, Any] = json.loads(corpus_path().read_text(encoding="utf-8"))
    vectors = data.get("vectors")
    if not isinstance(vectors, list):
        raise ValueError("moderation_sanitize_vectors.json: missing vectors array")
    return vectors
