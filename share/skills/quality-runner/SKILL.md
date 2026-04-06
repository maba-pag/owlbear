---
name: quality-runner
description: "Handbook: Quality-Runner subagent — consumer invocation pattern, I/O contract, and fallback"
user-invocable: false
---

# Quality-Runner Subagent

Consumer reference for invoking the `quality-runner` utility subagent. Quality-Runner runs pytest, ruff, and coverage, returning a structured report. It is a mechanical utility agent — it does not edit files, interact with kanban, or make judgments.

## Consumer Invocation Pattern

Invoke via `runSubagent` with a structured prompt:

```
agentName: quality-runner
prompt: |
  Run: mode=scoped, task_id=263, test_paths=["tests/test_my_module.py"], coverage_modules=["my_module"], lint_paths=["serve/my-package/", "tests/test_my_module.py"]
```

Full-suite example:

```
agentName: quality-runner
prompt: |
  Run: mode=full, task_id=263
```

**Prerequisite:** The calling agent must list `quality-runner` in its frontmatter `agents:` array. Without this, `disable-model-invocation: true` blocks the call.

```yaml
# In the calling agent's frontmatter:
agents: [quality-runner]
```

## Input Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | `scoped` \| `full` | Yes | `scoped` runs only `test_paths`; `full` runs `tests/ serve/ -m "not api"` |
| `test_paths` | string[] | If `mode=scoped` | Paths to test files, e.g. `["tests/test_foo.py", "tests/test_bar.py"]` |
| `task_id` | string | Yes | Kanban task ID — isolates file-capture fallback output in `.owlbear/scratch/` |
| `coverage_modules` | string[] | No | Module names for focused coverage display; bare `--cov` always runs against all packages |
| `lint_paths` | string[] | No | Paths to lint; defaults to `serve/ tests/` if omitted |

## Output Format

Quality-Runner returns exactly 5 sections. Parse all 5 before taking action.

```
## Tests
passed: 42
failed: [{name: "test_foo::TestBar::test_baz", error: "AssertionError: expected 1 got 0"}]
skipped: 2

## Lint
clean: false
violations: [{file: "serve/foo/src/foo/bar.py", line: 12, code: "F401", msg: "'os' imported but unused"}]

## Coverage
overall_pct: 94
modules: [{name: "foo.bar", pct: 87}, {name: "foo.baz", pct: 100}]

## Exit Codes
pytest: 1
ruff: 1

## Errors
none
```

**Exit code interpretation:**

| pytest exit | Meaning |
|-------------|---------|
| 0 | All tests passed |
| 1 | Tests failed |
| 2 | Interrupted |
| 3 | Internal error |
| 4 | Command-line usage error |
| 5 | No tests collected |

## Fallback: Quality-Runner Unavailable

If Quality-Runner is unavailable (not listed in the calling agent's `agents:` array, or subagent dispatch fails), callers should run quality checks directly per the `h-pytest-and-linting` skill:

```powershell
# Scoped
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
uv run ruff check serve/ tests/

# Full suite (use isBackground=true)
uv run pytest tests/ serve/ -m "not api" -q --tb=short
uv run ruff check serve/ tests/
```

Parse terminal output manually and apply the pitfall mitigations from `h-pytest-and-linting` directly.
