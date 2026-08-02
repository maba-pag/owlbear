---
id: 1089
title: 'A-09: RED — guidance + error mapping tests'
status: archived
priority: medium
created: 2026-04-21 10:54:09.278833+00:00
updated: 2026-04-28T04:21:16.990266+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:red
parent: 1045
depends_on:
- 1083
- 1085
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §7 "guidance field", paper-integration.md §3.6–§3.7
Module: `serve/mcp-kanban/tests/test_mcp_guidance.py`

Test guidance field passthrough and the KanbanError → MCP ToolError error-mapping layer. Guidance is an engine-generated `list[str]` on every response envelope — the adapter must pass it through unmodified. Error mapping: every KanbanError subclass (ValidationError, NotFoundError, ConcurrencyError) maps to MCP `ToolError(user_message)`. Tests mock AgentView.

## Acceptance Criteria

- [ ] Guidance passthrough: engine returns guidance strings → adapter includes them in MCP response unmodified
- [ ] show_task section occurrence count guidance (AC12) passes through
- [ ] pick_tasks dispatch hints pass through
- [ ] create_task/edit_task body size warning (>100 KB) passes through
- [ ] move_task / end_work skip-transition warning passes through (AC-NEW-5); reject path requires a claimed task precondition per engine.py:3031-3035
- [ ] end_work(outcome="block") Action-Request/Decision-Request hint passes through (AC-NEW-4)
- [ ] Error mapping: ValidationError → ToolError with exact `user_message` passthrough ("title must not be empty"); no code on wire per §7
- [ ] Error mapping: NotFoundError → ToolError with exact `user_message` passthrough ("Task '{id}' not found")
- [ ] Error mapping: ConcurrencyError → ToolError with `user_message` prefix "Task '{id}' is already claimed by another agent"; no code on wire

## Architecture Review (loop-breaker pass 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Guidance passthrough + error mapping for one MCP adapter layer |
| Interface clarity | PASS | AC now explicit about exact user_message assertions |
| Dependency correctness | PASS | #1083, #1085 archived (done) |
| Module layering | PASS | Tests MCP adapter → engine boundary correctly |
| TDD compliance | PASS | This IS the RED phase task; RED was met historically (test-writer notes) |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | Guidance and error mapping are needed MCP surface features |
| Pattern consistency | PASS | Follows TestFromAC pattern |
| Security surface | PASS | No new security boundaries |
| Single domain | PASS | MCP adapter domain only |

### Loop-Breaker Diagnosis (pass 2)

Four review FAILs all cite the same root cause: error mapping assertions are too loose. The prior loop-breaker fixed two concrete test-file bugs (stale constant, unclaimed fixture) but did not address assertion specificity for error mapping. The reviewer has been consistent about this since review 1.

Root cause: the original AC said "ValidationError → ToolError (user_message only, no code on wire per §7)" without specifying exact equality. The test-writer wrote loose substring/keyword checks that technically satisfy the AC but don't prove exact passthrough. The reviewer correctly identifies this as false-green-prone.

Fix: refine error mapping AC lines to require exact `user_message` assertions. This removes ambiguity and gives the test-writer a clear bar.

Additionally, the AC line "All tests fail (RED phase)" has been removed. This was a one-time test-writer requirement that was met (11 failing tests recorded before builder work). The reviewer was counting it as FAIL because the current state is GREEN, which is expected after builder implementation. The `tdd:red` tag remains as the task-type marker.

