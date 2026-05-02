---
id: 1275
title: Fix stale test assertions in test_mcp_memory_1267.py
status: todo
priority: nice-to-have
created: 2026-05-02T06:23:30.198676+00:00
updated: 2026-05-02T07:43:19.197134+00:00
tags:
- scope:mcp-memory
- cleanup
- type:test
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

- [ ] Remove the four stale test functions (`test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call`) — `test_no_sqlite3_import_in_any_source_file` already covers the SQLite-absence invariant across all source files, making per-file deletion assertions redundant now that the files were recreated with non-SQLite implementations (td:0)
- [ ] If removing all tests from a class leaves it empty, remove the empty class too (td:0)
- [ ] `uv run pytest tests/test_mcp_memory_1267.py` passes (td:0)
- [ ] No other test files regress (td:0)

## Architecture Review

**Verdict:** APPROVED — simple test maintenance, all td:0

**AC Assessment:**

| AC line | Assessment | Action |
|---------|-----------|--------|
| Remove four stale tests | Clear, named targets, correct rationale | Refined from "update or remove" to "remove" — update path redundant with existing broader check |
| Remove empty classes | Added — prevents orphan class shells after deletion | New |
| pytest pass | Verifiable command | Kept as-is |
| No regression | Standard guard | Kept as-is |

**Architecture notes:**
- `server.py` now contains FastMCP server (`from mcp.server.fastmcp import ...`), no SQLite
- `tools.py` is markdown-backed (`from owlbear_mcp_memory.models import ...`), no SQLite
- `__main__.py` is a proper entry point again (`from owlbear_mcp_memory.server import mcp`)
- `test_no_sqlite3_import_in_any_source_file` (remaining in the same file) scans ALL `.py` files under `src/` — the SQLite invariant is still guarded
- Sibling test files `test_mcp_memory_1266.py` and `test_mcp_memory_1269.py` cover new implementations

**Dependency analysis:** No dependencies needed — all prerequisite changes (file recreation) already landed.

**Test-writer: SKIP** — all AC lines td:0 (mechanical test cleanup).

[[2026-05-02]]
APPROVED → todo. Refined AC: narrowed "update or remove" to "remove only" — the update path is redundant with existing `test_no_sqlite3_import_in_any_source_file`. Added empty-class cleanup AC. All td:0, Test-writer: SKIP. Tagged `type:test` for pass-through.