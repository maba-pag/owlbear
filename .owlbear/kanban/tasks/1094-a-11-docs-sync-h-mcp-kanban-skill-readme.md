---
id: 1094
title: 'A-11: docs sync — h-mcp-kanban skill + README'
status: todo
priority: needed
created: 2026-04-21T10:55:00.686129+00:00
updated: 2026-04-21T10:55:00.686129+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- docs
parent: 1045
depends_on:
- 1093
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md "Handoff Notes"
Files: `share/skills/h-mcp-kanban/SKILL.md`, `serve/mcp-kanban/README.md`

Update the h-mcp-kanban skill reference and the mcp-kanban README to reflect the redesigned 8-tool surface. This is the final Brief A task — all tool implementations must be complete before docs sync.

Changes required:
1. **h-mcp-kanban SKILL.md**: Rewrite tool reference to match the new 8-tool surface (list_tasks, show_task, pick_tasks, create_task, edit_task, move_task, start_work, end_work). Remove references to dropped tools (block_task, unblock_task, release_task). Document new params (archival_reason, archival_refs, dep_status, section, ids, outcome="block"). Update projection schemas (TaskSummary, TaskFull, DispatchEntry, Wave). Document guidance field.
2. **serve/mcp-kanban/README.md**: Update tool list, parameter signatures, and usage examples to match the implemented surface.

## Acceptance Criteria

- [ ] h-mcp-kanban SKILL.md lists exactly 8 tools with correct signatures per Brief A §5
- [ ] No references to dropped tools: block_task, unblock_task, release_task
- [ ] Projection schemas documented: TaskSummary (with dep_status, archival_reason, archival_refs), TaskFull, DispatchEntry, Wave
- [ ] end_work documents 4 outcomes: success, reject, release, block
- [ ] guidance field documented
- [ ] archival_reason enum (5 values) and archival_refs rules documented
- [ ] serve/mcp-kanban/README.md updated with matching tool list and signatures
- [ ] No stale references to `claimed_by`, `file` field, or legacy `status` param on edit_task