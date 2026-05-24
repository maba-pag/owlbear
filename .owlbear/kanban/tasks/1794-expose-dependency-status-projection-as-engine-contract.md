---
id: 1794
title: Expose dependency status projection as engine contract
status: done
priority: important
created: 2026-05-24T02:02:33.566320+02:00
updated: 2026-05-24T09:12:53+02:00
tags:
  - scope:kanban-engine
  - scope:cockpit-web
  - data-contract
  - technical-debt
  - discussion
parent: 1790
depends_on: []
ac:
  - Dependency status projection has a named engine/view contract used by both 
    list and show task projections.
  - Cockpit continues to consume `dep_status` only through API responses.
  - No direct task-file reads or writes are introduced.
  - Tests cover list and show projections for blocked/ok/no dependency cases.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
proof_bundle: smoke
---
## Observation
#1790 traced `dep_status` and confirmed Cockpit receives it from Kanban/Cockpit API projections, not direct filesystem reads. However, `AgentView.show_task` computes full-task `dep_status` by calling `engine._compute_dep_status()` with `# noqa: SLF001`, meaning the projection path relies on a private helper.

## Decision
User chose to create an engine cleanup task rather than hide the field or treat it as unsafe.

## Goal
Make dependency-status projection an explicit engine/view contract so list and show projections use a named public/internal projection method rather than reaching into a private helper.

## Resolution
Implemented `KanbanEngine.project_dep_status()` as the named read-time projection contract. `list_tasks()` now uses that contract with its full active/archive snapshot, and `AgentView.show_task()` uses the same contract for single-task projection instead of reaching into `_compute_dep_status()`.

`AgentView.start_work()` now also calls the public projection contract after building its active dependency context for guidance. The private pure helper remains internal to `KanbanEngine`; no Cockpit frontend code or task-file read/write path was added.

## Test Updates
Added `tests/test_engine_dependency_projection_1794.py` to cover list/show parity for blocked, ok, and no-dependency cases and to assert list/show use `project_dep_status()` directly. Updated stale dep-status tests so active unresolved dependencies remain `blocked`, matching the current engine contract and start-work guidance behavior.

## Verification
- `uv run pytest tests/test_engine_dependency_projection_1794.py tests/test_engine_dep_lookup.py serve/kanban/tests/test_engine_reads.py serve/kanban/tests/test_engine_list_show.py serve/kanban/tests/test_agent_view_dep_exception_parity.py serve/kanban/tests/test_engine_pick_tasks.py serve/kanban/tests/test_engine_coverage.py::TestFromAC_EngineListTasks::test_dep_status_included_in_summary serve/kanban/tests/test_agent_view_start_work_1526.py tests/test_start_work_dep_guidance_1526.py tests/test_agent_view_1527.py -q --tb=short` -> 150 passed.
- `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/agent_view.py tests/test_engine_dependency_projection_1794.py tests/test_engine_dep_lookup.py serve/kanban/tests/test_engine_list_show.py serve/kanban/tests/test_engine_reads.py serve/kanban/tests/test_engine_coverage.py serve/kanban/tests/test_agent_view_dep_exception_parity.py serve/kanban/tests/test_engine_pick_tasks.py` -> all checks passed.

## Follow-Up
Package-level `serve/kanban/tests/` still has three unrelated `list_sessions` failures; recorded separately as #1813 and left out of this implementation.
