---
id: 1819
title: Repair kanban config path validation tests
status: archived
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T10:50:02.881312+02:00
tags:
  - scope:kanban-engine
  - security
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The symlink-escape refresh failure is classified as stale test, missing
    runtime defense, or fixture issue.
  - The nested archive subdirectory move failure is traced to current
    path-containment behavior.
  - Any security-sensitive path validation change has focused tests before
    implementation.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The #1814 root glob has two failures in `tests/test_kanban_config_path_validation.py`, covering refresh-time symlink escape rejection and moving to an archive configured as a nested subdirectory.

## Boundary
Treat this as security-sensitive. Do not relax path containment without explicit approval and focused proof.

## Decision
User approved implementing #1819. The failures were stale runtime-topology expectations, not an observed path-containment defect:
- `refresh_config()` should still reject a symlink escape on the canonical product `tasks/` path. The repaired test now proves that real defense.
- Storage runtime ignores config-file path overrides because `PRODUCT_TOPOLOGY` owns `tasks_dir` and `archive_dir`; the nested archive test now asserts moves go to product `archive/`.

No path containment was relaxed.

## Verification
- `uv run ruff check tests/test_kanban_config_path_validation.py` — passed.
- `uv run pytest tests/test_kanban_config_path_validation.py -q --tb=short` — 22 passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 3 failed, 537 passed.

## Remaining
The root glob remains red due to #1820 and #1821.