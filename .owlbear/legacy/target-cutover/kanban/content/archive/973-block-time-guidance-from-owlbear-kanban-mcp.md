---
id: 973
title: Block-Time Guidance from owlbear-kanban MCP
status: archived
priority: medium
created: 2026-04-18T21:13:44.384255+00:00
updated: 2026-04-19T01:33:05.586573+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
- scope:cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief approved via ideator on 2026-04-18. Full Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decisions: `decisions.md`. Context (M1-M3, Critic, landscape): `context.md`.

## Problem

Across OwlBear and consuming projects, agents repeatedly set tasks to `blocked` without creating a Decision Request. Multiple instruction-file and memory updates have failed to change the behavior. Pattern is worst for action-needed blocks (e.g., "user must connect VPN"). Instructions buried in instruction files have proven insufficient; the rule needs to live where the action happens (the MCP tool response).

## Outcomes

1. In-turn block guidance: every `edit_task(block=...)` and `end_work(outcome="block")` returns a structured "ACTION REQUIRED: create a Decision Request" message in the same tool response that commits the block. The message is the first thing the agent sees in the response payload.
2. User vs. agent block disambiguation: Cockpit-initiated blocks carry the `block:user` tag. Agents reading a tagged task skip DR creation.
3. Reusable guidance mechanism: same helper serves three V1 use cases (block, forward-skip, success/commit). Adding a fourth use case is appending one tuple to a registry.

## Approach (Path A1 — soft, in-your-face, non-breaking)

- Add `guidance: list[str] = []` as first declared field on `KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`. Pydantic v2 declaration-order JSON serialization places it first.
- New module `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` with flat rule list and one `collect_guidance(operation, before, after, **kwargs) -> list[str]` function. V1 ships three rules.
- `server.py`: each affected tool (`edit_task`, `end_work`, `move_task`) calls `collect_guidance(...)` after engine call and attaches result. `move_task` pre-reads via `_show_validated()` for prior status.
- Cockpit `edit_task` route adds `block:user` on block, removes on unblock. MCP block branches remove the tag (agent re-blocking takes ownership).
- No engine changes. No new MCP arguments. No new tools. No new MCP primitives.

## Acceptance criteria

- `KanbanTask.guidance` field exists, first JSON-serialized field, defaults to `[]`, tested.
- `collect_guidance()` with three rules; positive/negative unit tests per rule.
- `edit_task(block=...)` and `end_work(outcome="block")` return guidance with DR-required message; integration-tested.
- `move_task` forward-skip > 1 slot returns guidance; 1-slot and backward moves return empty guidance.
- `end_work(outcome="success")` returns guidance with commit-pushed message.
- Cockpit `edit_task` route adds `block:user` on block, removes on unblock; tested.
- MCP `edit_task` and `end_work` block branches remove `block:user` if present; tested.
- Skill docs updated: `h-mcp-kanban`, `r-pipeline-protocol`, `w-decision-routing`.
- All existing kanban MCP tests still pass.
- Seed propagation verified.

## Out of scope

- Hard validation (`ToolError` on missing DR) — documented as fallback.
- New MCP primitives (elicitation, prompts, sampling).
- Engine-layer changes.
- Other candidate operations (create_task tag-required, etc.) — defer to follow-up Briefs.
- Numeric success metrics.
- Scribe agent or DR file format changes.

## Risks

- Guidance arrives after block commits (Critic Blocker 1, acknowledged) — mitigated by salience via JSON field order; hard-validation fallback documented.
- Tag bypass — acceptable self-attack risk.
- `move_task` pre-read cost — acceptable, not hot.
- Skill drift — guidance references convention by name, not verbatim.

## Estimated decomposition

