---
id: 1816
title: Triage dispatch validation and agent map tests
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
tags:
  - scope:kanban-engine
  - scope:mcp-kanban
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - Dispatch-rank validation failures are separated from lazy `agent_map` validation failures.
  - MCP `pick_tasks` ToolError expectations are verified against the current server behavior.
  - A focused command for this cluster has an understood pass/fail result before implementation.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has 20 dispatch/agent-map failures: 10 in `tests/test_engine_dispatch_validation.py` and 10 in `tests/test_engine_lazy_agent_map.py`.

## Evidence
- `tests/test_engine_dispatch_validation.py`: init/refresh dispatch-rank mismatch tests did not raise `ConfigError`.
- `tests/test_engine_lazy_agent_map.py`: `pick_tasks` incomplete `agent_map` tests and MCP ToolError tests did not raise expected errors.

## Boundary
Do not decide whether empty/incomplete `agent_map` is valid for Cockpit versus dispatch until this cluster is reviewed.