---
name: w-tdd-red
description: "Workflow: TDD RED phase — write failing tests from acceptance criteria"
user-invocable: false
---

# TDD RED Phase

Write failing tests from a task's acceptance criteria. All tests must fail when complete — this is the RED phase of TDD.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

## Step 1 — Assess Task Type

From the task body retrieved by `start_work`:

<!-- NON_IMPL_TAGS: Authoritative list at w-arch-review (agent dispatch table). -->

1. Check if this is a **non-implementation task** (tagged `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, or `type:user-action`). If so, go to **Step 1a — Pass-through**.
2. Check if this is a **retry cycle** (body contains both `## Test-Writer Notes` and `## Review Evidence`). If so, go to **Step 1b — Retry-cycle handling**.
3. Identify referenced source files, modules, and interfaces in the AC.
4. Do NOT move task status yet — movement happens in Step 7 after verification.

### Step 1a — Pass-Through for Non-Implementation Tasks

Some tasks have no testable implementation (research, documentation, config).

1. Advance via `end_work(note="## Test-Writer Notes\n- Non-implementation task (tagged {tag}) — no tests applicable.\n- Passing through to builder.")` (moves to `in-progress` + releases claim).
3. Return: `DONE #{id} -> in-progress | non-impl pass-through, no tests needed`
4. **Stop here.**

### Step 1b — Retry-Cycle Handling

If the body contains both `## Test-Writer Notes` and `## Review Evidence`, this is a retry (reviewer FAILed back to `todo`).

1. Read the `## Review Evidence` section to understand the failure reason.
2. **If reviewer cites missing tests:** Write NEW failing tests addressing gaps. Add them to the existing `TestFromAC_{Feature}` class (or a new `TestFromAC_` class for a distinct AC concern). Do NOT remove or modify existing passing tests. Run pytest to verify: old tests PASS, new tests FAIL.
3. **If reviewer cites code quality, weak tests, or security (not missing tests):** Pass through — the builder will address the findings.
4. Advance via `end_work(note="## Test-Writer Notes\n- Retry: {summary of changes}")` (moves to `in-progress` + releases claim).
5. Return: `DONE #{id} -> in-progress | retry, {N} existing tests preserved{, M new tests added}`
6. **Stop here.**

## Step 2 — Search Codebase

Find interfaces, types, and existing patterns referenced in the AC:

- Read source files to understand function signatures, data structures, error types.
- Check existing `conftest.py` files for reusable fixtures.
- Source files are **read-only** — never create or edit files in `src/`.

### Step 2a — Non-Implementation Assessment

Run this only if Step 2 found no testable interfaces:

1. **Scan AC for Python implementation intent** — keywords: `implement`, `function`, `method`, `class`, `module`, `src/`, `serve/`, `.py`, `import`, `endpoint`, `API`.
2. **If implementation intent found:** proceed to Step 3 (new-module RED phase, ImportError tests expected).
3. **If NO intent AND AC references only non-Python files** (`.agent.md`, `SKILL.md`, `.instructions.md`, `.yml`, `.yaml`, `.json`, `.md`, `.prompt.md`): heuristic pass-through. Advance via `end_work(note="## Test-Writer Notes\n- Non-impl pass-through: config/docs only")`, return signal, and stop.
4. **If ambiguous:** default to pass-through with strong warning. Escalate to decision request via scribe only when AC is too ambiguous to determine builder intent.

## Step 3 — Plan Test Categories

Map each AC line to test categories:

- **Happy path** — expected behavior works correctly
- **Edge cases** — empty inputs, boundary values, concurrent access
- **Error paths** — invalid inputs, missing dependencies, expected exceptions
- **Boundary conditions** — limits, thresholds, off-by-one scenarios

## Step 4 — Write Tests

Create `tests/test_{module}_{task_id}.py` with class `TestFromAC_{Feature}`:

- Each AC line gets at least one test.
- **AC lines stating "X unchanged" / "no modification to Y" / "existing Z unmodified":** Write a direct regression guard test that calls the production code path and asserts the expected result. Do NOT rely on transitive coverage — if another test exercises X as a side-effect, that is not a substitute. A direct `TestFromAC_*` test is required.
- Test the **contract** described in AC, not a specific implementation.
- Use `unittest.mock.patch` / `MagicMock` for external dependencies.
- `from __future__ import annotations` at top of new files.
- Type hints on test helper functions.

**File naming:** Task-scoped tests use `test_{module}_{task_id}.py` (transient — removed by test-curator post-archive). Module-level `test_{module}.py` files are test-curator-managed and must not be created or edited by the test-writer.

**Class naming convention:**

- `TestFromAC_{Feature}` — tests written by the test-writer from AC.
- `TestBuilderDiscovered` is retired. If builder reports missing blocking edge-case coverage, add the needed tests under the `TestFromAC_` convention.

**TestFromAC immutability:** During the active pipeline (task creation through archive), `TestFromAC_*` classes are immutable — the builder cannot weaken, remove, or modify them. Post-archive, the test-curator gains authority to promote, consolidate, or remove assertions.

## Step 5 — Verify RED

Run pytest on the test file and confirm **every** test fails via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}_{task_id}.py"]
  lint_paths: ["tests/test_{module}_{task_id}.py"]
```

Confirm all tests appear in `failed:` list and `clean: true` in the Quality-Runner report.

### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, **block the task** per `r-pipeline-protocol` → Quality-Runner Mandate:

```
end_work(outcome="block", block_reason="Quality-Runner unavailable — cannot verify RED-phase failures independently")
```

Do not run pytest directly. Direct shell invocation is prohibited — it bypasses the canonical evidence pipeline.

**Expected failure types:** `ImportError`, `NotImplementedError`, `AssertionError`.

**Fix these:** `SyntaxError` (bug in test code). Any test that **passes** means the implementation already exists — remove the test or make it more specific.

Must be clean.

## Step 6 — Deliverables

Include the test summary in your `end_work` note:

```
## Test-Writer Notes
- Test file: tests/test_{module}_{task_id}.py
- Classes: {list of TestFromAC_ classes}
- Tests per category: happy {h}, edge {e}, error {r}, boundary {b}
- Total: {N} tests, all FAIL
- ruff: clean
```

Commit per `r-project-standards` → Commit Discipline:

```shell
git add tests/test_{module}_{task_id}.py
git commit -m "test: add failing tests for {feature} (#{id}, test-writer)"
```

Verify only test files are staged.

## Step 7 — Advance

Advance via `end_work` (moves to `in-progress` + releases claim).

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
