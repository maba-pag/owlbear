---
id: 848
title: Clean up stale test_pick_tasks.py — 38 tests broken by kanban_bin migration
status: research
priority: nice-to-have
created: '2026-04-12T12:13:32.236167+00:00'
updated: '2026-04-12T12:13:32.236167+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- All 38 tests in `tests/test_pick_tasks.py` either pass or are intentionally removed/archived
- If tests are updated: replace stale `kanban_bin` AppContext with engine-based pattern
- If tests are removed: gate/sort/limit coverage is verified to exist in other test files (#823, #825, test_kanban_mcp_migration.py)
- No net reduction in pick_tasks behavioral coverage

## Context

`test_pick_tasks.py` (consolidated from #620, #621, #628) uses the pre-Phase-2 `AppContext(kanban_bin=...)` pattern. All 38 tests fail with `TypeError: AppContext.__init__() got an unexpected keyword argument 'kanban_bin'`. This was broken by Phase 2 engine extraction, not by #826.

The tests cover gate logic, sort order, limit capping, edge cases, null-body safety, and tag passthrough. Most of this coverage is now duplicated across `test_pick_dispatchable_823.py`, `test_pick_dispatchable_824.py`, `test_server_pick_tasks_thin_wrapper_825.py`, and `test_kanban_mcp_migration.py`.

**Research needed:** verify coverage overlap before deciding update vs. remove.

Source: `.owlbear/research/slim-server-pick-tasks.md` §3.4