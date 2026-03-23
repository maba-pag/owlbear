---
applyTo: "**/*.py"
description: "Python coding conventions for this workspace."
---

# Python Conventions

## Package management

- Use `uv` — never bare `pip`. Run scripts with `uv run` (e.g., `uv run pytest`, `uv run ruff check`).
- Install deps: `uv sync --all-extras` (reads `pyproject.toml`). **Never bare `uv sync`** — dev dependencies (pytest, ruff, coverage) are declared as extras and get removed without `--all-extras`.

## Code style

- **ruff** for linting and formatting (config in `pyproject.toml`). Run `uv run ruff check` and `uv run ruff format --check`.
- **Docstrings:** Google convention enforced by ruff D rules (D2xx/D3xx/D4xx). D1xx (missing-docstring rules) are not yet enforced. Write Google-style docstrings (`Args:`, `Returns:`, `Raises:`) on all public classes and functions. Use raw-string docstrings (`r"""…"""`) only when the content contains backslash escape sequences.
- Type hints on all function signatures. Use `from __future__ import annotations` for modern syntax.
- Pylance strict mode for type checking.
- Pydantic `BaseModel` / `BaseSettings` for structured data and config.

## Project layout

- Source: `src/owlbear/` (namespace package, `__init__.py` in each subpackage).
- Tests: `tests/` mirroring `src/` structure (e.g., `tests/test_config.py` for `src/owlbear/config.py`).

## Testing

- **pytest** with `pytest-asyncio` for async tests.
- TDD by default — write the test first.
- Target >= 90 % coverage per phase gate.
- Use `unittest.mock.patch` / `MagicMock` for external dependencies (LLM calls, DB).
- For pytest/ruff/coverage **commands**, see the `pytest-and-linting` skill.

### Known gotchas

- **Pydantic v2 + MagicMock:** `MagicMock(spec=PydanticModel)` cannot auto-generate Pydantic v2 fields (`hasattr` returns `False` at class level). Explicitly set every accessed field on the mock: `mock_settings.field_name = value`.
- **Schema version bumps:** When bumping `_SCHEMA_VERSION`, grep all test files for the old version (`Select-String -Path "tests/*.py" -Pattern "_SCHEMA_VERSION"`) and update every assertion. Common breakage: `assert db.version == N`, fresh-database version checks.
- **`patch.dict("sys.modules")` on Python 3.12+:** Copies the entire dict on entry and restores on exit. Modules first imported inside the context are removed when it exits. Pre-import needed modules at file scope. Prefer `patch("module.attr")` over `patch.dict("sys.modules")`.

## Patterns

- **tenacity** for retry logic: exponential backoff, jitter, max 3 attempts.
- **Typer** for CLI commands (BearClaw entry point: `bearclaw.cli:app`).
- **PydanticAI** agents with structured output and dependency injection.
- GitHub Copilot OAuth — see `src/owlbear/config.py` for provider settings.
