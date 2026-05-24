---
id: 1815
title: Triage engine accessor migration root tests
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The 38 `tests/test_engine_accessor_migration.py` failures are classified as stale structural tests or current grouped-config defects.
  - Any source-inspection assertions are replaced with behavior-focused coverage only after explicit approval.
  - The accessor-migration slice has a verified pass/fail command and remaining failures are documented.
blocked: false
block_reason:
claimed_at:
archival_reason:
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