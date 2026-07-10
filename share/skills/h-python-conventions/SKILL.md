---
name: h-python-conventions
description: "Handbook: Python coding conventions for the OwlBear workspace"
user-invocable: false
---

# Python Conventions

## Package Management

- Use `uv` — never bare `pip`. Run scripts with `uv run` (e.g., `uv run pytest`, `uv run ruff check`).
- Install deps: `uv sync --all-extras` (reads `pyproject.toml`). Never bare `uv sync` — dev dependencies (pytest, ruff, coverage) are declared as extras and get removed without `--all-extras`.

## Code Style

- **ruff** for linting and formatting (config in `pyproject.toml`). Run `uv run ruff check` and `uv run ruff format --check`.
- **Docstrings:** Google convention enforced by ruff D rules (D2xx/D3xx/D4xx). D1xx (missing-docstring) not yet enforced. Use `r"""…"""` only when the content contains backslash sequences.
- Type hints on all function signatures. Use `from __future__ import annotations` for modern syntax.
- Pylance strict mode for type checking.
- Pydantic `BaseModel` / `BaseSettings` for structured data and config.

## Testing

- **pytest** with `pytest-asyncio` for async tests.
- TDD by default — write the test first.
- Target ≥ 90% coverage per phase gate.
- Use `unittest.mock.patch` / `MagicMock` for external dependencies (LLM calls, DB).
- `testpaths`: `["tests", "packages"]` — both root and package-local tests discovered.
- `--import-mode=importlib` set via `addopts` in `pyproject.toml` — required for monorepo layout.
- For test/lint **commands and flags**, see the `h-pytest-and-linting` skill.

### Two-Tier Test Model

| Tier | File naming | Lifespan | Authority |
|------|------------|----------|-----------|
| **Task-scoped** (transient) | `tests/test_{module}_{task_id}.py` | Legacy/task artifact only | Created only when a task explicitly needs temporary proof. Test-curator removes or mines after archive. |
| **Module-level** (durable, canonical) | `serve/{package}/tests/test_{module}.py` | Permanent | Test-curator mines coverage gaps from task-scoped tests and writes new module-level assertions. |

- **Task-scoped tests** are scaffolding. They verify acceptance criteria for a single task and are removed by the test-curator after the task is archived.
- **Module-level tests** are the durable test suite. Canonical location is `serve/{package}/tests/test_{module}.py`. Existing root `tests/test_{module}.py` durable files are legacy until E2 migration.
- Builder/verifier run focused proof commands proportional to the task risk. There is no mandatory GREEN phase or coverage target.

## Known Gotchas

- **Pydantic v2 + MagicMock:** `MagicMock(spec=PydanticModel)` cannot auto-generate Pydantic v2 fields. Explicitly set every accessed field on the mock.
- **Schema version bumps:** Search all test files for old version and update every assertion.
- **`patch.dict("sys.modules")` on Python 3.12+:** Modules first imported inside the context are removed when it exits. Pre-import needed modules at file scope. Prefer `patch("module.attr")`.

## Patterns

- **tenacity** for retry logic: exponential backoff, jitter, max 3 attempts.
- **Typer** for CLI commands.
