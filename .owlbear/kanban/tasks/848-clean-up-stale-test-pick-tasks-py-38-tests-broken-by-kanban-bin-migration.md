---
id: 848
title: Clean up stale test_pick_tasks.py — 38 tests broken by kanban_bin migration
status: backlog
priority: nice-to-have
created: '2026-04-12T12:13:32.236167+00:00'
updated: '2026-04-13T20:51:22.921613+00:00'
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
[[2026-04-13]]
## Research

Verified coverage overlap between 38 stale tests in `test_pick_tasks.py` and replacement suite (93 tests across 4 files).

**Key findings:**
- 24/38 tests have direct behavioral equivalents in #823/#824/#825/migration tests
- 10/38 test `_run_kanban` CLI patterns that no longer exist (engine extraction)
- 2/38 test atomicity gate intentionally dropped from `dispatch.py`
- 2/38 test JSON null-body scenario made impossible by Pydantic `body: str=""` model

**Trade-off matrix:** Update vs. Remove → Remove wins at .95 confidence. Updating would duplicate 93 existing tests using obsolete mock patterns.

**Follow-up:** #867 — delete `test_pick_tasks.py` (backlog, trivial file deletion)
**Doc:** `.owlbear/research/stale-test-pick-tasks-cleanup.md`