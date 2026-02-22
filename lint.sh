#!/bin/bash

# Lint ai_demo (ruff check + ruff format --check)
# Usage: ./lint.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔍 Linting ai_demo..."
echo ""

# Use ruff if available (from venv or PATH)
if command -v ruff &>/dev/null; then
    ruff check .
    ruff format --check .
elif [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/ruff" ]; then
    "$VIRTUAL_ENV/bin/ruff" check .
    "$VIRTUAL_ENV/bin/ruff" format --check .
else
    PYTHON=""
    command -v python3 &>/dev/null && PYTHON="python3"
    command -v python &>/dev/null && PYTHON="${PYTHON:-python}"
    if [ -z "$PYTHON" ]; then
        echo "python/python3 not found. Install Python or use a venv with ruff."
        exit 1
    fi
    if ! $PYTHON -c "import ruff" 2>/dev/null; then
        # Try .venv-lint with ruff (created on first run)
        LINT_VENV=".venv-lint"
        if [ ! -d "$LINT_VENV" ]; then
            echo "Creating $LINT_VENV and installing ruff..."
            $PYTHON -m venv "$LINT_VENV" && "$LINT_VENV/bin/pip" install ruff -q
        fi
        if [ -f "$LINT_VENV/bin/ruff" ]; then
            "$LINT_VENV/bin/ruff" check .
            "$LINT_VENV/bin/ruff" format --check .
        else
            echo "ruff not installed. Install with: pip install ruff (or: pip install -r requirements.txt)"
            exit 1
        fi
    else
        $PYTHON -m ruff check .
        $PYTHON -m ruff format --check .
    fi
fi

echo ""
echo "✅ ai_demo lint passed"
