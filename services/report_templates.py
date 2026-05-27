"""Structured admin report templates (AI-UP11)."""

from __future__ import annotations

import json
from typing import Any

SUPPORTED_REPORT_TYPES = frozenset({"face_health", "moderation_backlog", "grid_completeness"})
SCHEMA_VERSION = "report-v1"


def generate_report_markdown(
	report_type: str, report_locale: str, input_json: str
) -> tuple[str, str, str | None]:
	rt = (report_type or "").strip().lower()
	if rt not in SUPPORTED_REPORT_TYPES:
		return "", "", f"unsupported report_type {report_type!r}"

	raw = (input_json or "").strip()
	if not raw:
		return "", "", "input_json is required"
	if len(raw.encode("utf-8")) > 128_000:
		return "", "", "input_json too large"
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		return "", "", "invalid input_json"
	if not isinstance(data, dict):
		return "", "", "input_json root must be object"

	locale = (report_locale or "en").strip().lower() or "en"
	title = _title_for(rt, locale)
	sections = _sections_for(rt, data)
	md_lines = [f"# {title}", ""]
	for heading, body in sections:
		md_lines.append(f"## {heading}")
		md_lines.append(body)
		md_lines.append("")

	report_json = json.dumps(
		{"reportType": rt, "locale": locale, "sections": len(sections)}, ensure_ascii=False
	)
	return "\n".join(md_lines).strip(), report_json, None


def _title_for(report_type: str, locale: str) -> str:
	titles = {
		"face_health": {"en": "Face health report", "sk": "Správa o stave face"},
		"moderation_backlog": {"en": "Moderation backlog", "sk": "Moderácia — backlog"},
		"grid_completeness": {"en": "Grid completeness", "sk": "Kompletnosť gridu"},
	}
	return titles.get(report_type, {}).get(locale) or titles.get(report_type, {}).get(
		"en", report_type
	)


def _sections_for(report_type: str, data: dict[str, Any]) -> list[tuple[str, str]]:
	if report_type == "face_health":
		face = data.get("face") if isinstance(data.get("face"), dict) else {}
		return [
			("Summary", f"Face **{face.get('title', '?')}** — public={face.get('isPublic', '?')}."),
			(
				"Pages",
				f"{data.get('pageCount', len(data.get('pages') or []))} configured pages.",
			),
		]
	if report_type == "moderation_backlog":
		return [
			("Queue", f"Pending items: {data.get('pendingCount', 0)}."),
			("Oldest", f"Oldest pending age (hours): {data.get('oldestHours', 'n/a')}."),
		]
	return [
		("Grid", f"Component types present: {data.get('componentTypeCount', 0)}."),
		("Gaps", ", ".join(data.get("missingTypes") or []) or "None listed."),
	]
