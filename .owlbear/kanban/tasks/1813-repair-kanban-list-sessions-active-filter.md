---
id: 1813
title: Repair kanban list_sessions active filter failures
status: research
priority: important
created: 2026-05-24T09:10:04+02:00
updated: 2026-05-24T09:10:04+02:00
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
This appears unrelated to #1794's `dep_status` projection contract. Do not repair it without explicit approval.