---
name: w-tdd-red
description: "Workflow: TDD RED phase — write failing tests from acceptance criteria"
user-invocable: false
---

# TDD RED Phase

Write failing tests from a task's acceptance criteria. All tests must fail when complete — this is the RED phase of TDD.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Write failing tests from AC (RED phase).
- Non-impl pass-through (tag-based).
- Depth-zero pass-through (all `td:0`).
- Retry-cycle gap-fill from reviewer findings.
- Direct-to-review advance for test-only retries when all new tests are green.

### Out of Scope

- Writing or editing source code — builder (`w-tdd-green`).
- AC quality validation — architect (`w-arch-review`).
- Code review — reviewer (`w-code-review`).
- Architecture decisions — architect (`w-arch-review`).
- Full-suite regression — auditor (`w-task-verification`).

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

## Step 1 — Assess Task Type

From the task body retrieved by `start_work`:

<!-- NON_IMPL_TAGS: Authoritative list at w-arch-review (agent dispatch table). -->

1. Check if this is a **non-implementation task** (tagged `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, or `type:user-action`). If so, go to **Step 1a — Pass-through**.
2. Check `Proof bundle:` and route per `r-pipeline-protocol` taxonomy: `skip`/`existing` -> **Step 1d — Proof-bundle pass-through**; `smoke` -> continue with smoke-only planning/writing (one smoke test per AC line); `behavioral`/`critical` -> continue with full TDD mapping.
3. If `Proof bundle:` is absent, use legacy `(td:N)` compatibility from `r-pipeline-protocol` (Step 1e).
4. Check if this is a **retry cycle** (body contains both `## Test-Writer Notes` and `## Review Evidence`). If so, go to **Step 1b — Retry-cycle handling**.
5. Identify referenced source files, modules, and interfaces in the AC.
6. Do NOT move task status yet — movement happens in Step 7 after verification.

### Step 1a — Pass-Through for Non-Implementation Tasks

Some tasks have no testable implementation (research, documentation, config).

1. Advance via `end_work(note="## Test-Writer Notes\n- Non-implementation task (tagged {tag}) — no tests applicable.\n- Passing through to builder.")` (moves to `in-progress` + releases claim).
3. Return: `DONE #{id} -> in-progress | non-impl pass-through, no tests needed`
4. **Stop here.**

### Step 1b — Retry-Cycle Handling (Surgical Fill Mode)

If the body contains both `## Test-Writer Notes` and `## Review Evidence`, this is a retry (reviewer FAILed back to `todo`).

**Reading priority — follow this order before writing any tests:**

1. **Read `## Review Evidence` → "Required Follow-up"** section. This tells you EXACTLY which gaps to fill. Do not re-derive from scratch.
2. **Read the latest `## Builder Notes`** section. This shows the CURRENT interface state — removed parameters, renamed methods, changed signatures. Your new tests MUST match this reality.
3. **Check your own prior `## Test-Writer Notes`** — understand what already exists so you don't duplicate.
4. Reference the original AC only to verify you're targeting the right behavior.

**Writing rules:**

- **If reviewer cites missing tests:** Write NEW failing tests addressing ONLY the specified gaps. Add them to the existing `TestFromAC_{Feature}` class (or a new `TestFromAC_` class for a distinct AC concern). Do NOT remove or modify existing passing tests. Do NOT do a broad coverage uplift — fill only the reviewer's gaps.
- **If reviewer cites code quality, weak tests, or security (not missing tests):** Pass through — the builder will address the findings.
- Delegate to `quality-runner` to verify: old tests PASS, new tests FAIL (for the new gaps). If all tests pass (implementation already handles the gap), note this and advance — **the builder pass-through is unnecessary** (see Step 1b.1 below).

**Advance:** Commit new test files first, then advance:

```shell
git add tests/test_{module}_{task_id}.py && git commit -m "test: add retry tests for {feature} (#{id}, test-writer)"
```

Then: `end_work(note="## Test-Writer Notes\n- Retry: {summary of changes}")` (moves to `in-progress` + releases claim).

Return: `DONE #{id} -> in-progress | retry, {N} existing tests preserved{, M new tests added}`

**Stop here.**

#### Step 1b.1 — Direct-to-Review Advance (Test-Only Retry)

If ALL of the following are true:

- Reviewer's Required Follow-up contained ONLY test-proof gaps (no implementation fixes needed)
- All NEW tests PASS against current code (implementation already handles them)
- No lint or coverage issues detected

Then the builder has no work to do. Commit new tests, then advance directly to `review` instead of `in-progress`:

```shell
git add tests/test_{module}_{task_id}.py && git commit -m "test: add retry tests for {feature} (#{id}, test-writer)"
```

- `end_work(outcome="success", move_to="review", note="## Test-Writer Notes\n- Retry: added {M} tests for reviewer gaps. All pass against current impl.\n- Builder skip: test-only retry, all tests green.")`
- Return: `DONE #{id} -> review | test-only retry, builder skipped`
- **Stop here.**

### Step 1c — Depth-Zero Pass-Through

All AC lines are annotated `(td:0)` — no tests needed for this task.

If the Architecture Review verdict or AC text includes `Existing proof required: ...`, copy that line into the Test-Writer Notes. Test-writer still skips new test creation; builder/reviewer own proof execution through Quality-Runner.

1. Advance via `end_work(note="## Test-Writer Notes\n- All AC lines are (td:0) — test-writer skipped.\n- Passing through to builder.")` (moves to `in-progress` + releases claim).
2. Return: `DONE #{id} -> in-progress | all AC td:0, no tests needed`
3. **Stop here.**

### Step 1d — Proof-Bundle Pass-Through

If `Proof bundle:` is `skip` or `existing`, no new RED tests are required.

1. Advance via `end_work(note="## Test-Writer Notes\n- Proof bundle: {value} — no new test writing required.\n- Passing through to builder.")` (moves to `in-progress` + releases claim).
2. Return: `DONE #{id} -> in-progress | proof bundle {value}, no tests needed`
3. **Stop here.**

### Step 1e — Legacy `(td:N)` Compatibility (Fallback)

Only run this fallback when `Proof bundle:` is absent.

1. Apply `r-pipeline-protocol` compatibility mapping for legacy `(td:N)` tasks.
2. If all AC lines are effectively `td:0`, go to **Step 1c — Depth-zero pass-through**.
3. Otherwise continue with Step 2+ RED workflow using the mapped depth.

## Step 2 — Search Codebase

Find interfaces, types, and existing patterns referenced in the AC:

- Read source files to understand function signatures, data structures, error types.
- Check existing `conftest.py` files for reusable fixtures.
- Source files are **read-only** — never create or edit files in `src/`.

### Step 2a — Non-Implementation Assessment

Run this only if Step 2 found no testable interfaces:

1. **Scan AC for Python implementation intent** — keywords: `implement`, `function`, `method`, `class`, `module`, `src/`, `workspace/`, `.py`, `import`, `endpoint`, `API`.
2. **If implementation intent found:** proceed to Step 3 (new-module RED phase, ImportError tests expected).
3. **If NO intent AND AC references only non-Python files** (`.agent.md`, `SKILL.md`, `.instructions.md`, `.yml`, `.yaml`, `.json`, `.md`, `.prompt.md`): heuristic pass-through. Advance via `end_work(note="## Test-Writer Notes\n- Non-impl pass-through: config/docs only")`, return signal, and stop.
4. **If ambiguous:** default to pass-through with strong warning. Escalate to decision request via `create_dr` only when AC is too ambiguous to determine builder intent.

## Step 3 — Plan Test Categories

If `Proof bundle:` is present, use it as the primary routing signal:

- `smoke`: plan one smoke test per AC line (one assertion, happy path only)
- `behavioral` or `critical`: map each AC line to full TDD categories

If `Proof bundle:` is absent, use legacy `(td:N)` fallback behavior:

- Skip `(td:0)` AC lines entirely — do not plan or write tests for them
- For `(td:1)` lines (or lines without annotation — default to td:1), plan a single smoke test per line
- For `(td:2)` lines, map each AC line to test categories

Full TDD categories:

- **Happy path** — expected behavior works correctly
- **Edge cases** — empty inputs, boundary values, concurrent access
- **Error paths** — invalid inputs, missing dependencies, expected exceptions
- **Boundary conditions** — limits, thresholds, off-by-one scenarios

## Step 4 — Write Tests

Create `tests/test_{module}_{task_id}.py` with class `TestFromAC_{Feature}`:

- Each AC line gets at least one test.
- Prefer exact-value assertions over pattern matching: use `==` for values, assert exact exception types, and assert exact return values.
- Use pattern-based assertions (`in`, `>`, regex, partial matches) only when the AC explicitly describes pattern-based behavior.
- **AC lines stating "X unchanged" / "no modification to Y" / "existing Z unmodified":** Write a direct regression guard test that calls the production code path and asserts the expected result. Do NOT rely on transitive coverage — if another test exercises X as a side-effect, that is not a substitute. A direct `TestFromAC_*` test is required.
- Test the **contract** described in AC, not a specific implementation.
- Use `unittest.mock.patch` / `MagicMock` for external dependencies.
- `from __future__ import annotations` at top of new files.
- Type hints on test helper functions.

**File naming:**

- Default: task-scoped tests use `tests/test_{module}_{task_id}.py` (transient — removed by test-curator post-archive).
- Consolidation exception: when the task is tagged `consolidation-test`, write durable tests in `serve/{package}/tests/test_{module}.py`.
- Outside `consolidation-test` tasks, durable module-level files are test-curator-managed and must not be created or edited by the test-writer.

**Class naming convention:**

- `TestFromAC_{Feature}` — tests written by the test-writer from AC.
- `TestBuilderDiscovered` is retired. If builder reports missing blocking edge-case coverage, add the needed tests under the `TestFromAC_` convention.
- For `consolidation-test` durable files, use descriptive class names (for example, `TestBookmarkPipelineDurable`) and do not use `TestFromAC_`.

**TestFromAC immutability:** During the active pipeline (task creation through archive), `TestFromAC_*` classes are immutable — the builder cannot weaken, remove, or modify them. Post-archive, the test-curator gains authority to promote, consolidate, or remove assertions.

## Step 5 — Verify RED

Run the test file through Quality-Runner and confirm **every** test fails:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}_{task_id}.py"]
  lint_paths: ["tests/test_{module}_{task_id}.py"]
