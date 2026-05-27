"""Deterministic moderation decision explanation (AI-UP18)."""

from __future__ import annotations

import json
from typing import Any


def explain_decision(
	trace_id: str, decision_snapshot_json: str
) -> tuple[dict[str, Any] | None, str | None]:
	tid = (trace_id or "").strip()
	raw = (decision_snapshot_json or "").strip()
	if not tid:
		return None, "trace_id is required"
	if not raw:
		return None, "decision_snapshot_json is required"
	if len(raw.encode("utf-8")) > 64_000:
		return None, "decision_snapshot_json too large"

	try:
		snap = json.loads(raw)
	except json.JSONDecodeError:
		return None, "invalid decision_snapshot_json"

	if not isinstance(snap, dict):
		return None, "snapshot must be object"

	if str(snap.get("trace_id", "")).strip() and str(snap.get("trace_id")).strip() != tid:
		return None, "trace_id mismatch"

	path = str(snap.get("decision_path") or snap.get("path") or "rules")
	flags = snap.get("flags") if isinstance(snap.get("flags"), list) else []
	reason = str(snap.get("reason") or "No reason recorded.")
	excerpt = str(snap.get("sanitized_excerpt") or "")[:500]

	return {
		"path": path,
		"flags": [str(f) for f in flags if f],
		"reason": reason[:2000],
		"sanitized_excerpt": excerpt,
		"model_version": str(snap.get("model_version") or "explain-v1"),
	}, None