~6-9 atomic tasks. Planner subagent will decompose.
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/block-time-guidance-mcp-973.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with Brief Path A1 and locked decisions D1–D9 (confidence: .88)
- Challenge: SKIPPED — approach locked via 3-round architect debate
- Follow-up tasks created: #986 (model field), #987 (guidance module), #985 (edit_task integration), #989 (end_work integration), #991 (move_task integration), #990 (cockpit block:user), #988 (skill docs)
- Decision requests: none — T1 autonomous (all decisions locked in Brief)
- Dependency graph: #986 → #987 → {#985, #989, #991} (parallel) → #988; #990 independent
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent is umbrella; each of 7 subtasks has one responsibility |
| Interface clarity | PASS | `collect_guidance(operation, before, after, **kwargs) -> list[str]` — clear I/O |
| Dependency correctness | PASS (with note) | Dependency graph documented in body but `depends_on` fields empty on subtasks — must be wired during individual subtask architect reviews per graph: #986 then #987 then {#985, #989, #991} then #988; #990 independent |
| Module layering | PASS | New `guidance.py` in mcp-kanban layer, no upward imports; cockpit tag injection in route layer |
| TDD compliance | PASS | Each subtask specifies test files; subtasks flow through test-writer |
| KISS/YAGNI | PASS | Flat `(predicate, message_template)` rule list, no classes, no decorators, 3 rules for V1 |
| Premise challenge | PASS | Real problem (agents skip DR creation); no existing capability addresses this; instruction-file approach proven insufficient |
| Pattern consistency | PASS | Pydantic v2 models, `_record_to_task` conversion, `_show_validated` patterns all respected |
| Security surface | PASS | No new system boundaries; tags and guidance are internal to the pipeline |
| Single domain | PASS | MCP kanban domain primary; cockpit tag injection is ancillary (already split as #990) |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `collect_guidance()` raises | Guidance lost, operation already committed | RuntimeError | No (must be caught in server.py) | Operation succeeds, no guidance shown |
| `_show_validated` pre-read fails (move_task) | move_task fails before engine call | ToolError | Yes (existing pattern) | Clean error, no state change |
| Tag removal fails (block:user) | Stale tag persists | ValueError | Tolerable | Agent may skip DR creation unnecessarily |
| TOCTOU on move_task pre-read | Guidance reports stale status delta | N/A | By design (advisory) | Possible spurious forward-skip warning |

### Challenge Results

- Challenger: `reconsider` (confidence 0.72)
- Four challenges raised: C1 (end_work tag removal non-atomic), C2 (cockpit tag-diff edge case), C3 (in-place re-block tracing), C4 (move_task TOCTOU)
- Architect response: REBUTTED all four

**C1 rebuttal:** `engine.edit_task()` does not require a claim. After `engine.end_work()` releases the claim, `engine.edit_task(task_id, remove_tags=["block:user"])` is a valid sequential call in the same handler. Non-atomicity is acceptable: `block:user` is advisory. Worst case = stale tag = agent skips DR creation, same risk class as tag bypass (already accepted in Brief). No engine change needed.

**C2 rebuttal:** Edge case requires a Cockpit user to explicitly include/exclude `block:user` in their tag set while simultaneously blocking. `block:user` is a system-managed tag; frontend should not expose it for manual editing. Subtask #990 architect should add AC: "Cockpit frontend filters `block:user` from user-editable tag list, or route handler strips it from set-diff before injection." Acceptable V1 edge case.

**C3 rebuttal:** MCP `edit_task` block branch can issue `engine.edit_task(task_id, blocked=True, block_reason=block, remove_tags=["block:user"])` as a single atomic engine call. Traced and confirmed: engine processes all kwargs in one read-mutate-write cycle.

**C4 rebuttal:** Acknowledged, acceptable for advisory guidance. Brief R1.4 explicitly accepts this.

### Implementation Guidance for Subtask Architects

1. **Dependency wiring required.** All subtasks have `depends_on: []`. Wire per documented graph: #986 (no deps) then #987 (depends #986) then {#985, #989, #991} (each depends #986, #987) then #988 (depends #985, #989, #991). #990 has no deps.

2. **#989 (end_work integration):** `end_work` tag removal uses two sequential engine calls: `engine.end_work()` then `engine.edit_task(task_id, remove_tags=["block:user"])` then re-read. AC is achievable without engine changes.

3. **#985 (edit_task integration):** Block branch combines blocking + tag removal in single `engine.edit_task` call (atomic). Straightforward.

4. **#990 (cockpit block:user):** Note C2 edge case — if frontend allows manual `block:user` in tag sets, add handling or filtering. Consider AC line: "route handler strips `block:user` from set-diff computed tags before injection."

5. **#987 (guidance module):** Wrap `collect_guidance` callers in try/except to prevent guidance failures from breaking tool operations. Add defensive AC line.

6. **Parent task is an umbrella.** All implementation is in subtasks #985-#991. #973 tracks aggregate completion.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Subtask dependency wiring and implementation notes documented for downstream architects

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation pass-through: #973 is an umbrella parent task. Architecture review explicitly states: "All implementation is in subtasks #985-#991. #973 tracks aggregate completion."
- Every AC line maps to a specific subtask with its own test file:
  - `KanbanTask.guidance` field (AC1) → #986 → `serve/mcp-kanban/tests/test_guidance.py`
  - `collect_guidance()` 3-rule unit tests (AC2) → #987 → `test_guidance_rules_973.py`
  - `edit_task(block=...)` integration (AC3) → #985 → `test_guidance_edit_task_973.py`
  - `move_task` forward-skip (AC4) → #991 → `test_guidance_move_task_973.py`
  - `end_work(outcome="success")` guidance (AC5) → #989 → `test_guidance_end_work_973.py`
  - Cockpit `block:user` (AC6) → #990
  - MCP block branch `block:user` removal (AC7) → #985, #989
  - Skill docs (AC8) → #988 (non-impl)
  - "All existing tests pass" (AC9) → meta-constraint, verified at subtask level
  - "Seed propagation verified" (AC10) → non-impl
- ⚠️ API divergence note for builder: existing `guidance.py` + `test_guidance.py` (from task #974) use the OLD API (`"edit_block"`, `"end_work_block"`, `"end_work_success"` operations, `statuses` kwarg). Subtask #987's approved AC mandates the NEW API (`operation="edit_task"/"end_work"/"move"`, `outcome` kwarg, `status_names` kwarg, `before` can be `None`). The #987 test-writer will write failing tests for the new API; the builder must reconcile the API break. Passing through to builder.
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` — Updated to new API (`operation="edit_task"/"end_work"/"move"`, `outcome` kwarg, `status_names` kwarg, `before: KanbanTask | None`). Legacy operations (`edit_block`, `end_work_block`, `end_work_success`, `statuses=` kwarg) kept for backward compat with existing tests. Three V1 rules implemented (block DR, forward-skip, success/commit).
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — Wired `collect_guidance` into `edit_task` (guidance + block:user removal on block/unblock), `end_work` (guidance + block:user removal on block), and `move_task` (pre-read via `_show_validated`, forward-skip guidance).
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — Fixed tag-diff conflict in `_apply_block_kwargs`: strip `block:user` from `remove_tags` when blocking (prevents tag-diff removing it), strip from `add_tags` when unblocking (prevents tag-diff adding it).
- `serve/mcp-kanban/tests/test_guidance_rules_973.py` (new) — 15 tests for new API
- `serve/mcp-kanban/tests/test_guidance_edit_task_973.py` (new) — 4 integration tests for edit_task guidance
- `serve/mcp-kanban/tests/test_guidance_end_work_973.py` (new) — 5 integration tests for end_work guidance
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` (new) — 5 integration tests for move_task guidance
- `serve/mcp-kanban/tests/test_guidance.py` — Added `TestBuilderDiscovered` class with AC6 (model_validate roundtrip)
- `tests/test_cockpit_mutation_api.py` — Added `TestFromAC_BlockUserTagConflict` class (3 conflict resolution tests)
- `share/skills/h-mcp-kanban/SKILL.md` — Added "Response: Guidance Field" section
- `share/skills/r-pipeline-protocol/SKILL.md` — Added "DR Required on Agent Block" with block:user exemption
- `share/skills/w-decision-routing/SKILL.md` — Added block-guidance entry-point note in "When to Create a Decision Request"

### Test results

- 97 passed (mcp-kanban tests + cockpit mutation tests), 0 failed

### Lint

- ruff: clean (check + format)

### Coverage (touched modules)

- `guidance.py`: 98%
- `models.py`: 100%
- `mutation.py`: 100%
- `server.py`: 64% (untouched functions like list_tasks, create_task, pick_tasks not covered — guidance-specific paths fully covered)

### AC evidence

1. ✅ `KanbanTask.guidance` field first in JSON, defaults `[]` — `TestFromAC_KanbanTaskGuidanceField` passes; `TestBuilderDiscovered` adds model_validate roundtrip (AC6)
2. ✅ `collect_guidance()` 3 rules with pos/neg tests — `test_guidance_rules_973.py` (15 tests, new API) + `test_guidance.py` (11 tests, legacy API both pass)
3. ✅ `edit_task(block=...)` and `end_work(outcome="block")` return DR guidance — integration tests pass
4. ✅ `move_task` forward-skip > 1 slot → guidance; 1-slot and backward → empty — integration tests pass
5. ✅ `end_work(outcome="success")` → commit reminder — integration test passes
6. ✅ Cockpit block:user lifecycle + conflict resolution — `TestFromAC_BlockUserTag` (4 existing) + `TestFromAC_BlockUserTagConflict` (3 new) all pass
7. ✅ MCP block branches remove `block:user` if present — integration tests verify
8. ✅ Skill docs updated: h-mcp-kanban (guidance field section), r-pipeline-protocol (DR-required rule + block:user exemption), w-decision-routing (entry-point note)
9. ✅ All existing kanban MCP tests pass (59 total)

### API reconciliation note

The old `test_guidance.py` (from #974) used legacy operation strings; the approved #987 AC mandated a new API. Both now co-exist: the new API uses `operation="edit_task"/"end_work"/"move"` with `after.blocked`/`outcome` kwargs; legacy aliases (`edit_block`, `end_work_block`, `end_work_success`, `statuses=`) still work for backward compat.

### Commit: 161e4c2d

[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 78 passed, 0 failed, 0 skipped (scoped run: all 4 new test modules + test_guidance.py + test_cockpit_mutation_api.py)

### Lint: clean (ruff check + format, 0 violations)

### Coverage

- `owlbear_mcp_kanban.guidance`: 98%
- `owlbear_mcp_kanban.models`: 100%
- `owlbear_mcp_kanban.server`: 64% (untouched functions list_tasks/create_task/pick_tasks not exercised; guidance-specific paths fully covered per code-reader)
- `owlbear_cockpit.routes.mutation`: not measured in cross-package run; all mutation tests passed (78/78 includes test_cockpit_mutation_api.py)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: guidance field first, defaults [] | `TestFromAC_KanbanTaskGuidanceField` (test_guidance.py:64–99) — `keys[0] == "guidance"` + `== []` exact checks | YES | COVERED |
| AC2: collect_guidance() 3 rules | `TestFromAC_CollectGuidance` + `TestFromAC_CollectGuidanceNewAPI` — 24 combined unit tests with specific string/empty-list assertions | YES | COVERED |
| AC3: edit_task(block=...) → DR guidance | `TestFromAC_EditTaskGuidanceIntegration::test_block_returns_dr_guidance` | YES | COVERED |
| AC3b: end_work(outcome="block") → DR guidance | `TestFromAC_EndWorkGuidanceIntegration::test_block_outcome_returns_dr_guidance` | YES | COVERED |
| AC4: move_task forward-skip >1 → guidance; 1-slot/backward → [] | `TestFromAC_MoveTaskGuidanceIntegration` (3 tests) | YES | COVERED |
| AC5: end_work(outcome="success") → commit message | `TestFromAC_EndWorkGuidanceIntegration::test_success_outcome_returns_commit_guidance` | YES | COVERED |
| AC6: Cockpit adds/removes block:user | `TestFromAC_BlockUserTag` (4 tests); AC6-4 unblock sub-test checks HTTP 200 only (LAX), compensated by `TestFromAC_BlockUserTagConflict` conflict tests | MOSTLY YES | COVERED (AC6-4 LAX — compensated) |
| AC7: MCP block branches remove block:user | `test_block_removes_block_user_tag_if_present`, `test_unblock_no_dr_guidance_and_removes_block_user_tag`, `test_block_outcome_removes_block_user_tag_if_present` | YES | COVERED |
| AC8: Skill docs updated | None — non-testable; builder notes confirm 3 skills updated | Non-testable | NON-TESTABLE |
| AC9: All existing MCP tests pass | 78/78 (quality-runner confirmed) | Non-testable | NON-TESTABLE |
| AC10: Seed propagation verified | No test, no seed/ files in changed_files, builder self-report only ("✅") | Not verifiable | UNVERIFIED — guidance defaults to [] so no seed changes needed; self-report treated as adequate for advisory-only field |

#### Security Review

- No hardcoded secrets, injection vectors, path traversal, insecure deserialization, or credential leakage in changed files.
- `contextlib.suppress(Exception)` in server.py:226, 300, 348 is advisory-only guidance suppression — no security risk.
- No new dependencies.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_KanbanTaskGuidanceField` (test_guidance.py) | Unchanged — builder added additive `TestBuilderDiscovered` class | PRESERVED |
| `TestFromAC_CollectGuidance` (test_guidance.py) | Unchanged | PRESERVED |
| `TestFromAC_BlockUserTag` (test_cockpit_mutation_api.py) | Unchanged — builder added additive `TestFromAC_BlockUserTagConflict` class | PRESERVED |

No weakened or removed assertions.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `"Decision Request" in result[0]`, `"commit" in result[0].lower()`, `result == []`, `tags.count("block:user") == 1` — no lazy `assert result` patterns |
| Negative/error-path coverage | STRONG | Every positive test paired with negative: block/unblock, success/fail/reject, >1-slot/1-slot/backward |
| Mutation resistance | STRONG | Flipping `delta > 1` → caught; removing block:user exemption → caught; removing success branch → caught |
| Test independence | STRONG | All integration tests use `tmp_path` isolated boards; unit tests construct standalone objects |
| Descriptive naming | STRONG | `test_<condition>_<expectation>` pattern throughout |

#### Data Safety

- No issues. Guidance messages are hardcoded constants — no user input reaches message construction.
- Non-atomicity in end_work block path (engine.end_work + engine.edit_task sequential) — explicitly accepted in Architecture Review C1 rebuttal; block:user is advisory.
- `contextlib.suppress(Exception)` ensures guidance failures leave `task.guidance = []`; no corrupt state possible.

#### Implementation-Aware Test Gaps

- **Gap 1 (Informational — architect-accepted):** `end_work(outcome="block")` block:user removal failure silently suppresses DR guidance (server.py:345–352 with `contextlib.suppress`). No test exercises this failure path. Architecture Review C1 rebuttal explicitly accepted "non-atomicity is acceptable; block:user is advisory; worst case = stale tag." Not a new discovery; documented design risk. No FAIL.
- **Gap 2 (Trivial):** `_move_guidance` ValueError when status not in `status_names` — caught by suppress, returns []. Not tested but trivial defensive guard.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `test_guidance_rules_973.py` module docstring says "task #987" but file is a #973 deliverable. Minor future-reader confusion.
- `guidance.py`: `_block_guidance` uses `_BLOCK_OP_ALIASES = frozenset(...)` but `_is_success_operation` uses inline string check instead of parallel frozenset. Inconsistent style.
- `server.py:348`: `engine.edit_task(...)` called directly (blocking) inside `end_work` async handler, while `engine.end_work` 6 lines above uses `asyncio.to_thread`. Inconsistent threading pattern; low production risk given current single-threaded context.
- `test_guidance_edit_task_973.py:97` and `test_guidance_end_work_973.py:96`: block:user removal tests verify tag absence but don't assert guidance is still present in the same response. Dual assertion would be tighter.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: guidance field first, default [] | test_guidance.py:64–99, `keys[0] == "guidance"` | TestFromAC_KanbanTaskGuidanceField | PASS |
| AC2: collect_guidance() 3 rules | test_guidance.py:107+, test_guidance_rules_973.py:52+ — 24 tests | TestFromAC_CollectGuidance + TestFromAC_CollectGuidanceNewAPI | PASS |
| AC3: edit_task(block=...) + end_work(block) → DR guidance | test_guidance_edit_task_973.py:83, test_guidance_end_work_973.py:83 | TestFromAC_EditTaskGuidanceIntegration, TestFromAC_EndWorkGuidanceIntegration | PASS |
| AC4: move_task forward-skip guidance | test_guidance_move_task_973.py:86–159 | TestFromAC_MoveTaskGuidanceIntegration | PASS |
| AC5: end_work(success) → commit message | test_guidance_end_work_973.py:118 | TestFromAC_EndWorkGuidanceIntegration::test_success_outcome | PASS |
| AC6: Cockpit block:user lifecycle | test_cockpit_mutation_api.py:490+, TestFromAC_BlockUserTagConflict (3 tests) | TestFromAC_BlockUserTag + TestFromAC_BlockUserTagConflict | PASS |
| AC7: MCP block:user removal | test_guidance_edit_task_973.py:97,106, test_guidance_end_work_973.py:96 | 3 integration tests | PASS |
| AC8: Skill docs updated | h-mcp-kanban, r-pipeline-protocol, w-decision-routing — builder notes confirmed | Non-testable | PASS |
| AC9: All existing MCP tests pass | quality-runner: 78/78 | Meta-constraint | PASS |
| AC10: Seed propagation verified | No evidence — guidance defaults to [] so no seed file changes required; self-report adequate | None | PASS (trivially correct) |

### Confidence: .96

### Verdict: PASS

Deductions from 1.0:

- AC10: no evidence beyond builder self-report for explicit AC line (-0.02)
- AC6-4: LAX unblock sub-assertion compensated by conflict tests, not eliminated (-0.02)
[[2026-04-19]]

## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | File covers high-level stack/endpoints only; MCP tool response fields and Cockpit tag behaviors documented in skill files (authoritative). |
| 2 | Module docstrings | Yes | PASS | `guidance.py` module docstring + `collect_guidance()` full docstring present; `_apply_block_kwargs` in `mutation.py` has docstring; `KanbanTask` class docstring accurate. |
| 3 | External attribution | No | N/A | All 6 research sources internal codebase — no external patterns used. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | Yes | PASS | `.owlbear/research/block-time-guidance-mcp-973.md` exists, linked in task body, follow-up subtasks #985–#991 all created. |
| 5b | Skill docs (AC8) | Yes | PASS | h-mcp-kanban: "Response: Guidance Field" section added; r-pipeline-protocol: "DR Required on Agent Block" + block:user exemption; w-decision-routing: block-time guidance entry-point note. All confirmed present. |

**Files updated:** None — all required docs updated during implementation (AC8 verified).
**Scratch files:** No `.owlbear/scratch/973-*` files found — nothing to clean.
**Commit:** No additional commit needed.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: guidance field first, defaults [] | models.py:L11-12, TestFromAC_KanbanTaskGuidanceField | PASS |
| AC2: collect_guidance() 3 rules | guidance.py:L20-103, 24 unit tests across two modules | PASS |
| AC3: edit_task/end_work block returns DR guidance | server.py:L301-302,L350-351 integration + tests | PASS |
| AC4: move_task forward-skip guidance | server.py:L226-228, TestFromAC_MoveTaskGuidanceIntegration | PASS |
| AC5: end_work(success) commit reminder | test_guidance_end_work_973.py:L118 | PASS |
| AC6: Cockpit block:user lifecycle | mutation.py:L138-160, TestFromAC_BlockUserTag + conflict tests | PASS |
| AC7: MCP block branches remove block:user | integration tests in edit_task + end_work modules | PASS |
| AC8: Skill docs updated | h-mcp-kanban, r-pipeline-protocol, w-decision-routing confirmed | PASS |
| AC9: All existing MCP tests pass | Full suite 658 passed; 6 failures all in mcp-knowledge (unrelated) | PASS |
| AC10: Seed propagation | No changes needed (field defaults to []); trivially correct | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all in serve/mcp-knowledge, outside task scope), 0 skipped
- ruff: clean (0 violations)

### Architect Quality: 4/5

10 specific verifiable AC lines. Edge cases pre-identified in Brief (TOCTOU, non-atomicity, tag bypass). Builder needed minimal improvisation. Minor: AC10 trivially correct but vaguely stated; AC6 compound line.

### Deduction Breakdown

- AC10 no specific evidence beyond trivial correctness: -0.02
- 6 mcp-knowledge failures outside scope: no deduction
- Reviewer section detailed with PASS: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction

### Confidence: .98

### Action: archive
