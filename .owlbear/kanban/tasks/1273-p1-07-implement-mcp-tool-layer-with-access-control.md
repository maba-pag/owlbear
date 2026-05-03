---
id: 1273
title: 'P1-07: Implement MCP tool layer with access control'
status: in-progress
priority: needed
created: 2026-05-02T03:43:38.542522+00:00
updated: 2026-05-03T11:18:41.775272+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1272
blocked: false
block_reason:
claimed_at: 2026-05-03T11:18:41.775272+00:00
archival_reason:
archival_refs: []
---

## Objective

Implement the 5 MCP tools with access control, state transition enforcement, and query logic. Must pass all tests from #1272.

Brief: see parent #1266

## Scope

**In scope:**
- Rewrite `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — 5 tool functions
- `store_learning(title, content, categories, confidence, scope_agents?)` → creates pending entry via engine
- `query_memory(categories?, scope_agents?, min_confidence?, limit?)` → filtered retrieval, default curated+approved, sorted approved-first then confidence desc
- `update_entry(entry_id, content?, categories?, confidence?, promote?)` → curator-only edits, pending→curated promotion
- `delete_entry(entry_id)` → curator-only, sets state=deleted
- `approve_entry(entry_id)` → user-only, curated→approved promotion
- State transition enforcement: reject invalid transitions with clear error messages
- `allowed_agents` config: tool-level restriction mechanism (curator tools reject non-curator callers)
- Wire tools into MCP server (`server.py` or equivalent registration)
- Update `__main__.py` to start the new server

**Out of scope:**
- Engine changes (completed in #1271)
- Model changes (completed in #1269)
- Skill documentation (handled by #1274)

## Acceptance Criteria

- [ ] All tests from #1272 pass GREEN
- [ ] 5 tools registered and callable via MCP
- [ ] store_learning creates entries with state=pending
- [ ] query_memory default excludes pending/deleted, sorts correctly
- [ ] update_entry enforces curator-only access
- [ ] delete_entry enforces curator-only access
- [ ] approve_entry enforces curated→approved only (rejects other states)
- [ ] Invalid state transitions produce ToolError with descriptive message
- [ ] Server starts via `uv run` entry point
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_mcp_memory_tools_1273.py
- Classes: TestFromAC_UpdateEntryFieldValidation, TestFromAC_QueryMemoryLimit
- Tests per category: happy 0, edge 2 (limit boundary), error 4 (validation failures, TypeError), boundary 0
- Total: 6 tests, all FAIL
- ruff: clean

**AC mapping:**
| AC line | Tests |
|---|---|
| update_entry enforces curator-only access | 2 field-validation tests (model_copy bypass bug) |
| query_memory default excludes pending/deleted, sorts correctly | 4 limit-parameter tests (scope interface gap) |
| All tests from #1272 pass GREEN | Verified — 71 existing tests PASS |
| store_learning creates entries with state=pending | Covered in test_mcp_memory_1266.py — no duplication |
| delete_entry enforces curator-only access | Covered in test_mcp_memory_1266.py |
| approve_entry enforces curated→approved only | Covered in test_mcp_memory_1266.py |
| Invalid state transitions produce ToolError with descriptive message | Message-content tests PASS (impl already correct) — removed per RED-phase rule |

**Root causes for failures:**
1. `update_entry` uses `model_copy(update=..., validate=False)` (Pydantic v2 default) — field validators (ge=0.7, min_length=1) are bypassed, invalid data written to disk silently. Fix: use `model_copy(..., validate=True)` and wrap ValidationError as ToolError.
2. `query_memory` missing `limit?` parameter (specified in scope interface) — TypeError on any call with `limit=`. Fix: add `limit: int | None = None` parameter and apply slice after sort.