---
id: 974
title: 'RED: KanbanTask.guidance field + collect_guidance unit tests'
status: archived
priority: medium
created: 2026-04-18T21:17:49.860532+00:00
updated: 2026-04-19T01:18:32.064542+00:00
tags:
- scope:mcp
- scope:kanban
- type:test
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. RED phase per w-tdd-red.

## Acceptance Criteria

File: `serve/mcp-kanban/tests/test_guidance.py`

- `KanbanTask.guidance` defaults to `[]`
- `guidance` is the first field in JSON serialization order (Pydantic v2 declaration-order)
- `collect_guidance("block", before, after)` returns DR-required message
- `collect_guidance("block", ...)` on task with `block:user` tag skips DR message
- `collect_guidance("edit", ...)` non-block returns empty list
- `collect_guidance("move", before, after)` forward-skip > 1 slot returns guidance
- `collect_guidance("move", ...)` 1-slot adjacent and backward returns empty list
- `collect_guidance("success", ...)` returns commit-pushed message

All tests must FAIL (the field and module do not exist yet).
[[2026-04-18]]

## Architecture Review

### Refined Acceptance Criteria (supersedes original AC)

File: `serve/mcp-kanban/tests/test_guidance.py`
Imports: `from owlbear_mcp_kanban.models import KanbanTask`, `from owlbear_mcp_kanban.guidance import collect_guidance`

#### Model tests

- `KanbanTask.guidance` defaults to `[]`
- `guidance` is the first key in `KanbanTask.model_dump()` output (Pydantic v2 declaration-order)

#### `collect_guidance` — block rules (operations `"edit_block"` / `"end_work_block"`)

- `collect_guidance("edit_block", before, after)` where `"block:user"` NOT in `after.tags` → returns non-empty list; first item contains substring `"Decision Request"`
- `collect_guidance("end_work_block", before, after)` where `"block:user"` NOT in `after.tags` → returns non-empty list; first item contains substring `"Decision Request"`
- `collect_guidance("edit_block", before, after)` where `"block:user"` in `after.tags` → returns `[]`
- `collect_guidance("end_work_block", before, after)` where `"block:user"` in `after.tags` → returns `[]`

#### `collect_guidance` — move rule (operation `"move"`)

Status ordering passed via kwarg: `statuses=["research", "backlog", "todo", "in-progress", "review", "docs", "done"]`

- `collect_guidance("move", before, after, statuses=STATUSES)` where `after.status` is >1 slot ahead of `before.status` → returns non-empty list
- `collect_guidance("move", before, after, statuses=STATUSES)` where `after.status` is 1-slot ahead → returns `[]`
- `collect_guidance("move", before, after, statuses=STATUSES)` where `after.status` is backward → returns `[]`

#### `collect_guidance` — success rule (operation `"end_work_success"`)

- `collect_guidance("end_work_success", before, after)` → returns non-empty list; first item contains substring `"commit"` (case-insensitive)

#### Negative / unmatched operation

- `collect_guidance("unknown_op", before, after)` → returns `[]`

All tests must FAIL (the field and module do not exist yet).

### Refinement Summary

Original AC used operation strings `"block"`, `"edit"`, `"move"`, `"success"` that conflict with GREEN #976's interface: `"edit_block"`, `"end_work_block"`, `"move"`, `"end_work_success"`. Refined AC aligns with #976 and Brief decisions D2/D5. Also: (1) explicit `statuses` kwarg for move rule per D6; (2) assertion substrings specified for DR-required and commit-pushed messages; (3) both `edit_block` and `end_work_block` tested separately since they are distinct call sites per D2.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file, one concern (RED tests for guidance interface) |
| Interface clarity | PASS (after refinement) | Operation strings, kwargs, and assertion content now explicit |
| Dependency correctness | PASS | No deps needed — RED tests are designed to fail against absent code |
| Module layering | PASS | Tests import from same package (`owlbear_mcp_kanban.models`, `.guidance`) |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal test scope covering V1 rules only |
| Premise challenge | PASS | Parent Brief well-researched; guidance mechanism is validated approach |
| Pattern consistency | PASS | Follows existing mcp-kanban test conventions (pytest, class-based) |
| Security surface | PASS | No new system boundaries; tests only |
| Single domain | PASS | scope:mcp + scope:kanban = single kanban-MCP domain |

### Challenge Results

- Challenger: **block** (confidence 0.35 in original AC)
- Key findings: (C1) operation string mismatch RED↔GREEN — critical; (C3) status ordering injection unspecified — moderate; (C4) assertion content vague — minor
- Architect response: **accepted** — all three concerns addressed in refined AC. Operation strings aligned with #976. Status ordering via `statuses` kwarg made explicit. Assertion substrings specified.

### Verdict: APPROVE (after REFINE)

