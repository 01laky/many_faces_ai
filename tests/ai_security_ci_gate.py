"""AIH1 security CI gate — keep aligned with monorepo verify-ai-security-tests.mjs."""

from __future__ import annotations

from pathlib import Path

SECURITY_TEST_GLOB = "tests/**/*_security.py"


def security_test_files() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    return sorted(root.glob("tests/**/*_security.py"))
