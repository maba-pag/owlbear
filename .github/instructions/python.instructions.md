---
applyTo: "**/*.py"
description: "Python coding conventions for this workspace."
---

# Python Conventions

## Package management

- Use `uv` — never bare `pip`. Run scripts with `uv run` (e.g., `uv run pytest`, `uv run ruff check`).
- Install deps: `uv sync` (reads `pyproject.toml`).

## Code style

- **ruff** for linting and formatting (config in `pyproject.toml`). Run `uv run ruff check` and `uv run ruff format --check`.
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

## Patterns

- **tenacity** for retry logic: exponential backoff, jitter, max 5 attempts.
- **Typer** for CLI commands (BearClaw entry point: `bearclaw.cli:app`).
- **PydanticAI** agents with structured output and dependency injection.
- GitHub Copilot OAuth — see `src/owlbear/config.py` for provider settings.
