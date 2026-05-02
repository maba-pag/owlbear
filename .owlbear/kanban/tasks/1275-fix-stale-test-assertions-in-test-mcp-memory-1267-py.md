---
id: 1275
title: Fix stale test assertions in test_mcp_memory_1267.py
status: backlog
priority: nice-to-have
created: 2026-05-02T06:23:30.198676+00:00
updated: 2026-05-02T06:23:42.125355+00:00
tags:
- scope:mcp-memory
- cleanup
parent: 1266
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Four tests in `tests/test_mcp_memory_1267.py` now fail because they assert file absence for `server.py`, `tools.py`, and `__main__.py` — files that were deleted by #1267 but recreated by subsequent epic #1266 children with new file-based implementations.

### Failing tests
- `test_server_py_deleted`
- `test_tools_py_deleted`
- `test_main_py_has_no_server_import`
- `test_main_py_has_no_mcp_run_call`

## Acceptance Criteria

- [ ] All four stale assertions are either updated to check for SQLite absence specifically, or removed (since subsequent task tests cover the new implementations)
- [ ] `uv run pytest tests/test_mcp_memory_1267.py` passes
- [ ] No other test files regress