---
id: 1184
title: 'P1-05: Test pick_tasks resolve_pending_drs integration'
status: backlog
priority: needed
created: 2026-04-30T00:51:47.776679+00:00
updated: 2026-04-30T00:58:18.205204+00:00
tags:
- phase-1
- scope:kanban
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test that `pick_tasks` calls `resolve_pending_drs` before task selection logic
- Test that resolve exceptions do NOT propagate to `pick_tasks` caller (try/except wrapping)
- Test that resolved DRs are processed before task filtering occurs
- Test pick_tasks still functions correctly when no pending DRs exist
- Test pick_tasks still functions correctly when pending/ directory doesn't exist

## Scope

- IN: integration test for resolve call within pick_tasks flow
- OUT: decisions.py unit tests (covered by #1180), MCP layer

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/pick-tasks-resolve-integration-testing.md
- Sources: 5 studied, 5 high-relevance (all codebase/brief — no external sources needed)
- Recommendation: 5 tests using monkeypatch on `decisions.resolve_pending_drs`; mock at module function level, not private method (confidence: .90)
- Follow-up tasks created: none (this IS the test task)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — test specification task with clear established patterns; no design decision to challenge
- Key findings: existing test_engine_pick_tasks_1074.py establishes all patterns needed (tmp_path boards, _make_board helpers); mock target is `owlbear_kanban.decisions.resolve_pending_drs`; test file goes at `tests/test_pick_tasks_resolve_1184.py`