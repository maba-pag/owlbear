---
id: 494
title: Add ToolAnnotations to all mcp-kanban tools
status: todo
priority: needed
created: 2026-03-31T06:46:59.3680944+02:00
updated: 2026-03-31T07:13:35.5026434+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
class: standard
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