```

Confirm all tests appear in `failed:` list and `clean: true` in the Quality-Runner report.

**Expected failure types:** `ImportError`, `NotImplementedError`, `AssertionError`.

**Fix these:** `SyntaxError` (bug in test code). Any test that **passes** means the implementation already exists — remove the test or make it more specific.

Must be clean.

## Step 6 — Commit & Advance

Include the test summary in your `end_work` note:

```
## Test-Writer Notes
- Test file: tests/test_{module}_{task_id}.py
- Classes: {list of TestFromAC_ classes}
- Tests per category: happy {h}, edge {e}, error {r}, boundary {b}
- Total: {N} tests, all FAIL
- ruff: clean
```

**Commit your deliverables** (see `r-pipeline-protocol` → Who Commits What):

```shell
git add tests/test_{module}_{task_id}.py && git commit -m "test: add failing tests for {feature} (#{id}, test-writer)"
```

Stage only test files you created or modified. Verify with `git diff --cached --name-only` if uncertain.

Then advance via `end_work` (moves to `in-progress` + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Test-Writer Notes
- Test file: tests/test_{module}_{task_id}.py
- Classes: {list of TestFromAC_ classes}
- Tests per category: happy {h}, edge {e}, error {r}, boundary {b}
- Total: {N} tests, all FAIL
- ruff: clean
```

