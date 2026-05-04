---
id: 1342
title: 'Fix pick_tasks wave assembly: greedy algorithm constraint bugs'
status: todo
priority: needed
created: 2026-05-04T15:10:47.698484+00:00
updated: 2026-05-04T15:11:11.898492+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

`serve/kanban/src/owlbear_kanban/agent_view.py` (L300–540) implements a greedy bin-packing wave assembler. 20 tests in `serve/kanban/tests/test_engine_pick_tasks_1074.py` are red. The algorithm has bugs in: (a) dependency-disjointness checking (no intra-wave dep edges), (b) agent-bucket compatibility matching (D62/D63 symmetric check), (c) wave-size cap enforcement.

This is finished code that must work before sync. The feature decides what work gets dispatched to agents — it's the central process starter.

## Acceptance Criteria

1. All 20 tests in `serve/kanban/tests/test_engine_pick_tasks_1074.py` pass
2. Filter stage correctly excludes: claimed tasks, blocked=true, archived status, dep_status="blocked"
3. Sort stage produces deterministic order: priority_rank ASC, age DESC, id ASC
4. Greedy wave assembly respects all three constraints:
   - Wave length ≤ effective wave_size
   - No dependency edges between tasks in same wave
   - Agent-bucket compatibility (symmetric — D63)
5. AC27: wontfix-archived deps exclude dependent tasks
6. AC28: deprecated-archived deps set dep_status to redirect string
7. No regression in passing engine tests

## Key Files

- `serve/kanban/src/owlbear_kanban/agent_view.py` (L300–540)
- `serve/kanban/src/owlbear_kanban/dispatch.py`
- `serve/kanban/tests/test_engine_pick_tasks_1074.py`

## Source

Research: `.owlbear/research/kanban-mcp-deployment-audit.md`