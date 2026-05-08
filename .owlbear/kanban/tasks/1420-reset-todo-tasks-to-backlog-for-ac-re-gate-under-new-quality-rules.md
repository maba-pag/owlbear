---
id: 1420
title: Reset todo tasks to backlog for AC re-gate under new quality rules
status: research
priority: needed
created: 2026-05-07T23:54:22.341303+00:00
updated: 2026-05-07T23:54:28.558228+00:00
tags:
- pipeline
- ws-ac-quality
- scope:board
parent: 1403
depends_on:
- 1405
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: All tasks that were in `todo` at the time A2 (#1405) deployed are moved to `backlog` via `move_task`
P2: Before state: N tasks in `todo`. After state: those N tasks are in `backlog`; tasks that were in `in-progress`, `review`, or `done` are untouched
P2: Tasks in `backlog` are now subject to architect re-gate under new AC quality rules (h-ac-quality)
P3: Verification by `list_tasks status=todo` confirming no pre-existing tasks remain; `list_tasks status=backlog` confirming they arrived

## Fallback

If the assigned agent cannot perform board operations (no MCP kanban tools available), return a Channel B message requesting the orchestrator to execute the reset. Include the list of task IDs to move.

## Scope

**In scope:** Board state changes only — move tasks from `todo` to `backlog`
**Out of scope:** Modifying task content, re-writing AC, any skill/code changes
