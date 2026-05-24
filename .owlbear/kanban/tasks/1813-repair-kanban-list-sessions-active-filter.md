---
id: 1813
title: Repair kanban list_sessions active filter failures
status: done
priority: important
created: 2026-05-24T09:10:04+02:00
updated: 2026-05-24T09:20:20+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent:
depends_on: []
ac:
  - The default `list_sessions` filter returns running and stuck sessions from valid log lines.
  - Invalid JSON activity-log lines are skipped without dropping later valid session entries.
  - `serve/kanban/tests/test_list_sessions.py::TestFromAC_ListSessions::test_default_filter_returns_running_and_stuck_only` passes.
  - The `TestFromAC_EngineListSessions` coverage tests for active sessions and invalid JSON pass.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
proof_bundle: smoke
---
## Observation
While verifying #1794 with the package-level Kanban suite, the dependency-status tests were repaired, but three `list_sessions` tests continued to fail outside the dependency projection contract.

## Evidence
- Command: `uv run pytest serve/kanban/tests/ -q --tb=short`
- Result: 3 failed, 1355 passed.
- Failures:
  - `serve/kanban/tests/test_list_sessions.py::TestFromAC_ListSessions::test_default_filter_returns_running_and_stuck_only` returned no active sessions.
  - `serve/kanban/tests/test_engine_coverage.py::TestFromAC_EngineListSessions::test_active_session_filter_returns_running` returned an empty session list.
  - `serve/kanban/tests/test_engine_coverage.py::TestFromAC_EngineListSessions::test_invalid_json_line_skipped` returned an empty session list after an invalid JSON line.

## Boundary
User selected this task for implementation after #1794.

## Resolution
Removed the current-task-claim pruning from the public `list_sessions()` read path. The method now returns sessions derived from valid `activity.jsonl` entries and then applies the requested session-state filter. Cleanup still uses `_session_matches_current_claim()` directly when deciding whether to close stale active sessions.

## Verification
- `uv run pytest serve/kanban/tests/test_list_sessions.py::TestFromAC_ListSessions::test_default_filter_returns_running_and_stuck_only serve/kanban/tests/test_engine_coverage.py::TestFromAC_EngineListSessions::test_active_session_filter_returns_running serve/kanban/tests/test_engine_coverage.py::TestFromAC_EngineListSessions::test_invalid_json_line_skipped -q --tb=short` -> 3 passed.
- `uv run pytest serve/kanban/tests/ -q --tb=short` -> 1358 passed.
- `uv run pytest tests/test_engine_activity_session.py serve/kanban/tests/test_engine_activity.py tests/test_engine_cockpit_view.py -q --tb=short` -> 88 passed.
- `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py` -> all checks passed.
