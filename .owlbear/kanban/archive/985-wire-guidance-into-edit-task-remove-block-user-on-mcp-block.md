---
id: 985
title: Wire guidance into `edit_task` + remove `block:user` on MCP block
status: backlog
priority: needed
created: 2026-04-18T21:22:36.961973+00:00
updated: 2026-04-18T21:41:19.389680+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D3.

## Problem
MCP `edit_task` returns no guidance when blocking a task. Also, MCP block operations should remove any stale `block:user` tag (agent re-blocking takes ownership).

## Acceptance Criteria
- `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` after engine call.
- `edit_task(block=...)` returns `guidance` containing the DR-required message.
- `edit_task` block branch removes `block:user` tag if present via engine `remove_tags`.
- `edit_task` unblock branch also removes `block:user` if present.
- Integration test: `edit_task(block="reason")` → guidance contains DR message.
- Integration test: `edit_task(block="reason")` on task with `block:user` tag → tag removed.
- Integration test: `edit_task(unblock=True)` → no block guidance, `block:user` removed.
- Non-blocking `edit_task` (e.g. title change) → empty guidance.

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_edit_task_973.py` (new)

## Dependencies
- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/edit-task-guidance-985.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with implementation per Brief Path A1 and locked decisions D2, D3 (confidence: .90)
- Follow-up tasks created: none — #985 is already atomic with clear AC
- Decision requests: none — T1 autonomous (all decisions locked in Brief)

## Key Findings
1. **Atomic tag removal confirmed.** Engine `edit_task` accepts `blocked`, `block_reason`, and `remove_tags` in a single call. Block branch uses `kwargs.setdefault("remove_tags", []).append("block:user")` to combine with any user-supplied `remove_tag`.
2. **Guidance attachment pattern.** Post-engine-call: `_record_to_task(record)` → `collect_guidance("edit_task", before=None, after=task)` → assign to `task.guidance`. Wrapped in try/except per architect guidance note #5.
3. **Unblock branch also removes `block:user`.** Same `setdefault` pattern on the `elif unblock` branch.
4. **Dependencies #986 (model field) and #987 (guidance module) both still in research.** Must be wired as `depends_on` before #985 enters in-progress.

## Challenge Results
- Challenger: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions
- Confidence in original: .90
- Key challenges: N/A
- Researcher response: N/A

## Note
Task depends_on must be wired to [986, 987] per architect implementation guidance. Both deps are in research status.