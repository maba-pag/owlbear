---
id: 1816
title: Repair dispatch validation and agent map tests
status: archived
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T10:50:02.842425+02:00
tags:
  - scope:kanban-engine
  - scope:mcp-kanban
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - Dispatch-rank validation failures are separated from lazy `agent_map`
    validation failures.
  - MCP `pick_tasks` ToolError expectations are verified against the current
    server behavior.
  - A focused command for this cluster has an understood pass/fail result before
    implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The #1814 root glob has 20 dispatch/agent-map failures: 10 in `tests/test_engine_dispatch_validation.py` and 10 in `tests/test_engine_lazy_agent_map.py`.

## Evidence
- `tests/test_engine_dispatch_validation.py`: init/refresh dispatch-rank mismatch tests did not raise `ConfigError`.
- `tests/test_engine_lazy_agent_map.py`: `pick_tasks` incomplete `agent_map` tests and MCP ToolError tests did not raise expected errors.

## Boundary
User selected this slice for implementation after #1814 triage.

## Resolution
Replaced stale config-driven dispatch validation tests with product-topology authority tests. `load_config()` now intentionally treats config.yml as a `next_id` checkpoint; statuses, priorities, wave size defaults, and `agent_map` come from `PRODUCT_TOPOLOGY`. The updated tests assert that unknown config-file statuses/priorities and incomplete config-file `agent_map` entries do not override runtime topology.

MCP `pick_tasks` coverage now asserts the current behavior: incomplete config-file `agent_map` does not raise `ToolError`, while explicit invalid `wave_size` still maps to a `ToolError` containing `ERR_INVALID_WAVE_PARAM`.

## Verification
- `uv run pytest tests/test_engine_dispatch_validation.py tests/test_engine_lazy_agent_map.py -q --tb=short` -> 12 passed.
- `uv run ruff check tests/test_engine_dispatch_validation.py tests/test_engine_lazy_agent_map.py` -> all checks passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` -> root glob reduced to 52 failed, 540 passed; remaining failures are outside #1816 and tracked by #1815, #1817, #1818, #1819, #1820, and #1821.