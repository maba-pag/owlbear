---
name: tdd-red
description: "TDD RED phase workflow: read AC → search codebase → plan test categories → write failing tests → verify all fail. Used by test-writer agent."
---

# TDD RED Phase Workflow

Step-by-step process for the test-writer to produce failing tests from a task's acceptance criteria. This is the RED phase of TDD — all tests must fail when complete.

## Step 1 — Read the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. Identify referenced source files, modules, and interfaces in the AC
3. Do NOT move task status yet — movement happens in Step 7 after all tests are verified

## Step 2 — Search codebase

Find interfaces, types, and existing patterns referenced in the AC:

- Read source files to understand function signatures, data structures, error types
- Check existing `conftest.py` files for reusable fixtures
- Source files are **read-only** — never create or edit files in `src/`

## Step 3 — Plan test categories

Map each AC line to test categories:

- **Happy path** — the expected behavior works correctly
- **Edge cases** — empty inputs, boundary values, concurrent access
- **Error paths** — invalid inputs, missing dependencies, expected exceptions
- **Boundary conditions** — limits, thresholds, off-by-one scenarios

Use `manage_todo_list` to track AC-to-test mapping and progress.

## Step 4 — Write tests

Create or extend `tests/test_{module}.py` with class `TestFromAC_{Feature}`:

- Each AC line gets at least one test
- Test the **contract** described in AC, not a specific implementation
- Use `unittest.mock.patch` / `MagicMock` for external dependencies
- `from __future__ import annotations` at top of new files
- Type hints on test helper functions
- Read existing test files only for project conventions (imports, fixtures, conftest usage) — not for test logic

**Class naming convention:**

- `TestFromAC_{Feature}` — tests written by the test-writer from AC
- Never use `TestBuilderDiscovered` — that is the builder's convention

## Step 5 — Verify RED

Run pytest on your test file and confirm **every** test fails:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

**Expected failure types:**

- `ImportError` — module or function does not exist yet
- `NotImplementedError` — stub exists but is not implemented
- `AssertionError` — assertion against unimplemented behavior

**Unexpected failure types (fix these):**

- `SyntaxError` — bug in your test code, fix it before completing
- Any test that **passes** — the implementation already exists for that behavior; remove the test or make it more specific to new behavior

Then run ruff on your test file:

```powershell
uv run ruff check tests/test_{module}.py
```

Must be clean — no lint errors.

## Step 6 — Append summary

Write a test summary to the kanban task body:

```powershell
kanban\kanban-md.exe edit {id} -a "## Test-Writer Notes
- Test file: tests/test_{module}.py
- Classes: {list of TestFromAC_ classes}
- Tests per category: happy {h}, edge {e}, error {r}, boundary {b}
- Total: {N} tests, all FAIL ✓
- ruff: clean" -t
```

## Step 7 — Advance

Move the task to `in-progress` to signal the builder:

```powershell
kanban\kanban-md.exe move {id} in-progress
```

## Verification checklist

- [ ] Every AC line has at least one test
- [ ] All tests are contract-level (no implementation assumptions)
- [ ] `TestFromAC_{Feature}` naming on all test classes
- [ ] `pytest` confirms all tests FAIL (ImportError, NotImplementedError, or AssertionError)
- [ ] No `SyntaxError` failures
- [ ] `ruff` clean on test file
- [ ] No source files created or edited
- [ ] `from __future__ import annotations` on new files
- [ ] Summary appended to task body
- [ ] Task moved to `in-progress`
