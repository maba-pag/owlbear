---
name: w-tdd-green
description: "Workflow: TDD GREEN phase — implement minimal code to pass failing tests"
user-invocable: false
---

# TDD GREEN Phase

Implement the minimum code to make all failing tests pass. This is the GREEN phase of TDD — the test-writer already wrote the RED tests.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `in-progress` status (the test-writer already moved it here).

### Step 0a — Non-Implementation Pass-Through

Check the task body for `## Test-Writer Notes` containing "Non-implementation task" or "non-impl pass-through". If found:

1. Advance via `end_work(note="## Builder Notes\n- Non-implementation task — no code changes needed.\n- Passing through to review.")` (moves to `review` + releases claim).
3. Return: `DONE #{id} -> review | non-impl pass-through, no code changes`
4. **Stop here.**

## Step 1 — Plan the Change

Before writing any code, articulate:

- **What will change** — which files, functions, interfaces
- **Expected behavior** — what the code should do when complete
- **What could go wrong** — edge cases, breaking changes, import cycles

For function signature or interface changes, use `vscode_listCodeUsages` to find all callers and verify the change won't break downstream consumers.

## Step 2 — Read Existing Tests

The test-writer has already created `TestFromAC_*` classes in `tests/test_{module}_{task_id}.py`.

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
  test_paths: ["tests/test_{module}_{task_id}.py"]
  lint_paths: ["tests/test_{module}_{task_id}.py"]
```

Confirm all `TestFromAC_*` tests appear in the `failed:` list. If any pass, investigate before implementing.

### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```shell
uv run pytest tests/test_{module}_{task_id}.py -q --tb=short
```

See `h-pytest-and-linting` for flags and known pitfalls.

> **Backward compatibility:** When no `TestFromAC_*` classes exist (old-style single-agent TDD), fall back to the full RED+GREEN workflow — write failing tests yourself, then implement.

### Module-Level Test Visibility

After confirming the task-scoped tests fail, also run the module's durable test file (if it exists) to establish a regression baseline:

```shell
uv run pytest tests/test_{module}.py -q --tb=short 2>/dev/null || echo "No module-level test file — skip"
```

This gives early cross-task regression signal without full-suite cost. If `tests/test_{module}.py` does not exist, skip with a note — module-level files are test-curator-managed.

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
  test_paths: ["tests/test_{module}_{task_id}.py"]
  lint_paths: ["serve/{package}/src/", "tests/test_{module}_{task_id}.py"]
```

All tests must pass (`failed: []`), zero failures.

### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```shell
uv run pytest tests/test_{module}_{task_id}.py -q --tb=short
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 4 — Add Builder-Discovered Tests (Optional)

During implementation you may discover edge cases not covered by the test-writer's `TestFromAC_*` tests. Add these in a **separate** `TestBuilderDiscovered` class in the same task-scoped file. Never add to `TestFromAC_*` classes.

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
  test_paths: ["tests/test_{module}_{task_id}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["serve/{package}/src/", "tests/test_{module}_{task_id}.py"]
```

All must pass (`failed: []`, `clean: true`). Target 90% coverage on touched modules.

Also run the module-level durable tests (if they exist) to catch cross-task regressions:

```shell
uv run pytest tests/test_{module}.py -q --tb=short 2>/dev/null || echo "No module-level test file — skip"
```

### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```shell
uv run pytest tests/test_{module}_{task_id}.py -q --tb=short
uv run pytest tests/test_{module}_{task_id}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
uv run ruff check serve/ tests/
```

See `h-pytest-and-linting` for exact flags and known pitfalls.

**Refactoring check:** If your change renames imports, changes function signatures, or moves mock targets, grep all test files for the old symbol name before proceeding:

```shell
grep -r "old_name" tests/*.py
```

### Step 6.1 — Pass: Continue

If verification passes (`failed: []`, `clean: true`, coverage ≥ 90%), proceed to Step 7.

### Step 6.2 — Fail: Same-Context Retry

If verification fails:

1. Read the error output — identify the specific failing test and error message.
2. Diagnose the root cause.
3. Apply a targeted fix.
4. Re-verify via Quality-Runner (or fallback).

If this second run passes, proceed to Step 7.

### Step 6.3 — Fail Again: Delegate to fix-attempt

This triggers after exactly 2 failures (not 1, not 3): initial attempt → same-context retry (Step 6.2) → fix-attempt delegation. The sequence is mandatory; never skip steps.

> **Prerequisite:** Before invoking, verify that `fix-attempt` is included in the builder's `agents:` array. Agents not listed in the array fail silently — confirm this agents-array dependency before delegation.

Construct and invoke the fix-attempt subagent. Fields must conform to the Input Contract in `fix-attempt.agent.md`:

```
agentName: fix-attempt
prompt: |
  task_id: {id}
  test_file: tests/test_{module}_{task_id}.py
  source_files: serve/{package}/src/{namespace}/{module}.py
  retry_hint: {extract specific errors from error output; identify which failing tests produced them; provide Reflexion-style verbal diagnosis — what went wrong, which failing test(s) are blocked, and the suggested fix direction. Not generic "tests failed".}
  error_summary: {condensed pytest failure output, max 500 tokens}
```

Handle fix-attempt result:

| Verdict | Action |
|---------|--------|
| `FIXED` | Re-verify with pytest (all tests must pass) and ruff (lint clean). If pass → proceed to Step 7. If still failing → `end_work(outcome="reject")`: diagnose root cause and route to `todo` (test assumptions wrong) or `backlog` (AC/architecture wrong). |
| `FAILED` | Diagnose root cause: test assumptions wrong → `end_work(outcome="reject", move_to="todo")`; AC/architecture wrong → `end_work(outcome="reject", move_to="backlog")`. Append Channel B notes with same-context retry (Step 6.2) diagnosis and fix-attempt diagnosis — record each source separately. |

## Step 7 — Deliverables

Include builder notes in your `end_work` note.

Commit per `r-project-standards` → Commit Discipline:

```shell
git add serve/{package}/src/{namespace}/{module}.py tests/test_{module}_{task_id}.py
git commit -m "feat: implement {feature} (#{id}, builder)"
```

Verify only task-related files are staged.

## Step 8 — Advance

Advance via `end_work` (moves to `review` + releases claim).

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
