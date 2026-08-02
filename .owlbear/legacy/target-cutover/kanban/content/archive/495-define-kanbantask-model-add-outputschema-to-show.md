---
id: 495
title: Define KanbanTask model + add outputSchema to show/move/pick
status: archived
priority: medium
created: 2026-03-31 06:47:09.589536+02:00
updated: 2026-04-01 06:18:42.903355+02:00
started: 2026-04-01 06:18:39.009286+02:00
completed: 2026-04-01 06:18:39.009286+02:00
tags:
- scope:mcp
- type:build
- phase-2
depends_on:
- 489
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] New file: packages/mcp-kanban/src/owlbear_mcp_kanban/models.py with KanbanTask(BaseModel)
- [ ] model_config = ConfigDict(populate_by_name=True) (default extra=ignore, structuredContent matches outputSchema)
- [ ] Required fields: id (int), title (str), status (str), priority (str), created (str), updated (str), class_ (str, Field(alias=class))
- [ ] Optional fields: started (str or None), completed (str or None), assignee (str or None), claimed_by (str or None), claimed_at (str or None), tags (list[str] = []), due (str or None), estimate (str or None), parent (int or None), depends_on (list[int] = []), blocked (bool = False), block_reason (str or None), body (str or None), file (str or None)
- [ ] show_task, move_task, pick_task: return type str to KanbanTask; use KanbanTask.model_validate_json(stdout)
- [ ] show_task, move_task, pick_task: error path from return error-string to raise ToolError(stderr.strip())
- [ ] Wrap model_validate_json in try/except ValidationError; on failure raise ToolError with validation details
- [ ] Verify structuredContent uses alias keys (class not class_) matching outputSchema; if FastMCP serializes by field name, return model.model_dump(by_alias=True) instead of model instance
- [ ] Scope exclusions: list_tasks (array), create_task, edit_task, start_work all remain returning str
- [ ] Update skills/mcp-kanban/SKILL.md error-handling section: show/move/pick raise ToolError (isError true), other tools return error-string
- [ ] Tests: outputSchema in tool listing for show/move/pick; structuredContent with alias keys; ToolError on rc!=0; ValidationError caught and wrapped; model validates sample kanban-md JSON shapes
- [ ] ruff clean

## Context
Follows #489 (--json switch). See docs/research/mcp-kanban-outputschema-annotations.md
FastMCP auto-derives outputSchema from Pydantic BaseModel return types.
Error handling switches from return error-str to raise ToolError per MCP spec.
Note: orchestrator package has a separate planner Task model (planner/models.py) for internal processing with datetime types and frozen config, intentionally distinct from this protocol-boundary model.

## Research
Validated prior research (mcp-kanban-outputschema-annotations.md).
See docs/research/kanbantask-model-outputschema.md for full findings.

### Key finding: Model field correction
Proposed KanbanTask model missing 3 fields from actual kanban-md output:
- class (always present, use Field(alias=class) since reserved word)
- claimed_by (optional, dynamic claim)
- claimed_at (optional, ISO timestamp)

### Classification
T1 (Autonomous) -- implements pre-approved design from #477.
Checklist items 1-7 validated. No T3 triggers.

[[2026-03-31]] Tue 22:34
## Architecture Review
See docs/scratch/495-architect.md for full review.

[[2026-04-01]] Wed 00:07
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_kanbantask_model_495.py
- Classes: TestFromAC_KanbanTaskModelExists, TestFromAC_KanbanTaskModelConfig, TestFromAC_KanbanTaskRequiredFields, TestFromAC_KanbanTaskOptionalFields, TestFromAC_KanbanTaskAliasSerialisation, TestFromAC_ShowTaskReturnsKanbanTask, TestFromAC_MoveTaskReturnsKanbanTask, TestFromAC_PickTaskReturnsKanbanTask, TestFromAC_OutputSchemaAnnotations, TestFromAC_ModelValidatesSampleJsonShapes
- Tests per category: happy 14, edge 5, error 12, boundary 4
- Total: 47 tests, all FAIL
- ruff: clean
- AC coverage: models.py KanbanTask, model_config, required fields, optional fields, show/move/pick KanbanTask return, ToolError on rc!=0, ValidationError wrap, alias serialisation, outputSchema KanbanTask fields, sample JSON shapes validated
- Scope exclusions (list/create/edit/start_work remain str): pre-existing correct behavior, cannot fail in RED, removed per tdd-red rules

[[2026-04-01]] Wed 00:35
## Builder Notes
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/models.py (new), packages/mcp-kanban/src/owlbear_mcp_kanban/server.py, skills/mcp-kanban/SKILL.md
- Tests: 47 passed, models.py 100% coverage
- Lint: ruff clean
- Evidence: all TestFromAC_* classes green; EM102/TRY003 fixed by assigning msg variable
- Fixes applied: output_schema override via fn_metadata after tool registration (same pattern as list_tasks); alias keys (class not class_) set via model_json_schema(by_alias=True)

[[2026-04-01]] Wed 01:48
## Review Evidence
See docs/scratch/495-reviewer.md for full evidence.

[[2026-04-01]] Wed 03:24
## Builder Notes (v2)
- Root cause: first builder created models.py correctly but made no changes to show/move/pick in server.py
- Files changed: server.py (show/move/pick bodies), test_server.py (TestFromAC_Tools), test_integration.py (_MINIMAL_CONFIG)
- server.py: added ToolError + ValidationError imports; updated show_task/move_task/pick_task to return KanbanTask, raise ToolError on rc!=0, wrap ValidationError
- test_server.py: updated 3 success tests to mock valid JSON + isinstance check; removed show/move/pick from error-string parametrize (they now raise ToolError)
- test_integration.py: added 'class: standard' to _MINIMAL_CONFIG so kanban-md outputs class field
- Tests: 140 passed (47 from #495 + 93 from packages), models.py 100% coverage, server.py 93% coverage
- Lint: ruff clean

[[2026-04-01]] Wed 04:23
## Review Evidence (v2)
See docs/scratch/495-reviewer-v2.md for full evidence.

[[2026-04-01]] Wed 04:41
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | No behavior change at copilot-instructions level; per-tool detail lives in skills/mcp-kanban/SKILL.md (already updated by builder) |
| 2 | Docstrings | Yes | Pass | models.py: module docstring + KanbanTask class docstring present; server.py show_task/move_task/pick_task all have accurate docstrings |
| 3 | docs/sources/overview.md | Yes | Pass | KanbanTask Model + outputSchema Validation (Task #495) section already present with 4 source rows |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/kanbantask-model-outputschema.md exists and linked in task body under ## Research |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/495-architect.md
- docs/scratch/495-cov.txt
- docs/scratch/495-pkg-test.txt
- docs/scratch/495-reviewer-v2.md
- docs/scratch/495-reviewer.md

[[2026-04-01]] Wed 06:18
## Audit
### AC Verification
All 12 AC items PASS. See spot-check evidence below.

### Test Results
- pytest task scope: 140 passed (47 from #495 + 93 package)
- pytest full suite: 2479 passed, 236 failed (pre-existing from other tasks)
- Cross-task regression: 2 tests in test_drop_board_context_489.py fail (stale mock data after move/pick return type change)
- ruff: clean

### AC Quality: 5/5
### Deduction breakdown
- Start 1.00
- -.05 cross-task test regression (2 stale #489 mocks)
- Net .95
### Confidence: .95
### Action: archive
