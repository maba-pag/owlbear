---
id: 494
title: Add ToolAnnotations to all mcp-kanban tools
status: archived
priority: medium
created: 2026-03-31 06:46:59.368094+02:00
updated: 2026-03-31 13:43:02.897126+02:00
started: 2026-03-31 13:43:02.427108+02:00
completed: 2026-03-31 13:43:02.427108+02:00
tags:
- scope:mcp
- type:build
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] list_tasks: annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
- [ ] show_task: annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
- [ ] create_task: annotations=ToolAnnotations(destructiveHint=False)
- [ ] move_task: annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True)
- [ ] edit_task: annotations=ToolAnnotations(destructiveHint=False)
- [ ] pick_task: annotations=ToolAnnotations(destructiveHint=False)
- [ ] board_context: annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
- [ ] Import ToolAnnotations from mcp.types
- [ ] Tests verify annotations are registered on each tool (all 7)
- [ ] ruff clean

## Context
Follow-up from #477 research. See docs/research/mcp-kanban-outputschema-annotations.md
Pattern: copy mcp-knowledge server which already uses ToolAnnotations (packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py).
Test pattern: copy _get_tool_annotations helper from packages/mcp-knowledge/tests/test_ingest_graph_tools.py L636-685.
Note: start_work/end_work tools do not exist yet (tasks #470, #471) -- add annotations when those tools are built.
Note: board_context may be removed by #477, but annotate it while it exists.

[[2026-03-31]] Tue 07:13
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- not research-driven (T1 config work; annotations mapping is mechanical)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| list_tasks readOnly+idempotent | Correct per MCP spec, read-only query | Keep |
| show_task readOnly+idempotent | Correct, read-only lookup | Keep |
| create_task destructive=False | Correct, additive write | Keep |
| move_task destructive=False+idempotent | Correct, status is idempotent | Keep |
| edit_task destructive=False | Correct, append_body is not idempotent | Keep |
| pick_task destructive=False | Correct, side effects vary | Keep |
| board_context readOnly+idempotent | ADDED: was missing from original AC | Added |
| Import ToolAnnotations | Correct, from mcp.types | Keep |
| Tests verify annotations | Precise, covers all 7 tools | Refined to explicit count |
| ruff clean | Standard | Keep |

### Architecture Notes
Single-responsibility: decorator metadata only, no behavioral change. Follows existing mcp-knowledge pattern exactly (ToolAnnotations import + decorator param). No new codepaths, no failure modes, no security surface. board_context was missing from original AC but exists in server.py -- added to ensure complete coverage.

### Changes Made
- Refined AC: added board_context annotations, explicit tool count (7), pattern references for impl and tests
- Moved to todo, released claim

### Dependencies
- None required (no depends_on). Independent of #477 (board_context removal) and #495 (outputSchema).

[[2026-03-31]] Tue 08:20
## Test-Writer Notes
- Test file: packages/mcp-kanban/tests/test_tool_annotations_494.py
- Classes: TestFromAC_ToolAnnotations
- Tests per category: happy 0, edge 0, error 0, boundary 0, annotation-contract 19
- Total: 19 tests, all FAIL
- ruff: clean
- AC coverage:
  - list_tasks readOnly+idempotent: test_list_tasks_read_only_hint_true, test_list_tasks_idempotent_hint_true
  - show_task readOnly+idempotent: test_show_task_read_only_hint_true, test_show_task_idempotent_hint_true
  - create_task destructive=False: test_create_task_destructive_hint_false
  - move_task destructive=False+idempotent: test_move_task_destructive_hint_false, test_move_task_idempotent_hint_true
  - edit_task destructive=False: test_edit_task_destructive_hint_false
  - pick_task destructive=False: test_pick_task_destructive_hint_false
  - board_context readOnly+idempotent: test_board_context_read_only_hint_true, test_board_context_idempotent_hint_true
  - ToolAnnotations import: test_tool_annotations_used_in_server_module
  - All 7 tools have annotations: test_all_tools_have_annotations[7 params]

[[2026-03-31]] Tue 11:52
## Builder Notes

- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py

- Added ToolAnnotations import + annotations on all 7 tools (list_tasks, show_task readOnly+idempotent; create_task, edit_task, pick_task destructive=False; move_task destructive=False+idempotent; board_context readOnly+idempotent)

- Tests: 19 passed, ruff clean, coverage 27% on server.py (metadata tests only, expected)

[[2026-03-31]] Tue 12:35
## Review Evidence

### Test Results
- pytest: 19 passed, 0 failed (test_tool_annotations_494.py)

### Lint Results
- ruff: All checks passed!

### Coverage
- server.py: 27% expected - decorator lines covered at import; function bodies pre-existing, out of scope for this task

### Test-Writer Audit
All 10 AC lines mapped to TestFromAC_ToolAnnotations. Assertions use is True / is False - would fail on value flip. No MISSING or LAX.

### Security Review
Pure metadata decorators. No new input paths, no subprocess changes, no hardcoded secrets. No OWASP concerns.

### TestFromAC Comparison
Builder only modified server.py. Test file unchanged from test-writer. All 19 TestFromAC_ToolAnnotations methods PRESERVED.

### Test Quality
- Assertion specificity: STRONG (is True / is False with descriptive messages)
- Negative/error coverage: N/A for declarative metadata
- Test independence: STRONG

### Data Safety
No data mutations. Purely declarative metadata.

### Implementation Gap Analysis
Implementation is one import + 7 decorator arguments. No branches, no error paths. All new behavior covered.

### AC Compliance
- list_tasks readOnly+idempotent: server.py @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)); tests PASS
- show_task readOnly+idempotent: server.py as spec; tests PASS
- create_task destructive=False: server.py as spec; test PASS
- move_task destructive=False+idempotent: server.py as spec; tests PASS
- edit_task destructive=False: server.py as spec; test PASS
- pick_task destructive=False: server.py as spec; test PASS
- board_context readOnly+idempotent: server.py as spec; tests PASS
- Import ToolAnnotations from mcp.types: server.py line 12 verified; test PASS
- All 7 tools have annotations: test_all_tools_have_annotations x7 PASS
- ruff clean: All checks passed!

