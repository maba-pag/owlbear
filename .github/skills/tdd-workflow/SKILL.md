---
name: tdd-workflow
description: "TDD implementation workflow: read AC → write failing tests → implement → verify → advance. Use when building features or fixing bugs with test-driven development."
---

# TDD Workflow

Step-by-step process for implementing a kanban task using test-driven development.

## Step 1 — Read the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. `kanban\kanban-md.exe move {id} in-progress`
3. Read referenced source files to understand existing code
4. Initialize `manage_todo_list` with implementation steps

## Step 2 — Plan the change

Before writing any code, articulate:

- **What will change** — which files, functions, interfaces
- **Expected behavior** — what the code should do when complete
- **What could go wrong** — edge cases, breaking changes, import cycles

## Step 3 — Write failing tests (RED)

Create or extend `tests/test_{module}.py`:

- Cover every AC line from the kanban task
- Test happy path and edge cases
- Use `unittest.mock.patch` / `MagicMock` for external dependencies
- Follow existing test file patterns in the project

Run and verify they **fail**:

```powershell
uv run pytest tests/test_{module}.py -v --tb=short
```

## Step 4 — Implement minimal code (GREEN)

Write the minimum code to make all tests pass:

- Follow existing module patterns
- `from __future__ import annotations` at top
- Type hints on all function signatures
- Functions under ~50 lines
- Docstrings on public classes and functions

Run and verify they **pass**:

```powershell
uv run pytest tests/test_{module}.py -v --tb=short
```

## Step 5 — Refactor (if needed)

Only refactor code you just wrote:

- Remove duplication within your change
- Improve naming if unclear
- Split functions if too long
- Do NOT refactor unrelated code

## Step 6 — Verify

Run the full verification suite:

```powershell
uv run pytest tests/ -m "not api" --tb=short -q
uv run ruff check src/ tests/
```

Both must pass. Target ≥ 90% coverage on touched modules.

## Step 7 — Advance

```powershell
kanban\kanban-md.exe move {id} review
```

## Verification checklist

- [ ] Tests written BEFORE implementation (saw them fail)
- [ ] Implementation is the minimum code to pass all tests
- [ ] `pytest` all pass, `ruff` clean
- [ ] Coverage ≥ 90% on touched modules
- [ ] No unrelated files edited
- [ ] Diff is surgical — smallest change that achieves the AC
- [ ] `from __future__ import annotations` on new files
- [ ] Type hints on all signatures, docstrings on public API