### AC Refinement Summary
1. Error mapping AC lines 7-9: added "exact user_message passthrough" requirement with specific expected strings.
2. ConcurrencyError: specified prefix-match instead of exact equality (the `claimed_at_hint` suffix is dynamic and depends on the rival claim's timestamp).
3. Removed "All tests fail (RED phase)" AC line — historical requirement already met.

### Concrete Defect Fixes (test-writer: apply all three)

**Fix 1 — ValidationError exact equality (line 424):**
Replace the loose keyword check with exact equality:
```python
assert str(exc_info.value) == "title must not be empty"
```
Keep the `ERR_` absence check as a belt-and-suspenders guard.

**Fix 2 — NotFoundError exact equality (line 447):**
Replace the broad message check with exact equality:
```python
assert str(exc_info.value) == "Task '9999' not found"
```

**Fix 3 — ConcurrencyError prefix-match (line 472):**
Replace the fragment check with a prefix assertion (claimed_at_hint is dynamic):
```python
error_text = str(exc_info.value)
assert error_text.startswith("Task '1' is already claimed by another agent")
```
Keep the `ERR_ALREADY_CLAIMED not in error_text` check.

### Non-blocking notes
- Reject-path sentinel: the current test implicitly proves AgentView is the source (adapter fallback returns [] for reject), so the sentinel patch is pattern-consistency nice-to-have, not a blocker.
- Sibling suite `test_mcp_lifecycle_tools.py:348` mocks `user_message="ERR_BLOCK_REASON_REQUIRED: ..."` — this is a mock setup bug in another task, not a wire contract contradiction. The real engine uses a clean user_message. Out of scope for #1089.
- Test file docstring header "All tests must FAIL (RED phase)" and per-test "FAIL path (RED)" narratives are historical documentation. Non-blocking — update if desired.

### Challenge Results
- Challenger: block (confidence 0.37)
- Architect response: REBUTTED
  - "Speculative approval": standard REFINE → APPROVE pattern. Architect provides guidance, test-writer applies it. That's how loop-breakers work.
  - "RED contract drift": ACCEPTED — removed the AC line and clarified the `tdd:red` tag is a type marker.
  - "ConcurrencyError exact equality underspecified": ACCEPTED — changed to prefix-match to handle dynamic claimed_at_hint.
  - "Sibling suite contradiction": REBUTTED — mock bug in another suite, not a real wire contract conflict.
  - "Reject sentinel misprioritized": ACCEPTED — downgraded to non-blocking.

### Verdict: REFINE → APPROVE
### Action Taken: Refined 3 error mapping AC lines with exact user_message requirements. Removed stale RED AC line. Added 3 concrete test fixes. Advancing to todo.
[[2026-04-28]]
Architecture review complete (loop-breaker pass 2). Refined 3 error mapping AC lines with exact user_message requirements: ValidationError exact equality, NotFoundError exact equality, ConcurrencyError prefix-match (dynamic claimed_at_hint). Removed stale "All tests fail (RED phase)" AC line — historical requirement already met. Added 3 concrete test fixes. Challenger rebutted (block @ 0.37). Advancing to todo.
[[2026-04-28]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_guidance_1089.py
- Classes: TestFromAC_GuidancePassthrough, TestFromAC_ErrorMapping
- Retry: applied 3 architect-directed assertion fixes (loop-breaker pass 2)
  - Fix 1: ValidationError → exact equality `str(exc_info.value) == "title must not be empty"` + ERR_ guard
  - Fix 2: NotFoundError → exact equality `str(exc_info.value) == "Task '9999' not found"`
  - Fix 3: ConcurrencyError → prefix-match `error_text.startswith("Task '1' is already claimed by another agent")` + ERR_ALREADY_CLAIMED guard
- Total: 11 tests, all PASS (GREEN — builder already implemented; architect removed "all tests fail" AC line as historical requirement already met)
- ruff: clean
- AC coverage: all 9 AC lines covered
[[2026-04-28]]
## Builder Notes
- Implementation: no code changes required; validated existing adapter behavior already satisfies refined AC for guidance passthrough and KanbanError -> ToolError user_message mapping.
- Files changed: none.
- Tests: 11/11 passed in task-scoped suite (`serve/mcp-kanban/tests/test_mcp_guidance_1089.py`); additional regression sanity: 42/42 passed across guidance + lifecycle suites.
- Coverage: `owlbear_mcp_kanban.server` measured at 51% (task-scoped) / 53% (with adjacent lifecycle suite).
- Ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, and `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`.
- Evidence summary: guidance passthrough and exact/prefix error-message mapping behavior match AC lines 1-9; no fallback-path regression observed in scoped/adjacent verification.
- Fixes applied: none (existing implementation already GREEN against current AC/tests).
[[2026-04-28]]
## Review Evidence
### Test Results
- `pytest`: 11 passed, 0 failed (`serve/mcp-kanban/tests/test_mcp_guidance_1089.py`) via quality-runner.

### Lint
- `ruff`: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`.

### Coverage
- `owlbear_mcp_kanban.server`: 51% on the task-scoped run.
- Reviewer note: builder reported no source edits; this low whole-module figure is residual context for the large adapter module, not a blocker for this task-owned slice.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Guidance passthrough | `test_show_task_guidance_passes_through_unmodified` | Yes — `show_task` returns the AgentView payload directly (`server.py:300`) and the test asserts exact list equality (`test_mcp_guidance_1089.py:233-255`). | COVERED |
| show_task section occurrence count guidance | `test_show_task_section_occurrence_count_guidance` | Yes — exact equality on the duplicate-section guidance string (`test_mcp_guidance_1089.py:213-232`) against the direct `show_task` path (`server.py:300`). | COVERED |
| pick_tasks dispatch hints | `test_pick_tasks_dispatch_hints_guidance` | Yes — exact equality on the guidance list (`test_mcp_guidance_1089.py:260-278`) against direct adapter return (`server.py:567`). | COVERED |
| create_task/edit_task body size warning | `test_create_task_body_size_warning_guidance`, `test_edit_task_body_size_warning_guidance` | Yes — both assert exact warning equality (`test_mcp_guidance_1089.py:279-316`) against direct adapter returns (`server.py:311`, `server.py:398`). | COVERED |
| move_task / end_work reject skip-transition warning | `test_move_task_skip_transition_warning_guidance`, `test_end_work_reject_skip_transition_warning_guidance` | Yes — `move_task` sentinel-patches fallback guidance (`test_mcp_guidance_1089.py:317-341`); `end_work(reject)` exact-equality proof (`test_mcp_guidance_1089.py:342-364`) is sufficient because fallback guidance is computed at `server.py:557`, and `collect_guidance` only emits block/success/move guidance (`guidance.py:22-55`, `guidance.py:78`). | COVERED |
| end_work(outcome="block") AR/DR hint | `test_end_work_block_action_request_hint_guidance` | Yes — fallback guidance is sentinel-patched and exact equality is asserted (`test_mcp_guidance_1089.py:370-396`) against `end_work` (`server.py:486`). | COVERED |
| ValidationError -> ToolError exact `user_message`; no code on wire | `test_validation_error_maps_to_tool_error` | Yes — exact message equality plus `ERR_` absence guard (`test_mcp_guidance_1089.py:409-430`) against `create_task`/`ToolError(exc.user_message)` (`server.py:311`). | COVERED |
| NotFoundError -> ToolError exact `user_message` | `test_not_found_error_maps_to_tool_error` | Yes — exact message equality (`test_mcp_guidance_1089.py:431-449`) against `show_task` + `_map_kanban_error` (`server.py:69`, `server.py:300`). | COVERED |
| ConcurrencyError -> ToolError prefix + no code on wire | `test_concurrency_error_maps_to_tool_error_user_message_only` | Yes — required prefix and `ERR_ALREADY_CLAIMED` absence are asserted (`test_mcp_guidance_1089.py:450-473`) against `start_work` mapping (`server.py:449`). | COVERED |

#### Security Review
- No issues in scope. The adapter entry points delegate to engine/AgentView and map `KanbanError.user_message` to `ToolError` (`server.py:69`, `server.py:300`, `server.py:311`, `server.py:337`, `server.py:398`, `server.py:449`, `server.py:486`, `server.py:567`). No shell execution, path construction, or unsafe deserialization was found.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_GuidancePassthrough` | Builder notes report no changed files; current assertions remain exact-equality and sentinel-backed where fallback exists. | PRESERVED |
| `TestFromAC_ErrorMapping` | Builder notes report no changed files; current assertions remain exact-equality/prefix plus no-`ERR_` guards. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality/prefix/no-`ERR_` assertions across `test_mcp_guidance_1089.py:227`, `:255`, `:273`, `:292`, `:311`, `:336`, `:364`, `:395`, `:423`, `:445`, `:468`. |
| Negative/error-path coverage | STRONG | Guidance passthrough includes fallback-sensitive cases for move/block/reject; error mapping covers ValidationError, NotFoundError, and ConcurrencyError. |
| Manual mutation reasoning | STRONG | Wrong guidance source, transformed list, wrong message text, or leaked machine code would fail the task suite. |
| Test independence | STRONG | Fixtures create fresh temp boards (`test_mcp_guidance_1089.py:136`, `:157`, `:167`, `:182`, `:194`). |
| Descriptive names | STRONG | Test names map directly to AC behavior and failure mode. |

#### Data Safety
- No issues in scope. The reviewed code adds no new persistence, concurrency control, or unbounded-resource behavior; it delegates to existing engine/view methods.

#### Implementation-Aware Gaps
- No task-scoped gaps. Code-reader initially flagged `end_work(reject)` passthrough as potentially lax, but reviewer verification showed the fallback cannot synthesize reject skip guidance because `collect_guidance` only handles block/success/move outcomes. A passthrough regression would therefore fail `test_end_work_reject_skip_transition_warning_guidance`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` still contains stale RED-phase header/docstrings. The executable assertions remain valid.
- Whole-module coverage remains 51% on the scoped run because `owlbear_mcp_kanban.server` is much larger than this task slice.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Guidance passthrough | `show_task` direct return (`server.py:300`) + exact list equality (`test_mcp_guidance_1089.py:233-255`) | `test_show_task_guidance_passes_through_unmodified` | PASS |
| show_task occurrence-count guidance | Duplicate-section guidance exact equality (`test_mcp_guidance_1089.py:213-232`) | `test_show_task_section_occurrence_count_guidance` | PASS |
| pick_tasks dispatch hints | Direct adapter return (`server.py:567`) + exact equality (`test_mcp_guidance_1089.py:260-278`) | `test_pick_tasks_dispatch_hints_guidance` | PASS |
| create/edit body-size warning | Exact warning equality in both task methods (`test_mcp_guidance_1089.py:279-316`) | `test_create_task_body_size_warning_guidance`, `test_edit_task_body_size_warning_guidance` | PASS |
| move_task / end_work reject skip warning | Sentinel-backed move proof (`test_mcp_guidance_1089.py:317-341`) plus reject-path precondition (`:355`) and exact equality (`:364`); fallback reject guidance absent by helper contract (`guidance.py:22-55`, `guidance.py:78`) | `test_move_task_skip_transition_warning_guidance`, `test_end_work_reject_skip_transition_warning_guidance` | PASS |
| end_work(block) AR/DR hint | Sentinel-backed exact equality (`test_mcp_guidance_1089.py:370-396`) | `test_end_work_block_action_request_hint_guidance` | PASS |
| ValidationError exact `user_message`; no code | Exact equality + `ERR_` absence (`test_mcp_guidance_1089.py:409-430`) | `test_validation_error_maps_to_tool_error` | PASS |
| NotFoundError exact `user_message` | Exact equality (`test_mcp_guidance_1089.py:431-449`) | `test_not_found_error_maps_to_tool_error` | PASS |
| ConcurrencyError prefix + no code | Prefix + `ERR_ALREADY_CLAIMED` absence (`test_mcp_guidance_1089.py:450-473`) | `test_concurrency_error_maps_to_tool_error_user_message_only` | PASS |

### Deductions
- `-0.04`: whole-module coverage remains 51% on the task-scoped run.
- `-0.02`: stale RED-phase comments remain in the task test file.

### Verdict
- PASS
- Confidence: 0.94

### Action
- Advance to `docs`.

### Post-task Reflection
- Code-reader surfaced a plausible false-green concern on `end_work(reject)`, but the real helper contract in `guidance.py` ruled it out.
- This review was a test-only slice against an unchanged adapter implementation, so AC proof quality mattered more than diff size.
- Task-scoped suites on large adapter modules can still show low whole-module coverage; keep that as residual risk rather than inventing unrelated scope.
[[2026-04-28]]
## Docs Gate

### Step 0 Checks
- Task status: `docs` ✓
- `## Review Evidence` section: present ✓ (PASS @ 0.94, reviewed by quality-runner)

### Scope Classification

**Changed-files set (from Builder Notes):**
- `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` — new test file (builder's only deliverable)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — referenced in review but builder explicitly states "Files changed: none"

Both files are OUT of IN-scope: test files are not IN-scope; `server.py` was not modified.

| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` | OUT (test file) | N/A |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | OUT (not changed) | N/A |

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder: no code changes; no behavior/API/CLI/config change. No IN-scope prose docs reference this test slice. |
| 2 | Module docstrings | No | N/A | `server.py` not modified; no new Python modules created. |
| 3 | External attribution | No | N/A | No external patterns cited in task body or review. |
| 4 | Research doc | No | N/A | No `.owlbear/research/*1089*.md` exists; no research phase noted. |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/mcp-kanban/src/**`; `mcp-topology.excalidraw` describes `serve/mcp-*/src/**`. Neither glob matches `tests/**`. No source files changed, so no describes-match triggers. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

**No docs impact.** All items resolve to N/A.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1089-*` scratch files found)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Guidance passthrough | `test_show_task_guidance_passes_through_unmodified` — sentinel-patched AgentView + exact list equality (`test_mcp_guidance_1089.py:248-256`) | PASS |
| show_task occurrence-count guidance | `test_show_task_section_occurrence_count_guidance` — exact equality (`test_mcp_guidance_1089.py:213-232`) | PASS |
| pick_tasks dispatch hints | `test_pick_tasks_dispatch_hints_guidance` — exact equality (`test_mcp_guidance_1089.py:260-278`) | PASS |
| create/edit body-size warning | `test_create_task_body_size_warning_guidance`, `test_edit_task_body_size_warning_guidance` — exact warning equality (`test_mcp_guidance_1089.py:279-316`) | PASS |
| move_task / end_work reject skip warning | `test_move_task_skip_transition_warning_guidance`, `test_end_work_reject_skip_transition_warning_guidance` — sentinel-backed + exact equality (`test_mcp_guidance_1089.py:317-364`) | PASS |
| end_work(block) AR/DR hint | `test_end_work_block_action_request_hint_guidance` — sentinel-patched exact equality (`test_mcp_guidance_1089.py:370-396`) | PASS |
| ValidationError exact user_message; no code | `test_validation_error_maps_to_tool_error` — `str(exc_info.value) == "title must not be empty"` + ERR_ absence guard (`test_mcp_guidance_1089.py:423-430`) | PASS |
| NotFoundError exact user_message | `test_not_found_error_maps_to_tool_error` — `str(exc_info.value) == "Task '9999' not found"` (`test_mcp_guidance_1089.py:445`) | PASS |
| ConcurrencyError prefix + no code | `test_concurrency_error_maps_to_tool_error_user_message_only` — prefix assertion + ERR_ALREADY_CLAIMED absence (`test_mcp_guidance_1089.py:468-473`) | PASS |

### Test Results
- pytest (full suite): 2756 passed, 137 failed, 4 skipped. **0 failures in task scope** (11/11 pass). 137 failures are pre-existing (115) + other tasks (#1086, #1090: 22 new).
- ruff: 8 findings, **0 in task scope**. All in unrelated modules (knowledge, memory, orchestrator).

### Architect Quality: 4/5
AC required 2 loop-breaker passes before reaching adequate specificity — original error mapping AC was too loose, reviewer correctly flagged it repeatedly. Final AC is specific with exact expected strings and concrete test fixes. Effective root-cause diagnosis and refinement, but iteration cost was avoidable with stricter initial AC.

### Deduction Breakdown
- AC lines with no evidence: 0 → no deduction
- Lint violations in scope: 0 → no deduction
- AC quality ≤ 3: No (4/5) → no deduction
- Missing reviewer evidence: No (detailed, PASS @ 0.94) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 614764ba | chore(kanban) | 1089 task file | #1089 |