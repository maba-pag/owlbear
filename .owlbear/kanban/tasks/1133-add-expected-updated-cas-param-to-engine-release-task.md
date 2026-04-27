---
id: 1133
title: Add expected_updated CAS param to engine.release_task
status: research
priority: important
created: 2026-04-26T15:52:15.326051+00:00
updated: 2026-04-26T16:14:18.052358+00:00
tags:
- cockpit,kanban-engine
parent: 1130
depends_on:
- 1130
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Add OCC compare-and-swap support to engine.release_task() so cockpit can avoid clearing a fresh claim from a stale UI snapshot.

Acceptance Criteria:
- [ ] engine.release_task(task_id, *, expected_updated=None, source=engine) accepts optional OCC token.
- [ ] When expected_updated is provided, uses write_task_if_unchanged instead of write_task.
- [ ] ConcurrencyError(ERR_STALE) raised on mismatch (consistent with edit/move pattern).
- [ ] When expected_updated is None, behavior is unchanged (LWW for agent callers).
- [ ] CockpitView.release_task(task_id, *, expected_updated) requires the token (mirrors edit/move pattern).
- [ ] Unit tests cover: happy path with CAS, stale token conflict, None token (LWW fallback).

Scope boundary: Engine layer only (engine.py + CockpitView class). Route wiring is #1132.

Likely files:
- serve/kanban/src/owlbear_kanban/engine.py (release_task + CockpitView.release_task)
- tests/test_engine_cockpit_view_1078.py

Research: .owlbear/research/cockpit-mutation-occ-parity.md