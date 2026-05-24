---
id: 1854
title: 'P1-04: Engine API — list_requests and sweep'
status: backlog
priority: needed
created: 2026-05-24T20:58:29.519700+02:00
updated: 2026-05-24T21:00:29.440957+02:00
tags:
  - phase-1
  - scope:kanban
  - api
parent: 1850
depends_on:
  - 1853
ac:
  - list_requests(status, task_id) returns requests filtered by status 
    ("pending" | "resolved" | "all", default "pending") and optional task_id; 
    returns empty list when no matches exist.
  - Sweep function scans pending/ for files where resolution.selected_option_id 
    is non-null OR resolution.free_text is non-null; for each match, sets 
    resolved_at, moves to resolved/, appends write-back, and conditionally 
    unblocks.
  - Sweep is invoked as part of pick_tasks execution — when pick_tasks runs, 
    sweep executes before task selection.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `list_requests` engine function with status and task_id filters
- New sweep function for structured DR schema (detects non-null resolution fields)
- Integration point: wire sweep into `pick_tasks` (agent_view module)
- Sweep handles: manual file edits, crash recovery scenarios

**Out of scope:**
- MCP/Cockpit layers
- Old `resolve_pending_drs` function (retained for backward compat until P2-05/P2-06 removal)

## Test scope
`serve/kanban/tests/` and `tests/test_engine_*`