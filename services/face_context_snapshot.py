"""Face context snapshot formatter (AI-UP3)."""

from __future__ import annotations

import json

MAX_SNAPSHOT_BYTES = 256_000
SUPPORTED_SCHEMA_MAJOR = 1


def build_face_context_snapshot(snapshot_json: str) -> tuple[str, str, list[str], str | None]:
	raw = (snapshot_json or "").strip()
	if not raw:
		return "", "", [], "snapshot_json is required"
	if len(raw.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
		return "", "", [], "snapshot_json too large"

	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		return "", "", [], "invalid snapshot_json"

	if not isinstance(data, dict):
		return "", "", [], "snapshot root must be object"

	schema_version = str(data.get("schemaVersion", "1.0"))
	major = _schema_major(schema_version)
	if major is None or major > SUPPORTED_SCHEMA_MAJOR:
		return "", "", [], f"unsupported schemaVersion {schema_version}"

	warnings: list[str] = []
	face = data.get("face") if isinstance(data.get("face"), dict) else {}
	pages = data.get("pages") if isinstance(data.get("pages"), list) else []
	modules = data.get("contentModules") if isinstance(data.get("contentModules"), dict) else {}
	integration = data.get("integration") if isinstance(data.get("integration"), dict) else {}

	if not pages:
		warnings.append("no pages in snapshot")
	if not modules:
		warnings.append("contentModules missing")

	lines = [
		"# Face context (read-only)",
		f"Face: {face.get('title', '(unknown)')} (public={face.get('isPublic', '?')})",
		f"Pages ({len(pages)}):",
	]
	for page in pages[:40]:
		if isinstance(page, dict):
			lines.append(
				f"  - {page.get('index', '?')} type={page.get('pageType', '?')} components={page.get('componentCount', 0)}"
			)
	grid_types = data.get("gridComponentTypes")
	if isinstance(grid_types, list) and grid_types:
		lines.append(f"Grid component types: {', '.join(str(x) for x in grid_types[:30])}")
	enabled = modules.get("enabled") if isinstance(modules.get("enabled"), list) else []
	if enabled:
		lines.append(f"Enabled modules: {', '.join(str(x) for x in enabled)}")
	if integration:
		lines.append(
			"Integration: "
			+ ", ".join(
				f"{k}={integration[k]}" for k in sorted(integration.keys()) if k in integration
			)
		)

	formatted = "\n".join(lines)
	return formatted, schema_version, warnings, None


def _schema_major(version: str) -> int | None:
	parts = version.split(".", 1)
	try:
		return int(parts[0])
	except ValueError:
		return None
