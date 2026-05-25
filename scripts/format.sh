#!/usr/bin/env bash
# Apply Ruff format (tabs per pyproject.toml [tool.ruff.format]).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v ruff >/dev/null 2>&1; then
	ruff format .
elif [ -f ".venv-lint/bin/ruff" ]; then
	.venv-lint/bin/ruff format .
else
	python3 -m ruff format .
fi

echo "✅ many_faces_ai format complete"
