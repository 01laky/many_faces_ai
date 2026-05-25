"""Deterministic stitch v1 (mirrors backend OperatorAiLiveStatsStitch)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class StitchedPart:
	index: int
	bundle_id: str
	text: str
	failed: bool


def stitch_bundle_answers(parts: Iterable[StitchedPart]) -> str:
	"""Merge per-bundle sub-answers into one operator-visible message."""
	ordered = sorted(parts, key=lambda p: p.index)
	if not ordered:
		return "No statistics data was available to answer this question."

	blocks: list[str] = []
	for part in ordered:
		if part.failed:
			blocks.append(f"**{part.bundle_id}:** Data unavailable for this bundle.")
			continue
		if not (part.text or "").strip():
			blocks.append(f"**{part.bundle_id}:** No answer generated.")
			continue
		blocks.append(f"**{part.bundle_id}:**\n{part.text.strip()}")

	return "\n\n".join(blocks).strip()
