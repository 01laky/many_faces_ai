"""Ensure repo root is on ``sys.path`` for scripts and tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_repo_root_on_path() -> Path:
	root = str(ROOT)
	if root not in sys.path:
		sys.path.insert(0, root)
	return ROOT
