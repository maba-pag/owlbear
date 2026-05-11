---
name: w-tdd-green
description: "Workflow: TDD GREEN phase — implement minimal code to pass failing tests"
user-invocable: false
---

# TDD GREEN Phase

Implement the minimum code to make all failing tests pass. This is the GREEN phase of TDD — the test-writer already wrote the RED tests.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Implement minimal code to pass tests (GREEN phase).
- Run quality-runner for scoped tests, lint, and coverage.
- Non-impl pass-through.
- Reject to test-writer (wrong interface) or architect (wrong AC).
- Commit source files before advancing.

### Out of Scope

- Writing tests — test-writer (`w-tdd-red`).
- Refactoring unrelated modules — planner/architect for separate task routing (`w-task-decomposition`, `w-arch-review`).
- AC quality validation — architect (`w-arch-review`).
- Code review — reviewer (`w-code-review`).
- Documentation updates — doc-writer (`w-doc-update`).

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Verify the task is in `in-progress` status (the test-writer already moved it here).

### Step 0a — Bundle-Based Routing

Route builder verification flow from `Proof bundle:` in the task body (see `r-pipeline-protocol` taxonomy). Use legacy `(td:N)` only as compatibility fallback when `Proof bundle:` is absent.

1. If `Proof bundle: skip`:
   Implement from AC directly (no `TestFromAC_*` pass requirement for this task).

  Continue the normal builder flow (plan, implement, verify, commit, and advance) without `TestFromAC_*` test-gate requirements.

  Record in Builder Notes that `Proof bundle: skip` removed `TestFromAC_*` verification only; it did not remove AC implementation obligations.

  Return: `DONE #{id} -> review | proof bundle skip, AC implemented without TestFromAC gate`

   **Stop here.**

2. If `Proof bundle: existing`:
   Implement from AC directly (no new tests to write).

   Find `Existing proof required: ...` in AC, Architecture Review, or Test-Writer Notes.

   Run the named existing proof through Quality-Runner before advancing. Use `mode=scoped` for named test paths and `mode=full` only when the required proof is explicitly full-suite.

   Record the Quality-Runner summary in Builder Notes.

   Do not advance while required proof is failing or missing.

  After proof passes, continue the normal builder flow (commit and advance with `## Builder Notes` evidence).

   Return: `DONE #{id} -> review | proof bundle existing, required proof passed`

   **Stop here.**

3. If `Proof bundle:` is absent, apply legacy compatibility mapping from `r-pipeline-protocol` before continuing.

4. Keep the explicit non-impl pass-through trigger: if Test-Writer Notes contain "Non-implementation task" or "non-impl pass-through", advance with no code changes and pass through to review.

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
   - **Tests assume wrong interface** (AC is correct, tests are wrong) → `end_work(outcome="reject", move_to="todo")` with Required Follow-up table (see `r-pipeline-protocol` §3) targeting test-writer: list each test method + the correct interface it should assert.
   - **AC describes wrong interface** (codebase contradicts the AC) → `end_work(outcome="reject", move_to="backlog")` with Required Follow-up table targeting architect: list each AC line + what the codebase actually does.
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

> **Missing RED tests:** When no `TestFromAC_*` classes exist and this is not an explicit non-implementation pass-through, reject to `todo` with a Required Follow-up table for test-writer. Builder does not write failing tests.

### Module-Level Test Visibility

After confirming the task-scoped tests fail, also check the module's durable test file (if it exists) through Quality-Runner to establish a regression baseline. Prefer canonical package-local durable tests in `serve/{package}/tests/`, with root `tests/` as a legacy fallback during transition.

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["serve/{package}/tests/test_{module}.py"]  # or ["tests/test_{module}.py"] if only the legacy root file exists
  lint_paths: ["serve/{package}/tests/test_{module}.py"]
```

If no module-level durable test file exists, record `No module-level test file — skip`. This gives early cross-task regression signal without full-suite cost while preserving the canonical evidence pipeline.

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

## Step 4 — Handle Missing Blocking Edge Cases

During implementation you may discover a blocking edge case not covered by the
test-writer's `TestFromAC_*` tests.

When that happens:

1. Do **not** write a new test.
2. Do **not** modify `TestFromAC_*` classes.
3. Reject back to the test-writer via `end_work(outcome="reject", move_to="todo")`.
4. Include a Required Follow-up table (see `r-pipeline-protocol` §3) targeting test-writer: list the missing behavior, why it blocks implementation, and which test class should cover it.
5. Do not commit partial GREEN-phase work when rejecting for missing test
  coverage.

Skip this step when existing `TestFromAC_*` coverage is sufficient.

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

Also check the module-level durable tests (if they exist) through Quality-Runner to catch cross-task regressions:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["serve/{package}/tests/test_{module}.py"]  # or ["tests/test_{module}.py"] if only the legacy root file exists
  lint_paths: ["serve/{package}/tests/test_{module}.py"]
```

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
| `FIXED` | Re-verify via Quality-Runner (all tests must pass, lint clean). If pass → proceed to Step 7. If still failing → `end_work(outcome="reject")`: diagnose root cause and route to `todo` (test assumptions wrong) or `backlog` (AC/architecture wrong). Include Required Follow-up table. |
| `FAILED` | Diagnose root cause: test assumptions wrong → `end_work(outcome="reject", move_to="todo")`; AC/architecture wrong → `end_work(outcome="reject", move_to="backlog")`. Include Required Follow-up table. Append Channel B notes with same-context retry (Step 6.2) diagnosis and fix-attempt diagnosis — record each source separately. |

## Step 7 — Commit & Advance

Include builder notes in your `end_work` note.

**Commit your deliverables** (see `r-pipeline-protocol` → Who Commits What):

```shell
git add serve/{package}/src/{namespace}/{module}.py && git commit -m "feat: implement {feature} (#{id}, builder)"
```

Stage only files you created or modified. Verify with `git diff --cached --name-only` if uncertain.

Then advance via `end_work` (moves to `review` + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Builder Notes
- Implementation: {files changed}
- Tests: {N} TestFromAC passed
- Coverage: {X}% on touched modules
- ruff: clean
- Approach: {brief description of implementation strategy}
```

## Verification Checklist

- [ ] Test-writer's `TestFromAC_*` tests verified as failing before implementation
- [ ] All `TestFromAC_*` tests pass after implementation
- [ ] No `TestFromAC_*` classes modified
- [ ] No tests were added or modified by the builder
- [ ] Implementation is the minimum code to pass all tests
- [ ] Quality-Runner reports `failed: []` and `clean: true`
- [ ] Coverage 90% or higher on touched modules
- [ ] No unrelated files edited
- [ ] Diff is surgical — smallest change that achieves the AC
- [ ] `from __future__ import annotations` on new files
- [ ] Type hints on all signatures, docstrings on public API
- [ ] Deliverables committed before advancing

## Known Pitfalls

- **Modifying or adding tests:** The builder must never weaken, remove, or add tests. Missing blocking edge-case coverage goes back to the test-writer.
- **Scoped test runs:** Always scope to task-specific files. The full suite has hundreds of tests and will time out.
- **Coverage measurement failures:** Invoke the `quality-runner` subagent for coverage measurement — do not load pytest skills or retry flag variations directly.
- **Symbol renames breaking other tests:** When renaming imports or mock targets, grep all test files for the old name. Single-file updates cause 10–40 regressions when other files still reference the old symbol.
- **Non-impl pass-through:** Check for the test-writer's pass-through note FIRST. Missing this check causes unnecessary implementation attempts on config/docs tasks.