### Verdict: PASS (confidence 0.97)

[[2026-03-31]] Tue 13:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| list_tasks readOnly+idempotent | server.py L104 decorator confirmed | PASS |
| show_task readOnly+idempotent | server.py L133 decorator confirmed | PASS |
| create_task destructive=False | server.py L143 decorator confirmed | PASS |
| move_task destructive=False+idempotent | server.py L182 decorator confirmed | PASS |
| edit_task destructive=False | server.py L192 decorator confirmed | PASS |
| pick_task destructive=False | server.py L239 decorator confirmed | PASS |
| board_context readOnly+idempotent | server.py L258 decorator confirmed | PASS |
| Import ToolAnnotations | server.py L13 from mcp.types | PASS |
| Tests verify annotations (all 7) | 19 tests in test_tool_annotations_494.py, all PASS | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (task-scoped): 19 passed, 0 failed
- pytest (full suite): 1998 passed, 294 failed (all failures pre-existing RED-phase tests from other tasks: #470, #472, #485, etc.)
- ruff: All checks passed

### Commit Verification
- e1d91ee feat: add ToolAnnotations to all mcp-kanban tools (#494, builder) -- server.py + test file

### AC Quality Score: 5/5
AC was specific (exact ToolAnnotations per tool), complete (all 7 tools covered), architect added missing board_context line. No improvisation needed.

### Deduction breakdown: none -- all 10 AC lines verified with evidence, reviewer section thorough, tests pass, ruff clean, AC quality 5
### Confidence: 1.0
### Action: archive

-t

[[2026-03-31]] Tue 13:42
## Audit
### AC Verification
All 10 AC lines verified with evidence in server.py (ToolAnnotations decorators on all 7 tools + import + 19 tests + ruff clean).

### Test Results
- pytest (task-scoped): 19 passed, 0 failed
- pytest (full suite): 1998 passed, 294 failed (all pre-existing RED-phase tests)
- ruff: All checks passed

### Commit Verification
- e1d91ee feat: add ToolAnnotations (#494, builder) -- server.py + test file

### AC Quality Score: 5/5
AC was specific, complete, architect added missing board_context. No improvisation needed.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive
