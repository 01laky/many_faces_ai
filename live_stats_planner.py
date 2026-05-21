"""Planner index JSON salvage and parse (mirrors backend OperatorAiLiveStatsPlanner)."""

from __future__ import annotations

import json
import re
from typing import List

_FENCE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)


def salvage_json_object(text: str) -> str:
    """Extract the first JSON object from model output."""
    text = text.strip()
    m = _FENCE.search(text)
    if m:
        return m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def parse_planner_indices(
    model_output: str,
    catalog_length: int,
    max_selected: int,
    metrics_like: bool = True,
) -> List[int]:
    """Parse planner indices; fallback [0] when metrics-like and parse fails."""
    raw = salvage_json_object(model_output)
    try:
        data = json.loads(raw)
        indices = data.get("indices", [])
        if not isinstance(indices, list):
            raise ValueError("indices not list")
        out = sorted({int(i) for i in indices if isinstance(i, int) or str(i).isdigit()})
        out = [i for i in out if 0 <= i < catalog_length]
        if not out:
            return [0] if metrics_like else []
        return out[:max_selected]
    except (json.JSONDecodeError, ValueError, TypeError):
        return [0] if metrics_like else []
