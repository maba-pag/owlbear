---
id: 1814
title: Triage root engine test glob failures
status: done
priority: important
created: 2026-05-24T09:12:53+02:00
updated: 2026-05-24T09:23:21+02:00
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
proof_bundle: smoke
---
## Observation
While verifying #1794, the mapped root engine/Kanban glob produced a broad unrelated failure set that is too large to fold into the dependency-status projection contract.

## Evidence
- Command: `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=short`
- Result: 73 failed, 531 passed.
- Failure clusters in the output included accessor-migration structural tests, dispatch/config validation expectations, MCP incomplete-agent-map expectations, validation predicate tests, Cockpit/session list tests, edit-task mutation tests, config path validation tests, and Kanban board split tests.

## Boundary
Triage only. Do not change product code or broad historical regression tests without explicit approval of a child task.

## Current Rerun
- Command: `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no`
- Result after #1813: 72 failed, 532 passed.
- Result after #1816: 52 failed, 540 passed.
- Result after #1815: 14 failed, 526 passed.
- Result after #1817: 11 failed, 529 passed.
- Result after #1818: 5 failed, 535 passed.
- Result after #1819: 3 failed, 537 passed.
- Result after #1820: 2 failed, 538 passed.
- Result after #1821: 540 passed.

## Failure Groups
- #1815: 38 accessor-migration grouped-config/source-inspection failures in `tests/test_engine_accessor_migration.py` (resolved in #1815).
- #1816: 20 dispatch validation, lazy `agent_map`, and MCP `pick_tasks` error-surface failures across `tests/test_engine_dispatch_validation.py` and `tests/test_engine_lazy_agent_map.py` (resolved in #1816).
- #1817: 3 validation-push predicate/error-code failures in `tests/test_engine_validation_push.py` (resolved in #1817).
- #1818: 6 engine coverage failures around edit-task mutation returns and board-config deep-copy behavior (resolved in #1818).
- #1819: 2 config path validation failures around symlink escape refresh and nested archive directory movement (resolved in #1819).
- #1820: 1 scan-based ID allocation concurrency failure in `tests/test_engine_1443.py` (resolved in #1820).
- #1821: 2 Kanban board split static/source-layout failures in `tests/test_kanban_board_split.py` (resolved in #1821).

## Recommendation
The root engine/Kanban glob is green. Continue with product-facing Cockpit work or the new #1822 1024px board-overflow review.