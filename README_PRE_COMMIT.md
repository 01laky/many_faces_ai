# pre-commit (Python) — many_faces_ai

This project uses the **pre-commit** framework for Python code quality checks (not Husky; see **many_faces_portal** / **many_faces_admin** for Yarn + Husky examples).

## Installation

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install git hooks
pre-commit install
```

## What it does

The pre-commit hooks run automatically before each commit and check:

1. **Trailing whitespace** - Removes trailing whitespace
2. **End of file** - Ensures files end with newline
3. **YAML/JSON/TOML validation** - Validates config files
4. **Large files** - Prevents committing files > 1MB
5. **Merge conflicts** - Detects merge conflict markers
6. **Private keys** - Detects accidentally committed private keys
7. **Black** - Formats Python code (line length: 100)
8. **Ruff** - Lints Python code (fast, replaces flake8)

## Manual execution

Run all hooks on all files:

```bash
pre-commit run --all-files
```

Run specific hook:

```bash
pre-commit run black --all-files
pre-commit run ruff --all-files
```

## Update hooks

```bash
pre-commit autoupdate
```

## Skip hooks (not recommended)

Skip hooks for a single commit:

```bash
git commit --no-verify
```

## Configuration

Configuration is in `.pre-commit-config.yaml`:

- **Black**: Code formatter (line length: 100)
- **Ruff**: Fast linter (replaces flake8, pylint, isort)

Additional configuration is in `pyproject.toml` for Black and Ruff settings.

## Tools used

- **Black** - Uncompromising Python code formatter
- **Ruff** - Fast Python linter (10-100x faster than flake8)
- **pre-commit hooks** - General file checks (trailing whitespace, etc.)
