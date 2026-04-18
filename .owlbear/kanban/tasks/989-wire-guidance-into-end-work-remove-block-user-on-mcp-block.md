---
id: 989
title: Wire guidance into `end_work` + remove `block:user` on MCP block
status: backlog
priority: needed
created: 2026-04-18T21:23:00.860323+00:00
updated: 2026-04-18T21:44:39.398134+00:00
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
MCP `end_work` returns no guidance when blocking or succeeding. Also, `end_work(outcome="block")` should remove any stale `block:user` tag.

## Acceptance Criteria
- `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` after engine call.
- `end_work(outcome="block")` returns `guidance` containing the DR-required message.
- `end_work(outcome="block")` removes `block:user` tag if present.
- `end_work(outcome="success")` returns `guidance` with commit-pushed reminder.
- `end_work(outcome="fail")` and `end_work(outcome="reject")` → empty guidance.
- Integration test per outcome.

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_end_work_973.py` (new)

## Dependencies
- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/end-work-guidance-989.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with implementation per Brief Path A1 and locked decisions D2, D3 (confidence: .90)
- Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions
- Follow-up tasks created: none — #989 is already atomic with clear AC
- Decision requests: none — T1 autonomous (all decisions locked in Brief)

## Key Findings
1. **Non-atomic tag removal confirmed.** Engine `end_work` does NOT accept `remove_tags`. Sequential calls required: `engine.end_work()` → `engine.edit_task(task_id, remove_tags=["block:user"])`. Engine `edit_task` does not require a claim. Architect rebuttal C1 confirmed this path.
2. **Guidance attachment pattern.** Same as sibling #985: `_record_to_task(record)` → `collect_guidance("end_work", before=None, after=task, outcome=outcome)` → assign to `task.guidance`. Wrapped in try/except per architect note #5.
3. **Four outcomes mapped.** Block → DR guidance + tag removal. Success → commit reminder. Fail/reject → empty guidance. All clearly defined in AC and guidance module spec (#987).
4. **Dependencies #986 (model field) and #987 (guidance module) both in research.** Must be wired as `depends_on` before #989 enters in-progress. Both calls use `asyncio.to_thread`.