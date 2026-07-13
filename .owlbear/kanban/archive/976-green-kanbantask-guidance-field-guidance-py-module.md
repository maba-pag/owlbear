---
id: 976
title: 'GREEN: KanbanTask.guidance field + guidance.py module'
status: archived
priority: medium
created: 2026-04-18T21:18:03.809586+00:00
updated: 2026-04-19T02:24:20.827316+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 974
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase per w-tdd-green. Makes #974 tests pass.

## Acceptance Criteria

Files:

- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- new `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`

Per Brief decisions D4 + D5:

- Add `guidance: list[str] = []` as the FIRST declared field on `KanbanTask` (Pydantic v2 declaration-order JSON serialization places it first).
- Create `guidance.py` with flat rule list. Each rule is a `(predicate, message_template)` tuple.
- One function: `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **kwargs) -> list[str]`.
- V1 ships three rules:
  1. `operation in ("edit_block", "end_work_block")` and `block:user` tag NOT in `after.tags` → DR-required message
  2. `operation == "move"` and `after.status` is > 1 slot ahead of `before.status` (in the engine's status order) → forward-skip message
  3. `operation == "end_work_success"` → commit-pushed message
- No classes, no decorators.

All tests in #974 pass; all existing kanban MCP tests still pass.
[[2026-04-19]]

## Architecture Review

### Context

Implementation already exists in codebase — both `guidance.py` and the `guidance` field on `KanbanTask` are committed and wired into `server.py`. Parent #973 and dependency #974 are both archived. Task #987 has already extended the guidance module beyond V1 scope. This is an orphaned subtask that was never pipeline-advanced after implementation.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One model field + one module with flat rules |
| Interface clarity | PASS | `collect_guidance(operation, before, after, **kwargs) -> list[str]` — clear inputs/outputs |
| Dependency correctness | PASS | #974 (RED tests) archived/done |
| Module layering | PASS | guidance.py imports from models.py (same pkg); server.py imports guidance.py. No upward imports |
| TDD compliance | PASS | #974 is the preceding RED task, archived |
| KISS/YAGNI | PASS | Flat functions, no classes, no decorators per AC |
| Premise challenge | PASS | Guidance messages for kanban ops is a valid feature; no existing equivalent |
| Pattern consistency | PASS | Follows mcp-kanban conventions (Pydantic models, ToolError, contextlib.suppress for non-critical enrichment) |
| Security surface | PASS | No new system boundaries — messages generated internally |
| Single domain | PASS | Entirely within mcp-kanban |

### AC Deviation Note

AC specifies `(predicate, message_template)` tuples; implementation uses helper functions (`_is_block_operation`, `_block_guidance`, `_move_guidance`, `_is_success_operation`). Functionally equivalent — flat rules, no classes, no decorators. Acceptable builder refinement for a GREEN task where #974 tests are the true contract.

### Challenge Results

- Challenger: reconsider (confidence 0.35)
- Key concerns: (1) tuple-vs-helper AC deviation, (2) codebase mutated by #987, (3) orphaned subtask with code already shipped
- Architect response: Accepted concern about tuple deviation (noted above). Implementation is functionally correct and matches the spirit of AC. Pipeline flow needed for proper closure — test-writer/reviewer/auditor can stamp existing work. The code is sound regardless of pipeline ordering.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Implementation exists; pipeline flow provides proper closure and traceability

[[2026-04-19]]

## Test-Writer Notes

**Pass-through: GREEN task with prior RED coverage**

- Test file: `serve/mcp-kanban/tests/test_guidance.py` (written by #974 RED phase)
- Implementation already exists: `guidance.py` + `KanbanTask.guidance` field fully committed
- All AC criteria covered — no new failing tests to write:

| AC | Test(s) |
|----|---------|
| `guidance: list[str] = []` default | `test_guidance_defaults_to_empty_list` |
| `guidance` first key in model_dump() | `test_guidance_is_first_key_in_model_dump` |
| `model_validate` without guidance key → `[]` | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` |
| `edit_block` without `block:user` → DR message | `test_edit_block_without_block_user_tag_returns_dr_message` |
| `end_work_block` without `block:user` → DR message | `test_end_work_block_without_block_user_tag_returns_dr_message` |
| `edit_block` with `block:user` → `[]` | `test_edit_block_with_block_user_tag_returns_empty` |
| `end_work_block` with `block:user` → `[]` | `test_end_work_block_with_block_user_tag_returns_empty` |
| `move` >1 slot forward → guidance | `test_move_forward_skip_more_than_one_slot_returns_guidance` |
| `move` exactly 1 slot → `[]` | `test_move_forward_one_slot_returns_empty` |
| `move` backward → `[]` | `test_move_backward_returns_empty` |
| `end_work_success` → commit message | `test_end_work_success_returns_commit_message` |
| unknown op → `[]` | `test_unknown_operation_returns_empty_list` |

- Total: 12 tests in `TestFromAC_KanbanTaskGuidanceField` + `TestFromAC_CollectGuidance`, all currently PASS
- Writing new failing tests is not possible — implementation is complete
- Arch review explicitly noted: "Pipeline flow for proper closure and traceability"
[[2026-04-19]]

## Builder Notes

**Pipeline closure** — implementation was already committed as part of the original dev work. This task advances for traceability.

**Files verified (no changes needed):**

- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` — `collect_guidance()` with flat rule helpers, 3 V1 rules (block DR, move skip, end_work_success commit)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` — `guidance: list[str] = []` declared as first field on `KanbanTask`

**Test results:** 12/12 `TestFromAC_*` tests PASS (3 model field tests + 9 collect_guidance tests)
**Full suite:** 66/66 mcp-kanban tests PASS
**Lint:** `ruff check serve/mcp-kanban/` — All checks passed
**Coverage:** Verified via test run (no coverage threshold set for this task)

**AC compliance:**

- ✅ `guidance: list[str] = []` is the FIRST key in `model_dump()` (confirmed by test)
- ✅ `collect_guidance(operation, before, after, **kwargs) -> list[str]`
- ✅ Rule 1: block op without `block:user` tag → DR-required message
- ✅ Rule 2: `move` >1 slot forward → forward-skip message
- ✅ Rule 3: `end_work_success` → commit-pushed message
- ✅ No classes, no decorators (flat helper functions — functionally equivalent to tuple predicates per arch review)
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 66 passed, 0 failed (full mcp-kanban suite, Quality-Runner independent run)

### Lint

clean: true — no ruff violations in guidance.py, models.py, or test_guidance.py

### Coverage

- owlbear_mcp_kanban.guidance: 98%
- owlbear_mcp_kanban.models: 100%
- Extended-API paths (beyond V1) covered by test_guidance_rules_973.py and test_guidance_rules_987.py

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `guidance: list[str] = []` default | `test_guidance_defaults_to_empty_list` | Yes — asserts `task.guidance == []` | COVERED |
| `guidance` first key in model_dump() | `test_guidance_is_first_key_in_model_dump` | Yes — asserts `keys[0] == "guidance"` | COVERED |
| model_validate without guidance key → [] | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` | Yes — asserts `task.guidance == []` | COVERED |
| `edit_block` without `block:user` → DR message | `test_edit_block_without_block_user_tag_returns_dr_message` | Yes — checks len > 0 and "Decision Request" in result[0] | COVERED |
| `end_work_block` without `block:user` → DR message | `test_end_work_block_without_block_user_tag_returns_dr_message` | Yes — same pattern | COVERED |
| `edit_block` with `block:user` → [] | `test_edit_block_with_block_user_tag_returns_empty` | Yes — asserts `result == []` | COVERED |
| `end_work_block` with `block:user` → [] | `test_end_work_block_with_block_user_tag_returns_empty` | Yes — asserts `result == []` | COVERED |
| `move` >1 slot forward → guidance | `test_move_forward_skip_more_than_one_slot_returns_guidance` | Yes — asserts len > 0 | COVERED |
| `move` exactly 1 slot → [] | `test_move_forward_one_slot_returns_empty` | Yes — asserts `result == []` | COVERED |
| `move` backward → [] | `test_move_backward_returns_empty` | Yes — asserts `result == []` | COVERED |
| `end_work_success` → commit message | `test_end_work_success_returns_commit_message` | Yes — checks "commit" in result[0].lower() | COVERED |
| unknown op → [] | `test_unknown_operation_returns_empty_list` | Yes — asserts `result == []` | COVERED |

All 12 AC lines: COVERED. No MISSING or LAX.

#### Security Review

No issues. Pure string manipulation and list-building logic. No external I/O, no user-controlled paths, no deserialization risks, no secrets.

#### Test Integrity

No TestFromAC modifications by builder — builder explicitly stated "no changes needed" and files verified. The RED test file (test_guidance.py) retains all 12 original test methods intact.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 12 TestFromAC_* methods | None (builder made no edits) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Substring checks ("Decision Request", "commit") meaningful; exact == [] checks for negative cases |
| Negative/error-path coverage | STRONG | All negative paths tested: block:user tag, 1-slot move, backward move, unknown op |
| Mutation resilience | ADEQUATE | Flipping DR rule logic would cause failures; message content checks would catch message removal |
| Test independence | STRONG | No shared mutable state; each test creates fresh KanbanTask instances |
| Descriptive test names | STRONG | All test names precisely describe the scenario |

Overall: ADEQUATE — no WEAK dimensions.

#### Data Safety

No issues. No shared mutable state. No unbounded inputs. Deterministic list-building only.

#### Implementation-Aware Gaps

- Beyond-V1 code paths (`after.blocked`, `end_work` with `outcome` kwarg, `status_names` kwarg, `before=None`) are NOT in test_guidance.py but ARE covered in test_guidance_rules_973.py and test_guidance_rules_987.py. These extensions were added by #987 with dedicated tests — not a gap.
- guidance.py 98% coverage confirms only trivially unreachable branches remain.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (no retries) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- AC specifies `(predicate, message_template)` tuples; implementation uses helper functions. Architect explicitly approved this as an acceptable refinement — functionally equivalent. No action needed.
- test_guidance.py uses `# type: ignore` comments due to try/except import pattern from RED phase. Minor style note, not a defect.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `guidance: list[str] = []` FIRST field | models.py:14 `guidance: list[str] = Field(default_factory=list)` — first field after model_config | test_guidance_is_first_key_in_model_dump | PASS |
| `collect_guidance(operation, before, after, **kwargs) -> list[str]` | guidance.py:21-46 | All TestFromAC_CollectGuidance | PASS |
| Rule 1: block op without `block:user` → DR message | guidance.py:57-64 `_is_block_operation` + `_block_guidance` | test_edit_block_without_block_user_tag_returns_dr_message | PASS |
| Rule 2: `move` >1 slot → forward-skip message | guidance.py:85-108 `_move_guidance` delta > 1 branch | test_move_forward_skip_more_than_one_slot_returns_guidance | PASS |
| Rule 3: `end_work_success` → commit message | guidance.py:67-69 `_is_success_operation` | test_end_work_success_returns_commit_message | PASS |
| No classes, no decorators | guidance.py: flat functions only — `_is_block_operation`, `_is_success_operation`, `_block_guidance`, `_move_guidance`, `collect_guidance` | — | PASS |
| All tests in #974 pass | Quality-Runner: 66 passed, 0 failed | Full suite | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | New `KanbanTask.guidance` field + `guidance.py` module. `copilot-instructions.md` has no mcp-kanban section; guidance is an internal MCP response detail, not a workspace convention. No update needed. |
| 2 | Module docstrings | Yes | Verified | `guidance.py`: module docstring ✅, `collect_guidance()` full Args/Returns docstring ✅, private helpers correctly undocumented. `models.py`: module docstring ✅, `KanbanTask` class docstring ✅, `_coerce_claimed` docstring ✅. All accurate. |
| 3 | External attribution | No | N/A | Pure internal design from Brief decisions D4+D5. No external repos or articles cited. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/976-*` file. Architecture review was inline in task body. |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`976-*` pattern returned no results)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `guidance: list[str] = []` FIRST field | models.py:15 — first field after model_config | PASS |
| `collect_guidance(operation, before, after, **kwargs) -> list[str]` | guidance.py:21-46 — correct signature | PASS |
| Rule 1: block op without `block:user` → DR message | guidance.py:57-64+82-85; test_edit_block_without_block_user_tag_returns_dr_message | PASS |
| Rule 2: move >1 slot → forward-skip message | guidance.py:87-108; test_move_forward_skip_more_than_one_slot_returns_guidance | PASS |
| Rule 3: end_work_success → commit message | guidance.py:67-69; test_end_work_success_returns_commit_message | PASS |
| No classes, no decorators | guidance.py: flat functions only | PASS |
| All #974 tests pass | 66/66 mcp-kanban tests pass (Quality-Runner full run) | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all 6 in mcp-knowledge — unrelated to task scope; 0 failures in mcp-kanban)
- ruff: clean, no violations

### Architect Quality: 4/5

AC was specific and verifiable. Minor gap: AC specified `(predicate, message_template)` tuples but implementation used helper functions — architect explicitly approved this as acceptable refinement. Functionally equivalent, no ambiguity in intent.

### Deduction Breakdown

- AC lines without evidence: 0 (all 7 verified) → no deduction
- Lint violations: none → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed, PASS at .97) → no deduction
- Full-suite failures in task scope: none → no deduction

### Confidence: .98

### Action: archive

Note: Pipeline-closure task — implementation was already committed. All pipeline stages documented this explicitly. Builder verified existing code rather than writing new code. All evidence checks out.
