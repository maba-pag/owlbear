---
id: 675
title: Add per-package tests for mcp-memory server
status: backlog
priority: needed
created: 2026-04-08T18:14:33.571087+02:00
updated: 2026-04-08T18:14:33.571087+02:00
tags:
    - scope:mcp-memory
    - ' type:test'
    - ' source:analysis'
depends_on:
    - 674
class: standard
---

## Context

Analysis synthesis identified that `serve/mcp-memory/` has zero per-package tests — no `tests/` directory exists. This is the only MCP server without local tests. The memory server contains the most self-contained logic of any server (approval state machine, scope-tiered sorting, confidence validation, and curator integration).

Root test files (`test_approve_memory_531.py`, `test_approve_memory_585.py`) exist but reference stale `packages/` paths (being fixed in #674).

## Acceptance Criteria

- [ ] AC1: `serve/mcp-memory/tests/` directory exists with `conftest.py` and at least 1 test file
- [ ] AC2: Approval state machine tested — all 3 valid transitions (`pending→approved`, `pending→deleted`, `deleted→pending`) and rejection of invalid transitions
- [ ] AC3: `record_learning` validation tested — confidence below 0.7 returns error, invalid category returns error
- [ ] AC4: `get_knowledge` scope-tiered sort order tested — tier 1 (agent+project) before tier 4 (global)
- [ ] AC5: `mark_for_deletion` idempotency tested — calling twice on same entry succeeds
- [ ] AC6: `list_entries` filter combinations tested — by agent_id, category, status, include_deleted
- [ ] AC7: Package smoke test — `import owlbear_mcp_memory` succeeds

Depends on: #674 (stale path fixes)
