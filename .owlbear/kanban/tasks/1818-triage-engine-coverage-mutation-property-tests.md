---
id: 1818
title: Repair engine coverage mutation and property tests
status: done
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:55:12+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - Edit-task mutation failures are classified separately from board-config deep-copy failures.
  - The current return contract for `edit_task` dependency/parent mutations is verified before changes.
  - Deep-copy expectations are checked against the current grouped `BoardConfig` model.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has six failures in `serve/kanban/tests/test_engine_coverage.py`: three edit-task mutation return tests and three board-config deep-copy tests.

## Evidence
- Edit mutation failures: parent mutation, add-deps merge, add-deps idempotence.
- Property failures: nested dict copy, nested agent map copy, nested existing list isolation.

## Boundary
Do not change mutation return semantics or config-copy behavior without focused approval.

## Decision
User approved implementing #1818. The six failures were stale test expectations, not observed product defects:
- `edit_task()` now rejects dangling parent/dependency references, so mutation-return tests must create the referenced task files before asserting successful edits.
- `BoardConfig` is grouped; defensive-copy checks must mutate `config.agents.*` and `config.policy.*`, not removed top-level `config.agent_map` fields.

No product code change was needed.

## Verification
- `uv run ruff check tests/test_engine_coverage.py` — passed.
- `uv run pytest tests/test_engine_coverage.py -q --tb=short` — 23 passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 5 failed, 535 passed.

## Remaining
The root glob remains red due to #1819, #1820, and #1821.