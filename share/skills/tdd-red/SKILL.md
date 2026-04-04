---
name: tdd-red
description: "Workflow: TDD RED phase — write failing tests from acceptance criteria"
user-invocable: false
---

# TDD RED Phase

Write failing tests from a task's acceptance criteria. All tests must fail when complete. See `w-tdd-red` for the full test-writer workflow.

## Step 1 — Assess Task Type

Check if this is a non-implementation task (tagged `research`, `docs`, `test`, etc.). If so, pass through to builder with a note. Otherwise, identify referenced source files, modules, and interfaces in the AC.

## Step 2 — Write Tests

Create `tests/test_{module}.py` with `TestFromAC_{Feature}` class. Each AC line gets at least one test.

## Step 3 — Verify RED

Confirm every test fails via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  lint_paths: ["tests/test_{module}.py"]
```

Confirm all tests appear in `failed:` list and `clean: true` in the Quality-Runner report.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run ruff check tests/test_{module}.py
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 4 — Advance

Append test summary to task body via `edit_task` (with `append_body` and `timestamp=True`), then advance via `end_work`.