### Action Taken: Refined AC to align operation strings with GREEN #976 interface (`"edit_block"`, `"end_work_block"`, `"move"`, `"end_work_success"`), specified `statuses` kwarg for move rule, and added assertion substring requirements. Test-writer must follow refined AC in this section, not original

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance.py`
- Classes: `TestFromAC_KanbanTaskGuidanceField`, `TestFromAC_CollectGuidance`
- Tests per category: happy 4, edge 1, error 2, boundary 2, model 2
- Total: 11 tests, all FAIL confirmed
- ruff: clean

### AC Coverage

| AC Line | Test |
|---------|------|
| `KanbanTask.guidance` defaults to `[]` | `test_guidance_defaults_to_empty_list` |
| `guidance` first key in `model_dump()` | `test_guidance_is_first_key_in_model_dump` |
| `edit_block` without `block:user` → DR message | `test_edit_block_without_block_user_tag_returns_dr_message` |
| `end_work_block` without `block:user` → DR message | `test_end_work_block_without_block_user_tag_returns_dr_message` |
| `edit_block` with `block:user` → `[]` | `test_edit_block_with_block_user_tag_returns_empty` |
| `end_work_block` with `block:user` → `[]` | `test_end_work_block_with_block_user_tag_returns_empty` |
| `move` forward >1 slot → guidance | `test_move_forward_skip_more_than_one_slot_returns_guidance` |
| `move` 1-slot adjacent → `[]` | `test_move_forward_one_slot_returns_empty` |
| `move` backward → `[]` | `test_move_backward_returns_empty` |
| `end_work_success` → commit message | `test_end_work_success_returns_commit_message` |
| unknown operation → `[]` | `test_unknown_operation_returns_empty_list` |

### Failure modes (RED)

- Model tests: `AttributeError` — `KanbanTask` has no `guidance` field
- `collect_guidance` tests: `AssertionError` — `owlbear_mcp_kanban.guidance` module does not exist (ImportError wrapped via `_require_guidance()`)

Commit: `dde538ad`
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` — added `guidance: list[str] = Field(default_factory=list)` as the first field (before `id`) to satisfy Pydantic v2 declaration-order serialization requirement
- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` — new module with `collect_guidance(operation, before, after, **kwargs)` and two private helpers `_block_guidance` / `_move_guidance` (split to satisfy PLR0911 ≤6 returns per function)

### Test results

- 11 TestFromAC tests: all PASS (confirmed RED before implementation)
- 30 mcp-kanban total: all PASS (no regressions)

### Lint status

ruff: CLEAN (fixed TC001 by moving KanbanTask import into TYPE_CHECKING block; fixed PLR0911 by extracting helper functions)

### Evidence

- RED verified: 11 FAILED before implementation (AttributeError on guidance field, ImportError on guidance module)
- GREEN confirmed: 11 PASSED after implementation
- Commit: `4438375c`
[[2026-04-19]]

## Review Evidence

### Test Results

pytest: 60 passed, 0 failed, 0 skipped (full mcp-kanban suite)

### Lint

ruff: CLEAN — 0 violations

### Coverage

- `owlbear_mcp_kanban.guidance`: 98%
- `owlbear_mcp_kanban.models`: 100%

### AC Compliance (Refined AC from Architecture Review)

| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|------------|------------------------|---------|
| `KanbanTask.guidance` defaults to `[]` | `test_guidance_defaults_to_empty_list` | Yes | COVERED |
| `guidance` first key in `model_dump()` | `test_guidance_is_first_key_in_model_dump` | Yes | COVERED |
| `edit_block` w/o `block:user` → "Decision Request" | `test_edit_block_without_block_user_tag_returns_dr_message` | Yes | COVERED |
| `end_work_block` w/o `block:user` → "Decision Request" | `test_end_work_block_without_block_user_tag_returns_dr_message` | Yes | COVERED |
| `edit_block` + `block:user` → `[]` | `test_edit_block_with_block_user_tag_returns_empty` | Yes | COVERED |
| `end_work_block` + `block:user` → `[]` | `test_end_work_block_with_block_user_tag_returns_empty` | Yes | COVERED |
| `move` forward >1 slot → guidance | `test_move_forward_skip_more_than_one_slot_returns_guidance` | Yes | COVERED |
| `move` 1-slot adjacent → `[]` | `test_move_forward_one_slot_returns_empty` | Yes | COVERED |
| `move` backward → `[]` | `test_move_backward_returns_empty` | Yes | COVERED |
| `end_work_success` → first item contains "commit" | `test_end_work_success_returns_commit_message` | Yes | COVERED |
| `unknown_op` → `[]` | `test_unknown_operation_returns_empty_list` | Yes | COVERED |

### TestFromAC Integrity

All 11 `TestFromAC_*` tests preserved unmodified. `TestBuilderDiscovered` class adds one strengthening test (AC6: `model_validate` from dict without `guidance` key) — STRENGTHENED, not weakened.

### Security Review

No hardcoded secrets, injection, path traversal, or unsafe deserialization. `extra="ignore"` on `ConfigDict` correctly rejects unknown fields.

### Test Quality

STRONG on all five dimensions: assertion specificity (exact equality + required substrings), negative/error-path coverage (5 empty-list tests), mutation resistance (flip `> 1` → `>= 1` caught by `test_move_forward_one_slot_returns_empty`), test independence (fresh `_task()` per test), descriptive names throughout.

### Data Safety

Pure business logic — string comparisons, list operations. No persistence, no mutable shared state.

### Implementation Notes

Builder correctly placed `guidance` as the first field in `KanbanTask` for Pydantic v2 declaration-order serialization. `_BLOCK_OP_ALIASES` frozenset and private helpers `_block_guidance`/`_move_guidance` are minimal and appropriate. TC001 and PLR0911 lint fixes are correct.

### Deductions: 0

### Confidence: .97 → PASS

[[2026-04-19]]

## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | File has no mcp-kanban section; `guidance` field and `collect_guidance` module are internal impl details, not documented at system-instruction level |
| 2 | Module docstrings | Yes | PASS | `guidance.py` module docstring ✅; `collect_guidance()` full docstring with Args/Returns ✅; `KanbanTask` class docstring ✅; private helpers are underscore-prefixed — no docstrings required |
| 3 | External attribution | No | N/A | No external repos or patterns referenced |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No .owlbear/research/ doc produced |

**Files updated:** None required.
**Scratch files:** None found (`.owlbear/scratch/974-*`).
**Commit:** None — no documentation changes needed.
[[2026-04-19]]

## Audit

### AC Verification (spot-check, reviewer trusted for full mapping)

| AC Line | Evidence | Status |
|---------|----------|--------|
| `KanbanTask.guidance` defaults to `[]` | models.py:L15 `guidance: list[str] = Field(default_factory=list)` + test_guidance_defaults_to_empty_list | PASS |
| `guidance` first key in `model_dump()` | models.py: guidance declared before `id` (Pydantic v2 declaration-order) + test_guidance_is_first_key_in_model_dump | PASS |
| `edit_block` w/o `block:user` -> DR message | guidance.py:_block_guidance + test_edit_block_without_block_user_tag_returns_dr_message | PASS |
| `end_work_block` w/o `block:user` -> DR message | guidance.py:_block_guidance + test_end_work_block_without_block_user_tag_returns_dr_message | PASS |
| `edit_block` + `block:user` -> `[]` | guidance.py:L80 `if "block:user" in after.tags: return []` + test_edit_block_with_block_user_tag_returns_empty | PASS |
| `end_work_block` + `block:user` -> `[]` | Same logic + test_end_work_block_with_block_user_tag_returns_empty | PASS |
| `move` forward >1 slot -> guidance | guidance.py:_move_guidance `delta > 1` + test_move_forward_skip_more_than_one_slot_returns_guidance | PASS |
| `move` 1-slot adjacent -> `[]` | guidance.py: `delta > 1` returns [] for delta=1 + test_move_forward_one_slot_returns_empty | PASS |
| `move` backward -> `[]` | guidance.py: negative delta, `delta > 1` false + test_move_backward_returns_empty | PASS |
| `end_work_success` -> commit message | guidance.py:_is_success_operation +_COMMIT_REMINDER_MSG + test_end_work_success_returns_commit_message | PASS |
| unknown operation -> `[]` | No branch matches, returns [] + test_unknown_operation_returns_empty_list | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all mcp-knowledge, pre-existing, unrelated), 0 skipped
- ruff: CLEAN (0 violations)

### Scope Check

Changed files: models.py, guidance.py (new), test_guidance.py (new) — all within serve/mcp-kanban, aligned with AC scope.

### Reviewer Evidence

Detailed section present. 60 mcp-kanban tests passed, 0 failed. 98% coverage on guidance, 100% on models. All 11 AC lines mapped COVERED. Confidence .97 PASS. Trusted for code-level findings.

### Upstream Commits

- Test-writer: dde538ad (RED tests)
- Builder: 4438375c (GREEN implementation)

### Architect Quality: 5/5

AC lines extremely specific (operation strings, expected substrings, explicit kwargs). Challenger engagement effective — caught operation string mismatch with GREEN #976, resolved via refinement. Edge cases covered (backward move, unknown op, block:user tag). Status ordering via statuses kwarg made explicit per D6.

### Deduction Breakdown

- AC lines with no evidence: 0
- Lint violations: 0
- AC quality score 5 (no deduction)
- Missing reviewer evidence: 0
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
