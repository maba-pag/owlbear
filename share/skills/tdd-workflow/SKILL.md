---
name: tdd-workflow
description: "Workflow: TDD workflow — full RED→GREEN cycle with Quality-Runner integration"
user-invocable: false
---

# TDD Workflow

Complete TDD cycle: write failing tests (RED), implement minimal code (GREEN), verify.

## Step 1 — RED Phase

Write failing tests from the acceptance criteria. See `w-tdd-red` for the full test-writer workflow.

## Step 2 — GREEN Phase

Implement the minimum code to make all tests pass. See `w-tdd-green` for the full builder workflow.

## Step 3 — Verify RED (Test-Writer)

Confirm all `TestFromAC_*` tests fail before implementation via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  lint_paths: ["tests/test_{module}.py"]
```

Confirm all tests appear in `failed:` list.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run ruff check tests/test_{module}.py
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 4 — Implement

Write the minimum code to make all tests pass. Follow existing module patterns.

## Step 5 — Verify GREEN (Builder)

Run the full verification suite via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/src/", "tests/test_{module}.py"]
```

All must pass (`failed: []`, `clean: true`). Target 90% coverage on touched modules.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
uv run ruff check serve/ tests/
```

See `h-pytest-and-linting` for exact flags and known pitfalls.

## Step 6 — Refactor

Only refactor code written in Step 4. Remove duplication, improve naming, split long functions.

## Step 7 — Confirm and Advance

Re-run Quality-Runner to confirm all tests still pass after refactoring:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/src/", "tests/test_{module}.py"]
```

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run ruff check serve/ tests/
```

See `h-pytest-and-linting` for exact flags and known pitfalls.

Advance via `end_work` when all tests pass and lint is clean.
