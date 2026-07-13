---
id: 1532
title: 'P1-01: Tests for body newline normalization at MCP kanban ingress'
status: archived
priority: medium
created: 2026-05-13T12:29:10.026075+00:00
updated: 2026-05-13T15:31:12.001370+00:00
tags:
  - phase-1
  - scope:mcp-kanban
  - type:test
parent: 1531
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

RED phase: write tests for the `_normalize_escaped_newlines()` helper and its integration into all 5 MCP kanban tool parameters.

Brief: see parent #1531

## Scope

**In scope:**
- Unit tests for the helper function (three-step protect/normalize/restore)
- Integration tests for all 5 affected parameters (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- Guidance message assertion when normalization occurs
- Guidance positional ordering (existing reminders still fire alongside normalization guidance)
- Escape convention preservation (`\\\\n` → literal `\n` in stored content) for all 5 parameters
- Passthrough (no normalization, no normalization guidance) when input has no literal `\n`

**Out of scope:**
- Implementation of the helper or call-site wiring
- Tool description text (docs-only, verified in impl task)
- Archive remediation, `\r\n`, non-body parameters

## Test Location

`tests/test_mcp_kanban_newline_norm_1531.py`

Existing proof scope: `tests/test_mcp_kanban.py` (must still pass after implementation)

## Acceptance Criteria

- [ ] Unit tests for `_normalize_escaped_newlines()`: protect step (escaped `\\\\n` preserved via sentinel), normalize step (literal `\\n` → real newline), restore step (sentinel → literal `\\n`)
- [ ] Integration tests: each of the 5 parameters triggers normalization (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- [ ] Guidance assertion: normalization guidance message appended to response when normalization occurs
- [ ] Guidance ordering: normalization guidance appends AFTER existing guidance (coexists, does not replace)
- [ ] Escape convention: `\\\\\\\\n` in input → literal `\\n` in stored content for all 5 affected parameters (create_task body, edit_task body, edit_task append_body, end_work note, create_dr body)
- [ ] Passthrough: when input has no literal `\\n`, no normalization occurs and no normalization-specific guidance is emitted (other guidance sources may still fire independently)
- [ ] Test file located at `tests/test_mcp_kanban_newline_norm_1531.py`
- [ ] All normalization-path tests fail in RED phase (passthrough regression guards may pass since no implementation exists to break clean-input behavior)

Proof bundle: skip
Existing proof scope: `tests/test_mcp_kanban.py` (must still pass after GREEN implementation in #1533)
2026-05-13T14:00:22+00:00
## Architecture Review (re-entry after 2nd review FAIL)

### Reviewer Findings Resolution

| # | Finding | Resolution |
|---|---|---|
| 1 | AC 8 vs AC 6 conflict — passthrough tests pass in RED | AC 8 narrowed: "All normalization-path tests fail in RED phase (passthrough regression guards may pass)" — correct TDD practice; regression guards verify negative case |
| 2 | AC 6 "no guidance emitted" too broad — end_work has non-normalization guidance | AC 6 narrowed: "no normalization-specific guidance is emitted (other guidance sources may still fire independently)" — feature scope is normalization only |
| 3 | AC 5 missing append_body escape test | AC 5 now explicitly lists all 5 parameters — test-writer must add `test_escape_convention_append_body_preserved` |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one helper + its 5 integration points |
| Interface clarity | PASS | AC now explicitly scopes guidance contract and escape coverage per parameter |
| Dependency correctness | PASS | No deps; #1533 correctly depends on this |
| Module layering | PASS | Tests import from `owlbear_mcp_kanban.server` — matches existing patterns |
| TDD compliance | PASS | This IS the RED phase; refined AC 8 correctly allows regression-guard greens |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | MCP JSON transport corruption of `\n` confirmed in research |
| Pattern consistency | PASS | Mock AppContext + async tool calls + response assertions |
| Security surface | PASS | Internal string normalization, no new boundaries |
| Single domain | PASS | mcp-kanban only |

### Design Diverge
- Trigger: skipped — single obvious approach

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: `tests/test_mcp_kanban.py`
- Test-writer: SKIP (pass-through via `type:test` tag)

### AC Refinement Summary
Rewrote full body with three targeted AC clarifications: (1) RED gate scoped to normalization-path only, (2) passthrough contract scoped to normalization guidance, (3) escape convention explicitly requires all 5 parameters. The test file needs one addition: `append_body` escape-convention test case.

### Verdict: APPROVE (REFINE path — AC tightened, then advanced)
### Action Taken: Refined AC to resolve review-cycle conflicts, advanced to todo
2026-05-13T14:09:42+00:00
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_newline_norm_1531.py (named after parent #1531, header confirms Task: #1532)
- Proof bundle: skip — tests pre-written and committed in prior session (commit: "test: add failing tests for body newline normalization (#1531, test-writer)")
- type:test tag → pass-through per w-tdd-red Step 1a/1d
- Classes: TestFromAC_NormalizeHelper, TestFromAC_CreateTaskNormalization, TestFromAC_EditTaskNormalization, TestFromAC_EndWorkNormalization, TestFromAC_CreateDrNormalization, TestFromAC_GuidancePositioning, TestFromAC_PassthroughNoNormalization
- Tests per category: happy/unit ~13, integration happy 11, edge 5, boundary 5, passthrough regression guards 5
- Total: ~34 tests; RED confirmed — 0 passed, ImportError on _normalize_escaped_newlines (not yet implemented)
- ruff: clean
2026-05-13T14:19:07+00:00
## Builder Notes
- Task classification: `type:test` RED deliverable authored by test-writer (non-implementation task for builder)
- Proof bundle: `skip` (pass-through eligible per workflow)
- Files changed by builder: none
- Tests run by builder: none (pass-through path)
- Lint run by builder: none (pass-through path)
- Evidence summary:
  - Task body already contains Test-Writer Notes confirming test file creation and RED state for normalization-path tests.
  - Builder did not alter test or source code, preserving ownership boundaries (`builder never writes tests`).
  - Advanced task to review as routing handoff only.
- Fixes applied: none
2026-05-13T14:28:37+00:00
## Review Evidence
- Verdict: FAIL
- FAIL route: FAIL #1532 -> backlog | AC 5 escape-convention coverage is still incomplete, and the file still carries superseded tool-description assertions outside the refined task scope.
- Builder evidence review: proof bundle `skip`; builder changed no files. File inspection was sufficient because the blocking issues are in the task test file itself.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC 5 | The refined child task still lacks the required `edit_task append_body` escape-convention test. The `edit_task` block covers append-body normalization and guidance, but only `body` has an escape-convention assertion. | `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:53`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:69`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:98`, `tests/test_mcp_kanban_newline_norm_1531.py:255`, `tests/test_mcp_kanban_newline_norm_1531.py:272`, `tests/test_mcp_kanban_newline_norm_1531.py:280` | backlog |
| 2 | Scope / AC alignment | The suite still includes `TestFromAC_ToolDescriptions`, even though tool description text is explicitly out of scope for this refined child task. The proof surface still enforces a removed requirement and no longer matches the task notes. | `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:38`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:107`, `tests/test_mcp_kanban_newline_norm_1531.py:534`, `tests/test_mcp_kanban_newline_norm_1531.py:552`, `tests/test_mcp_kanban_newline_norm_1531.py:555`, `tests/test_mcp_kanban_newline_norm_1531.py:558`, `tests/test_mcp_kanban_newline_norm_1531.py:561` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile the refined child-task contract with the test file: ensure `edit_task append_body` has explicit escape-convention proof in this task’s scope before re-dispatching. | `tests/test_mcp_kanban_newline_norm_1531.py`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md` | AC 5 at task `:53`; refinement notes at `:69` and `:98`; current `edit_task` coverage at `:255`, `:272`, `:280` |
| 2 | architect | Remove or extract the superseded tool-description assertions from this child task’s proof surface so review only gates the refined normalization-test contract. | `tests/test_mcp_kanban_newline_norm_1531.py`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md` | task scope `:38` and class list `:107` vs `TestFromAC_ToolDescriptions` at `:534` and assertions at `:552`, `:555`, `:558`, `:561` |

## Observations
- Current server code already contains the normalization helper and parameter-description patches (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:87`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:375`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:411`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:508`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:511`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:600`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:701`), so the stale tool-description assertions happen to align with today’s source. That does not make them in-scope for this refined child task.
- This review occurs after the task was explicitly re-entered from a 2nd review fail (`.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:61`), so protocol requires backlog routing on another blocking review cycle.
2026-05-13T14:32:48+00:00
## Review Rework Instructions (3rd cycle)\n\nTwo specific fixes required — AC is already correct, test file diverged:\n\n### Fix 1: Add missing `append_body` escape-convention test (AC 5)\n\nIn `TestFromAC_EditTaskNormalization`, add `test_escape_convention_append_body_preserved_as_single_backslash_n` — identical pattern to the existing `test_escape_convention_body_preserved_as_single_backslash_n` but targeting `append_body` kwarg.\n\nExpected assertion: `mock_view.edit_task.call_args.kwargs["append_body"] == "want\\nliteral"` when input is `"want\\\\nliteral"`.\n\n### Fix 2: Remove `TestFromAC_ToolDescriptions` class (out of scope)\n\nThe task scope explicitly excludes "Tool description text (docs-only, verified in impl task)". Delete the entire `TestFromAC_ToolDescriptions` class (lines ~534–570). No replacement needed — tool-description verification belongs in #1533.\n\n### No other changes\n\nAll other tests are correct. Do not modify any other test class.
2026-05-13T14:33:03+00:00
## Architecture Review (3rd cycle — rework routing)\n\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | Tests for one helper + 5 integration points |\n| Interface clarity | PASS | AC explicitly lists all 5 parameters for escape convention |\n| Dependency correctness | PASS | No deps; #1533 depends on this |\n| Module layering | PASS | Tests import from owlbear_mcp_kanban.server |\n| TDD compliance | PASS | RED phase task, type:test pass-through |\n| KISS/YAGNI | PASS | Minimal scope |\n| Premise challenge | PASS | MCP JSON transport corruption confirmed |\n| Pattern consistency | PASS | Mock AppContext + async tool calls |\n| Security surface | PASS | Internal string normalization |\n| Single domain | PASS | mcp-kanban only |\n\n### Design Diverge\n- Trigger: skipped — single approach, rework cycle\n\n### Challenge Results\n- Challenger: SKIPPED — proof bundle `skip`\n\n### Proof-Bundle Validation\n- Planner assignment: skip\n- Final bundle: skip\n- Existing proof scope: `tests/test_mcp_kanban.py`\n- Test-writer: SKIP (pass-through via `type:test` tag)\n\n### Reviewer Findings Resolution\n| # | Finding | Action |\n|---|---------|--------|\n| 1 | Missing `edit_task append_body` escape-convention test | Added explicit rework instruction with exact assertion pattern |\n| 2 | `TestFromAC_ToolDescriptions` out of scope | Added explicit rework instruction to delete class |\n\n### Verdict: APPROVE (REFINE path — rework instructions added, advanced to todo)\n### Action Taken: Added Review Rework Instructions section with two targeted fixes, advanced to todo
2026-05-13T14:41:43+00:00
## Test-Writer Notes
- Retry (3rd cycle): two targeted fixes per Review Rework Instructions.
- Test file: tests/test_mcp_kanban_newline_norm_1531.py
- Fix 1 (AC 5): Added `test_escape_convention_append_body_preserved_as_single_backslash_n` to `TestFromAC_EditTaskNormalization`. Asserts `mock_view.edit_task.call_args.kwargs["append_body"] == "want\\nliteral"` when input is `"want\\\\nliteral"`.
- Fix 2 (Scope): Removed out-of-scope `TestFromAC_ToolDescriptions` class (6 tests, tool description text explicitly excluded from this task).
- Total tests: 35 collected, 35 passed, 0 failed.
- Step 1b.1 — Direct-to-review advance: implementation already present in server.py; all new tests pass against current code; no implementation gaps remain. Builder skip: test-only retry, all tests green.
- Lint: ruff clean.
- Commit: `test: add append_body escape-conv test, remove out-of-scope ToolDescriptions (#1532, test-writer)`
- AC coverage: AC 1 (unit helper tests) ✓, AC 2 (5-param integration) ✓, AC 3 (guidance assertion) ✓, AC 4 (guidance ordering) ✓, AC 5 (escape convention all 5 params including append_body) ✓, AC 6 (passthrough) ✓, AC 7 (test file location + durable gate) ✓, AC 8 (RED gate) — normalization-path tests pass because implementation exists; passthrough regression guards correctly pass.
2026-05-13T15:01:07+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1532 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence review: builder was a pass-through handoff for a `type:test` retry; reviewer validated the task from test-writer evidence, direct file inspection, and an independent `quality-runner` rerun because the task body retained an explicit existing-proof scope.

| AC Line | Code / File Evidence | Test Evidence | Status |
|---|---|---|---|
| AC 1 | `tests/test_mcp_kanban_newline_norm_1531.py:133`; helper in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:87` | Helper behavior assertions at `tests/test_mcp_kanban_newline_norm_1531.py:167`, `tests/test_mcp_kanban_newline_norm_1531.py:183`, `tests/test_mcp_kanban_newline_norm_1531.py:190` | PASS |
| AC 2 | Normalization wired at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:375`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:411`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:508`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:511`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:600` | create_task `tests/test_mcp_kanban_newline_norm_1531.py:212`; edit_task body `tests/test_mcp_kanban_newline_norm_1531.py:246`; edit_task append_body `tests/test_mcp_kanban_newline_norm_1531.py:255`; end_work `tests/test_mcp_kanban_newline_norm_1531.py:305`; create_dr `tests/test_mcp_kanban_newline_norm_1531.py:344` | PASS |
| AC 3 | Guidance append paths at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:393`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:551`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:639` | Guidance assertions at `tests/test_mcp_kanban_newline_norm_1531.py:221`, `tests/test_mcp_kanban_newline_norm_1531.py:264`, `tests/test_mcp_kanban_newline_norm_1531.py:272`, `tests/test_mcp_kanban_newline_norm_1531.py:316`, `tests/test_mcp_kanban_newline_norm_1531.py:362` | PASS |
| AC 4 | Ordering-sensitive guidance append occurs after existing guidance collection in `edit_task` / `end_work` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:551`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:639` | Ordering proofs at `tests/test_mcp_kanban_newline_norm_1531.py:410`, `tests/test_mcp_kanban_newline_norm_1531.py:429` | PASS |
| AC 5 | Helper behavior at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:87`; call-site coverage at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:375`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:411`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:508`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:511`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:600` | create_task `tests/test_mcp_kanban_newline_norm_1531.py:229`; edit_task body `tests/test_mcp_kanban_newline_norm_1531.py:280`; edit_task append_body `tests/test_mcp_kanban_newline_norm_1531.py:289`; end_work `tests/test_mcp_kanban_newline_norm_1531.py:326`; create_dr `tests/test_mcp_kanban_newline_norm_1531.py:382` | PASS |
| AC 6 | No-op / no-guidance path driven by unchanged helper result and append logic in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:87`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:96`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:551`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:639` | Passthrough proofs at `tests/test_mcp_kanban_newline_norm_1531.py:459`, `tests/test_mcp_kanban_newline_norm_1531.py:473`, `tests/test_mcp_kanban_newline_norm_1531.py:487`, `tests/test_mcp_kanban_newline_norm_1531.py:501`, `tests/test_mcp_kanban_newline_norm_1531.py:517` | PASS |
| AC 7 | Task requires file placement and retains existing proof scope at `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:45`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:55`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:59` | File present at `tests/test_mcp_kanban_newline_norm_1531.py`; durable gate class at `tests/test_mcp_kanban_newline_norm_1531.py:543` and test at `tests/test_mcp_kanban_newline_norm_1531.py:553`; independent `quality-runner` rerun: 35 passed / 0 failed, durable gate passed | PASS |
| AC 8 | Refined RED semantics recorded at `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:56`, `.owlbear/kanban/tasks/1532-p1-01-tests-for-body-newline-normalization-at-mcp-kanban-ingress.md:67` | Task body preserves the original RED evidence, while the current rerun is expected to pass because implementation already exists and normalization-path assertions remain falsifiable | PASS |

- Independent verification: `quality-runner` scoped pass reported `tests/test_mcp_kanban_newline_norm_1531.py` with 35 passed, 0 failed; `ruff` clean; `test_durable_mcp_kanban_suite_no_new_failures` passed.
- Commit trace: matching test-writer commit subject found in `.git/logs/HEAD:2931` and `.git/logs/refs/heads/dev:2723`.

## Observations
- The prior blocking findings are resolved: `append_body` escape-convention coverage now exists at `tests/test_mcp_kanban_newline_norm_1531.py:289`, and the file tail now ends with `TestFromAC_ExistingDurableTestsUnchanged` at `tests/test_mcp_kanban_newline_norm_1531.py:543`; the superseded tool-description class is no longer present.
- Full `git diff` / `git status --porcelain` verification was not available in this tool surface because shell access was unavailable. Commit presence was verified via `.git/logs`, and current scoped file contents matched the handoff with no contradictory evidence.
2026-05-13T15:17:22+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Convention Mapping
Changed files: `tests/test_mcp_kanban_newline_norm_1531.py` only (test-writer work; builder was pass-through with zero file changes). Root `tests/` path matches no `serve/{pkg}/README.md` convention target. No public interface changes, no new commands, flags, or APIs introduced by this task.

### Checklist
| # | Item | Result | Evidence |
|---|------|--------|----------|
| 1 | README Verification | N/A | Test-only change in root `tests/`; no convention-mapped README target exists for this path |
| 2 | External Attribution | N/A | No external sources referenced in task body or review evidence |
| 3 | Research Doc | N/A | No research artifact for task #1532 |
| 4 | Deletion Detection | N/A | `TestFromAC_ToolDescriptions` class removed from test file only; internal test class with no README references |

### Scratch Cleanup
No `.owlbear/scratch/1532-*` files found — nothing to clean.
2026-05-13T15:31:12+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4596 passed, ~212 failed, 14 skipped; lint clean
- All 212 failures confirmed pre-existing in unrelated domains (cockpit_view FileNotFoundError on deleted test files, engine_accessor_migration stale accessor assertions, server status-names NoneType, ideation_diagram bridge element names). Task changed only `tests/test_mcp_kanban_newline_norm_1531.py` and zero source files — no causal path to any failure.
- Task-scoped rerun: 35 passed, 0 failed
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single test file in root `tests/`, scoped to mcp-kanban domain per tags)
- purpose match: PASS (tests cover newline normalization helper + 5 MCP parameter integration points, matching task summary)
- extraneous scope: none (out-of-scope ToolDescriptions class removed in 3rd cycle per reviewer findings)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC required 3 review cycles to stabilize: (1) AC 8 vs AC 6 conflict — passthrough tests passing in RED was correct TDD but AC wording was ambiguous, (2) AC 5 missing `append_body` escape-convention parameter, (3) out-of-scope tool-description tests not excluded from AC. Architect refined successfully each time, but initial AC quality caused two wasted review cycles.

### Commit Integrity
- upstream commit presence: PASS (`66da8e32 test: add append_body escape-conv test, remove out-of-scope ToolDescriptions (#1532, test-writer)` plus 4 prior commits for the file)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- AC quality score 3/5: -.03

### Confidence: 0.97
### Action: archive