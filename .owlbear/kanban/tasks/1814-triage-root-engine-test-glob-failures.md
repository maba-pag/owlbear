---
id: 1814
title: Triage root engine test glob failures
status: research
priority: important
created: 2026-05-24T09:12:53+02:00
updated: 2026-05-24T09:12:53+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent:
depends_on: []
ac:
  - Root `tests/test_engine_*.py tests/test_kanban_*.py` failures are grouped into current, actionable causes.
  - Stale structural/regression tests are updated or retired only with explicit approval.
  - A rerun of the root glob has an understood pass/fail status with any remaining failures linked to specific tasks.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
While verifying #1794, the mapped root engine/Kanban glob produced a broad unrelated failure set that is too large to fold into the dependency-status projection contract.

## Evidence
- Command: `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=short`
- Result: 73 failed, 531 passed.
- Failure clusters in the output included accessor-migration structural tests, dispatch/config validation expectations, MCP incomplete-agent-map expectations, validation predicate tests, Cockpit/session list tests, edit-task mutation tests, config path validation tests, and Kanban board split tests.

## Boundary
Do not repair this under #1794. Triage the clusters first and ask for implementation approval before changing product code or broad historical regression tests.