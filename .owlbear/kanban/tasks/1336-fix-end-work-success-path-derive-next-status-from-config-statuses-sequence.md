---
id: 1336
title: 'Fix end_work success path: derive next status from config.statuses sequence'
status: todo
priority: critical
created: 2026-05-04T15:00:05.698435+00:00
updated: 2026-05-04T15:08:59.893198+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-04T15:08:59.893198+00:00
archival_reason:
archival_refs: []
---

## Context

In `serve/kanban/src/owlbear_kanban/engine.py`, the `end_work(outcome="success")` path defaults `move_to="research"` instead of computing next status from `config.statuses[idx+1]` per Brief B design. This regresses tasks backward instead of advancing them.

## Acceptance Criteria

1. `end_work(outcome="success")` reads the task's current status, finds its index in config.statuses, and moves to statuses[idx+1]
2. If already at the last status, raise a clear error (cannot advance past final status)
3. `end_work(outcome="reject", move_to=X)` still uses explicit move_to (no change)
4. All currently-red tests in test_engine_coverage_1068 and test_list_sessions_952 that test success advancement must pass
5. No regression in passing engine lifecycle tests

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/config_loader.py`
- `.owlbear/research/end-work-compound-tool.md` §3.2
- `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md`

## Source

Finding 1 in `.owlbear/research/kanban-mcp-deployment-audit.md`