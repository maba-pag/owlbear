---
name: h-python-conventions
description: "Handbook: Python coding conventions for the OwlBear workspace"
user-invocable: false
---

# Python Conventions

## Package Management

- Use `uv` — never bare `pip`. Run repository checks with `uv run --locked` once dependency inputs
  and their lockfile are current; a dependency-changing task generates its required lockfile before
  locked proof. Use `uv run` for scripts that do not resolve project dependencies.
- Install the complete development environment with `uv sync --locked --all-packages --all-extras --all-groups` (reads the workspace manifests and lockfile). Never rely on bare `uv sync` for repository checks.

## Code Style

- **ruff** for linting and formatting (config in `pyproject.toml`). Run `uv run ruff check` and `uv run ruff format --check`.
- **Docstrings:** Google convention enforced by ruff D rules (D2xx/D3xx/D4xx). D1xx (missing-docstring) not yet enforced. Use `r"""…"""` only when the content contains backslash sequences.
- Type hints on all function signatures. Use `from __future__ import annotations` for modern syntax.
- Pylance strict mode for type checking.
- Pydantic `BaseModel` / `BaseSettings` for structured data and config.

## Testing

- **pytest** with `pytest-asyncio` for async tests.
- Use `unittest.mock.patch` / `MagicMock` for external dependencies (LLM calls, DB).
- Configure `testpaths` for the repository's actual root and package-local test directories.
- Use `--import-mode=importlib` through pytest configuration for monorepo-safe test imports.
- For test/lint **commands and flags**, see the `h-pytest-and-linting` skill.

### Proof Is Not Automatically a Test

Choose the cheapest evidence that exercises the claimed boundary. A search, diff, lint, typecheck,
import smoke, build, command invocation, or manual inspection can be valid task proof without
becoming a committed pytest test.

Use task proof instead of a durable test when checking only that:

- deleted text, an import, a file, or an old symbol is absent;
- a file, configuration key, dependency, export, or literal string exists;
- source text has a particular shape or wording;
- a formatter, linter, type checker, package builder, or framework validator accepts the change.

These checks freeze a change rather than protect product behavior. A structural artifact warrants a
durable test only when the artifact itself is a maintained public contract and no cheaper owning tool
validates it.

### Durable Test Admission

Create or retain a durable test only when it passes the pipeline Rent Test and protects at least one
of these:

- observable behavior or a public interface used by callers;
- a non-obvious invariant or edge case that is hard to re-derive;
- a realistic error, concurrency, security, migration, or data-loss boundary;
- a previously observed bug with meaningful recurrence risk;
- a shared path whose regression would be expensive or difficult to notice manually.

A durable test must be cheaper to understand and maintain than repeated verification of the risk it
protects. Do not add a test solely to raise coverage, mirror an acceptance-criteria sentence, or
preserve an implementation detail.

### Assertion Quality

- Exercise meaningful input and assert observable output, state, error, or side effect.
- Ask which plausible regression would make the test fail. If there is no behavioral answer, choose
  another proof mode or remove the test.
- Add negative, boundary, or alternate cases only when they distinguish the contract from a common
  incorrect implementation.
- Test through the same public boundary callers use. Mocks and fakes may replace lower external
  dependencies, but not the function, command, endpoint, workflow, or assembly being claimed.
- For small tools and CLIs, prefer command or public-function input/output tests with temporary
  files and state over assertions about internal source structure.
- Prefer a small set of discriminating assertions with clear behavioral ownership over exhaustive
  implementation coverage.

Coverage is a diagnostic for unexamined code, not a proxy for test value or product correctness.
Honor explicit project or CI thresholds, but never manufacture low-value assertions to reach them.

### Test Lifecycle and Placement

| Tier | File naming | Lifespan | Authority |
| --- | --- | --- | --- |
| **Task-scoped proof** (transient) | Project test root with task ID when executable scaffolding is necessary | Until task archive | Proves task completion; test-curator deletes it or mines behavior worth retaining. |
| **Durable behavioral test** | Owning package or configured test root, named for behavior | While the protected contract exists | Maintained regression suite for product behavior and risk boundaries. |

- Discover durable locations from pytest `testpaths`, package manifests, and the nearest existing test
  for the owning behavior; do not assume a repository root such as `serve/` or `src/`.
- Task-scoped executable scaffolding is exceptional, not the default proof for every change. After
  archive, the test-curator removes it or mines only assertions that pass Durable Test Admission.
- Durable test names describe behavior or risk, not task IDs or acceptance-criteria numbering.
- Builder and independent proof roles run commands proportional to packet and change risk. There is no mandatory GREEN phase or coverage target.

## Known Gotchas

- **Pydantic v2 + MagicMock:** `MagicMock(spec=PydanticModel)` cannot auto-generate Pydantic v2 fields. Explicitly set every accessed field on the mock.
- **Schema version bumps:** Search all test files for old version and update every assertion.
- **`patch.dict("sys.modules")` on Python 3.12+:** Modules first imported inside the context are removed when it exits. Pre-import needed modules at file scope. Prefer `patch("module.attr")`.

## Patterns

- **tenacity** for retry logic: exponential backoff, jitter, and a bounded attempt count appropriate
  to the dependency contract.
- **Typer** for CLI commands unless a project explicitly selects another CLI framework.
