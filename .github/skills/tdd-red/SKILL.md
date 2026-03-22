---
name: tdd-red
description: "TDD RED phase workflow: read AC → search codebase → plan test categories → write failing tests → verify all fail. Used by test-writer agent."
---

# TDD RED Phase Workflow

Step-by-step process for the test-writer to produce failing tests from a task's acceptance criteria. This is the RED phase of TDD — all tests must fail when complete.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append summary | `kanban\kanban-md.exe edit {id} -a "## Test-Writer Notes\n{content}" -t --claim <agent>` |
| Advance | `kanban\kanban-md.exe edit {id} --status in-progress --release` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Read and claim the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)
3. Check if this is a **non-implementation task** (tagged `research`, `docs`, `type:config`, or `type:docs`). If so, go to **Step 1a — Pass-through**.
4. Check if this is a **retry cycle** (task body contains both `## Test-Writer Notes` and `## Review Evidence`). If so, go to **Step 1b — Retry-cycle handling**.
5. Identify referenced source files, modules, and interfaces in the AC
6. Do NOT move task status yet — movement happens in Step 7 after all tests are verified

### Step 1a — Pass-through for non-implementation tasks

Some tasks don't have testable implementation (research, documentation, config). When
you encounter one:

1. Append a brief note to the task body:

   ```powershell
   kanban\kanban-md.exe edit {id} -a "## Test-Writer Notes\n- Non-implementation task (tagged {tag}) — no tests applicable.\n- Passing through to builder." -t
   ```

2. Advance + release: `kanban\kanban-md.exe edit {id} --status in-progress --release`
3. Return the signal:

   ```
   DONE #{id} -> in-progress | non-impl pass-through, no tests needed
   ```

4. **Stop here.** Do not proceed to Step 2.

### Step 1b — Retry-cycle handling

If the task body already contains **both** `## Test-Writer Notes` and `## Review Evidence`,
this is a retry cycle (reviewer FAILed the task back to `todo`). Do NOT re-run the
normal RED phase — the existing tests are valid artifacts from the prior cycle.

1. Read the `## Review Evidence` section to understand **why** the reviewer failed it.
2. **If the reviewer cites missing tests** (MISSING in coverage table, untested paths
   in implementation-aware analysis):
   - Write NEW failing tests addressing those specific gaps.
   - Add them to the existing `TestFromAC_{Feature}` class (or a new `TestFromAC_` class
     for a distinct AC concern).
   - Do NOT remove or modify existing passing tests — they are correct from the prior cycle.
   - Run pytest to verify: old tests PASS, new tests FAIL.
   - Append an update to the task body:

     ```powershell
     kanban\kanban-md.exe edit {id} -a "## Test-Writer Notes (retry)\n- Retry reason: reviewer cited missing tests\n- Added: {N} new failing tests for: {gap summary}\n- Preserved: {M} existing tests (all PASS)" -t
     ```

3. **If the reviewer cites code quality, weak tests, or security** (not missing tests):
   pass through without changes — the builder will address the findings. Append:

   ```powershell
   kanban\kanban-md.exe edit {id} -a "## Test-Writer Notes (retry)\n- Retry reason: reviewer FAIL was about {code quality / weak tests / security}, not missing tests.\n- Existing tests preserved. Builder will address reviewer findings." -t
   ```

4. Advance + release: `kanban\kanban-md.exe edit {id} --status in-progress --release`
5. Return: `DONE #{id} -> in-progress | retry, {N} existing tests preserved{, M new tests added}`
6. **Stop here.** Do not proceed to Step 2.

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

## Step 7 — Advance + release

Advance the task to `in-progress` and release the claim in one atomic command:

```powershell
kanban\kanban-md.exe edit {id} --status in-progress --release
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
- [ ] Task advanced to `in-progress` and claim released via `edit {id} --status in-progress --release`
