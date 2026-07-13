---
id: 1815
title: Repair engine accessor migration root tests
status: archived
priority: medium
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T10:50:02.826067+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The 38 `tests/test_engine_accessor_migration.py` failures are classified as
    stale structural tests or current grouped-config defects.
  - Source-inspection assertions are replaced with behavior-focused coverage
    after explicit approval.
  - The accessor-migration slice has a verified pass/fail command and remaining
    failures are documented.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The #1814 root glob currently has 38 failures in `tests/test_engine_accessor_migration.py`, concentrated in grouped config access, fixture schema, direct construction, predicate YAML nesting, and submodel mutation path checks.

## Evidence
- Command: `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no`
- Current root result: 72 failed, 532 passed.
- Failure cluster count: 38 failures in `tests/test_engine_accessor_migration.py`.

## Boundary
Do not update broad source-inspection tests or grouped-config behavior without explicit approval.

## Decision
User approved implementing #1815. The stale source-inspection tests referenced archived package-local files and old forwarding-property assertions. They are replaced with behavior-focused coverage for:
- `load_config()` projecting `PRODUCT_TOPOLOGY` into root and grouped submodels while preserving `next_id`.
- `KanbanEngine.board_config()` exposing grouped submodel instances.
- `refresh_config()` reloading only the `next_id` checkpoint from config-file topology.
- `create_task()` using product paths/defaults and rejecting ignored config-file status/priority values.
- Direct `BoardConfig.model_validate()` grouped and legacy-flat normalization behavior.

## Verification
- `uv run ruff check tests/test_engine_accessor_migration.py` — passed.
- `uv run pytest tests/test_engine_accessor_migration.py -q --tb=short` — 12 passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 14 failed, 526 passed.

## Remaining
The root glob is still red, but the remaining 14 failures are already represented by #1817, #1818, #1819, #1820, and #1821.