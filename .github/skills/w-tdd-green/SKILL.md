---
name: w-tdd-green
description: "Workflow: TDD GREEN phase — implement minimal code to pass failing tests"
user-invocable: false
---

# TDD GREEN Phase

Implement the minimum code to make all failing tests pass. This is the GREEN phase of TDD — the test-writer already wrote the RED tests.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

> **MCP equivalent:** `start_work(task_id="{id}")`

Verify the task is in `in-progress` status (the test-writer already moved it here).

### Step 0a — Non-Implementation Pass-Through

Check the task body for `## Test-Writer Notes` containing "Non-implementation task" or "non-impl pass-through". If found:

1. Append note via `edit_task` (with `append_body`): "## Builder Notes\n- Non-implementation task — no code changes needed.\n- Passing through to review."
   > **MCP equivalent:** `edit_task(task_id="{id}", append_body="## Builder Notes\n...", timestamp=True)`
2. Advance via `end_work` (moves to `review` + releases claim).
   > **MCP equivalent:** `end_work(task_id="{id}", note="non-impl pass-through", outcome="success")`
3. Return: `DONE #{id} -> review | non-impl pass-through, no code changes`
4. **Stop here.**

## Step 1 — Plan the Change

Before writing any code, articulate:

- **What will change** — which files, functions, interfaces
- **Expected behavior** — what the code should do when complete
- **What could go wrong** — edge cases, breaking changes, import cycles

For function signature or interface changes, use `vscode_listCodeUsages` to find all callers and verify the change won't break downstream consumers.

## Step 2 — Read Existing Tests

The test-writer has already created `TestFromAC_*` classes in `tests/test_{module}.py`.

1. Read the test file — identify every `TestFromAC_*` class.
2. Extract expected interfaces: function signatures, class names, error types, return values, and import paths.
3. Compare expected interfaces against the actual codebase. If they conflict:
   - **Tests assume wrong interface** (AC is correct, tests are wrong) → `end_work(outcome="reject", move_to="todo")` with notes on the real interface. Test-writer rewrites.
   - **AC describes wrong interface** (codebase contradicts the AC) → `end_work(outcome="reject", move_to="backlog")` with notes on the mismatch. Architect fixes AC.
4. Plan implementation approach based on these interfaces.

Verify all `TestFromAC_*` tests currently **fail** via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  lint_paths: ["tests/test_{module}.py"]
```

Confirm all `TestFromAC_*` tests appear in the `failed:` list. If any pass, investigate before implementing.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

See `h-pytest-and-linting` for flags and known pitfalls.

> **Backward compatibility:** When no `TestFromAC_*` classes exist (old-style single-agent TDD), fall back to the full RED+GREEN workflow — write failing tests yourself, then implement.

## Step 3 — Implement Minimal Code (GREEN)

Write the minimum code to make all tests pass:

- Follow existing module patterns.
- `from __future__ import annotations` at top.
- Type hints on all function signatures.
- Functions under ~50 lines.
- Docstrings on public classes and functions.

Run and verify via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  lint_paths: ["packages/{package}/src/", "tests/test_{module}.py"]
```

All tests must pass (`failed: []`), zero failures.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 4 — Add Builder-Discovered Tests (Optional)

During implementation you may discover edge cases not covered by the test-writer's `TestFromAC_*` tests. Add these in a **separate** `TestBuilderDiscovered` class. Never add to `TestFromAC_*` classes.

Each builder-discovered test follows RED-GREEN within this step:

1. Write the test in `TestBuilderDiscovered` — verify it **fails**.
2. Implement the fix — verify it **passes**.

Skip if `TestFromAC_*` tests already cover the behavior adequately.

## Step 5 — Refactor (If Needed)

Only refactor code you just wrote:

- Remove duplication within your change.
- Improve naming if unclear.
- Split functions if too long.
- Do NOT refactor unrelated code.

## Step 6 — Verify

Run the verification suite via Quality-Runner. **Always scope runs** to avoid timeouts:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["packages/{package}/src/", "tests/test_{module}.py"]
```

All must pass (`failed: []`, `clean: true`). Target 90% coverage on touched modules.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
uv run ruff check packages/ tests/
```

See `h-pytest-and-linting` for exact flags and known pitfalls.

**Refactoring check:** If your change renames imports, changes function signatures, or moves mock targets, grep all test files for the old symbol name before proceeding:

```powershell
Select-String -Path "tests/*.py" -Pattern "old_name"
```

## Step 7 — Deliverables

Append builder notes to task body via `edit_task` (with `append_body` and `timestamp=True`).

> **MCP equivalent:** `edit_task(task_id="{id}", append_body="## Builder Notes\n...", timestamp=True)`

Commit per `r-project-standards` → Commit Discipline:

```powershell
git add packages/{package}/src/{namespace}/{module}.py tests/test_{module}.py
git commit -m "feat: implement {feature} (#{id}, builder)"
```

Verify only task-related files are staged.

## Step 8 — Advance

Advance via `end_work` (moves to `review` + releases claim).

> **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")`

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Builder Notes
- Implementation: {files changed}
- Tests: {N} TestFromAC passed, {M} TestBuilderDiscovered added
- Coverage: {X}% on touched modules
- ruff: clean
- Approach: {brief description of implementation strategy}
```

## Verification Checklist

- [ ] Test-writer's `TestFromAC_*` tests verified as failing before implementation
- [ ] All `TestFromAC_*` tests pass after implementation
- [ ] No `TestFromAC_*` classes modified
- [ ] Any builder-added tests are in `TestBuilderDiscovered` class
- [ ] Implementation is the minimum code to pass all tests
- [ ] `pytest` all pass, `ruff` clean
- [ ] Coverage 90% or higher on touched modules
- [ ] No unrelated files edited
- [ ] Diff is surgical — smallest change that achieves the AC
- [ ] `from __future__ import annotations` on new files
- [ ] Type hints on all signatures, docstrings on public API
- [ ] Deliverables committed before advancing

## Known Pitfalls

- **Modifying TestFromAC classes:** The builder must never weaken, remove, or modify test-writer tests. This is an automatic FAIL in review.
- **Scoped test runs:** Always scope to task-specific files. The full suite has hundreds of tests and will time out.
- **Coverage measurement failures:** Load `h-pytest-and-linting` before retrying flag variations. The skill documents the exact approach.
- **Symbol renames breaking other tests:** When renaming imports or mock targets, grep all test files for the old name. Single-file updates cause 10–40 regressions when other files still reference the old symbol.
- **Non-impl pass-through:** Check for the test-writer's pass-through note FIRST. Missing this check causes unnecessary implementation attempts on config/docs tasks.