## Verification Checklist

- [ ] Every AC line has at least one test
- [ ] All tests are contract-level (no implementation assumptions)
- [ ] `TestFromAC_{Feature}` naming on all test classes
- [ ] `pytest` confirms all tests FAIL (ImportError, NotImplementedError, or AssertionError)
- [ ] No `SyntaxError` failures
- [ ] `ruff` clean on test file
- [ ] No source files created or edited — only test files
- [ ] `from __future__ import annotations` on new files
- [ ] Summary included in `end_work` note
- [ ] Test files committed before advancing
- [ ] All tests actually fail (not error) when run against current code
- [ ] Each AC line has at least one corresponding test

## Known Pitfalls

- **Tests that pass unexpectedly:** The implementation may already exist. Remove the test or make it more specific to truly new behavior.
- **SyntaxError in tests:** This is a bug in your test code, not a legitimate RED failure. Fix before completing.
- **Modifying source files:** The test-writer must never create or edit `src/` files. Tests define the contract; the builder implements.
- **Retry cycle confusion:** On retry, do NOT re-run the full RED phase. Read the reviewer's evidence and act on the specific feedback.
- **Pass-through tag detection:** Check both bare tags and `type:` prefix variants. Missing a pass-through tag causes unnecessary test writing for non-impl tasks.
- **Forgetting to commit on retry paths:** Step 1b and Step 1b.1 both create new test files. Commit them before calling `end_work` — the same rule applies as the main path.
