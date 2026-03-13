---
name: tdd-workflow
description: "TDD GREEN phase workflow: read existing tests → verify they fail → implement → verify → advance. Use when building features or fixing bugs with test-driven development."
---

# TDD Workflow

Step-by-step process for implementing a kanban task using test-driven development.

## Step 1 — Read and claim the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)
3. Verify task is in `in-progress` status (the test-writer already moved it here)
4. Read referenced source files to understand existing code
5. Initialize `manage_todo_list` with implementation steps

### Step 1a — Pass-through for non-implementation tasks

Check the task body for `## Test-Writer Notes` containing "Non-implementation task" or
"non-impl pass-through". If found:

1. Append a brief note to the task body:
   ```powershell
   kanban\kanban-md.exe edit {id} -a "## Builder Notes\n- Non-implementation task — no code changes needed.\n- Passing through to review." -t
   ```
2. Advance + release: `kanban\kanban-md.exe edit {id} --status review --release`
3. Return: `DONE #{id} -> review | non-impl pass-through, no code changes`
4. **Stop here.** Do not proceed to Step 2.

## Step 2 — Plan the change

Before writing any code, articulate:

- **What will change** — which files, functions, interfaces
- **Expected behavior** — what the code should do when complete
- **What could go wrong** — edge cases, breaking changes, import cycles

## Step 3 — Read existing tests

The test-writer has already created `TestFromAC_*` classes in `tests/test_{module}.py`.
Your job is to understand what they expect and make them pass.

1. Read the test file — identify every `TestFromAC_*` class
2. Extract the expected interfaces: function signatures, class names, error types,
   return values, and import paths the tests assume
3. Plan your implementation approach based on these interfaces

Verify all `TestFromAC_*` tests currently **fail**:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

Expect failures. If any `TestFromAC_*` tests already pass, something already exists —
investigate before implementing.

> **Backward compatibility:** When no `TestFromAC_*` classes exist (old-style
> single-agent TDD or standalone builder work), fall back to the full RED+GREEN
> workflow — write failing tests yourself, then implement.

## Step 4 — Implement minimal code (GREEN)

Write the minimum code to make all tests pass:

- Follow existing module patterns
- `from __future__ import annotations` at top
- Type hints on all function signatures
- Functions under ~50 lines
- Docstrings on public classes and functions

Run and verify they **pass**:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

Expect all tests passing, zero failures.

## Step 5 — Add builder-discovered tests (optional)

During implementation you may discover edge cases not covered by the test-writer's
`TestFromAC_*` tests. You may add these in a **separate** `TestBuilderDiscovered` class
in the same test file. Never add them to `TestFromAC_*` classes.

Each builder-discovered test must follow RED-GREEN within this step:

1. Write the test in `TestBuilderDiscovered` — verify it **fails**
2. Implement the fix — verify it **passes**

This step is optional. Skip it if the `TestFromAC_*` tests already cover the behavior
adequately.

## Step 6 — Refactor (if needed)

Only refactor code you just wrote:

- Remove duplication within your change
- Improve naming if unclear
- Split functions if too long
- Do NOT refactor unrelated code

## Step 7 — Verify

Run the verification suite. **Always scope test runs** — the full suite has hundreds of
tests and will time out.

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
uv run ruff check src/ tests/
```

Run plain — never pipe through PS cmdlets. See the `pytest-and-linting` skill
(read it with `read_file` if not already loaded)
for the full rules. If coverage measurement fails,
re-read that section before retrying — do NOT iterate through flag variations.

All must pass. Target ≥ 90% coverage on touched modules.

## Step 8 — Advance + release

Advance the task to `review` and release the claim in one atomic command:

```powershell
kanban\kanban-md.exe edit {id} --status review --release
```

## Verification checklist

- [ ] Test-writer's `TestFromAC_*` tests verified as failing before implementation
- [ ] All `TestFromAC_*` tests pass after implementation
- [ ] No `TestFromAC_*` classes modified
- [ ] Any builder-added tests are in `TestBuilderDiscovered` class
- [ ] Implementation is the minimum code to pass all tests
- [ ] `pytest` all pass, `ruff` clean
- [ ] Coverage ≥ 90% on touched modules
- [ ] No unrelated files edited
- [ ] Diff is surgical — smallest change that achieves the AC
- [ ] `from __future__ import annotations` on new files
- [ ] Type hints on all signatures, docstrings on public API
