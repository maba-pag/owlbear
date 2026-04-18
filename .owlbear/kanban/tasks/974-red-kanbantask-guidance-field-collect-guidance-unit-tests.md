---
id: 974
title: 'RED: KanbanTask.guidance field + collect_guidance unit tests'
status: in-progress
priority: needed
created: 2026-04-18T21:17:49.860532+00:00
updated: 2026-04-18T21:58:27.081176+00:00
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
### Action Taken: Refined AC to align operation strings with GREEN #976 interface (`"edit_block"`, `"end_work_block"`, `"move"`, `"end_work_success"`), specified `statuses` kwarg for move rule, and added assertion substring requirements. Test-writer must follow refined AC in this section, not original.
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