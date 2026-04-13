---
id: 860
title: Add sync_from_global and sync_to_global MCP tools
status: in-progress
priority: important
created: '2026-04-13T13:55:19.633331+00:00'
updated: '2026-04-13T19:01:37.328062+00:00'
tags:
- scope:knowledge
parent: null
depends_on:
- 858
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Split from #858 (sync tool AC items). After #858 establishes the local.db/global.db naming convention and global DB path resolution, this task adds two MCP tools for syncing between them.

Both tools wrap the existing `_do_import` function in `scope_transfer.py` which handles content-hash dedup, FK remapping, and atomic transactions.

## Acceptance Criteria

- [ ] New MCP tool `sync_from_global` in mcp-knowledge server.py:
  - Zero user-facing parameters (resolves paths internally)
  - Resolves global DB path via the global-path resolution function from #858
  - Opens global DB as read-only source connection
  - Calls `_do_import(src_conn=global_conn, dest_conn=local_conn, target_scope="global")` to import all entries into local DB under scope `"global"`
  - Content-hash dedup: duplicate documents (same hash) are skipped (existing `_do_import` behavior)
  - Returns count string: `"Imported {n} documents (skipped {m} duplicates) from global into local under scope 'global'"`
  - Returns `"error: global DB not found at {path}"` if global DB file doesn't exist
  - Returns `"error: global DB path could not be resolved"` if `owlbear-project.json` is missing or malformed
  - ToolAnnotations: `readOnlyHint=False, destructiveHint=False`
- [ ] New MCP tool `sync_to_global` in mcp-knowledge server.py:
  - Zero user-facing parameters
  - Resolves global DB path via same function
  - Opens global DB as read-write destination connection
  - Queries local DB for all entries with `scope="global"`, imports them into global DB with content-hash dedup
  - Creates global DB file (with `init_db` schema) if it doesn't exist yet
  - Returns count string: `"Exported {n} documents (skipped {m} duplicates) from local scope 'global' to global DB"`
  - Returns `"error: ..."` if global DB path can't be resolved
  - ToolAnnotations: `readOnlyHint=False, destructiveHint=False`
- [ ] Existing `import_scope`/`export_scope` MCP tools continue to work unchanged (regression check)
- [ ] Both tools registered in `__all__` and in the mcp FastMCP instance

## Technical notes

- `_do_import` already handles content-hash dedup and FK remapping — sync tools are thin wrappers
- Global DB merge is safe for concurrent projects because dedup is additive (skip existing docs by hash)
- The global-path resolution function is implemented in #858 — this task consumes it
[[2026-04-13]]
## Architecture Review

### AC Refinements

**CRITICAL — `_do_import` source-scope filtering:**
The AC claims sync tools are "thin wrappers" around `_do_import`, but `_do_import` reads ALL source rows unconditionally (`SELECT * FROM documents`). For `sync_to_global`, only `scope="global"` entries from local should be exported. Without a source-scope filter, `sync_to_global` would copy the entire local DB into global.

**Resolution (add to AC):**
- Extend `_do_import` with optional `source_scope: str | None = None` kwarg. When non-None, all source table reads are filtered with `WHERE scope = ?`. Default `None` preserves current behavior — backward-compatible.
- `sync_to_global` calls `_do_import(src_conn=local_conn, dest_conn=global_conn, target_scope="global", source_scope="global")`
- Update existing `import_scope` caller: no change needed (passes `source_scope=None` implicitly)

**Return message format:**
`_do_import` returns `f"Imported {n} documents (skipped {m} duplicates) into scope {target_scope}"`. The AC specifies different custom messages. Builder should either: (a) refactor `_do_import` to return `tuple[int, int]` (imported, skipped) so callers can format custom strings, updating `import_scope` accordingly; or (b) accept `_do_import`'s native format. Recommend (a) for clarity — "Exported" vs "Imported" matters semantically for `sync_to_global`.

**Connection lifecycle:**
Both sync tools must close their secondary connection (global DB) in a `finally` block, following the pattern in `import_scope` (scope_transfer.py L330-333).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two related sync tools + one `_do_import` enhancement, all in knowledge domain |
| Interface clarity | PASS (after refinement) | `source_scope` addition makes `sync_to_global` feasible; return format clarified |
| Dependency correctness | PASS | Depends on #858 (todo) for global path resolution; `depends_on` field enforces ordering |
| Module layering | PASS | mcp-knowledge server imports from knowledge package; `_do_import` change is in knowledge package |
| TDD compliance | PASS | Test-writer will process before builder |
| KISS/YAGNI | PASS | Thin wrappers + one backward-compatible kwarg; zero-parameter design with env var override from #858 |
| Premise challenge | PASS | Sync tools are the user-facing layer for multi-project knowledge sharing (decision #616) |
| Pattern consistency | PASS | Follows existing MCP tool patterns: `@mcp.tool(annotations=...)`, `asyncio.to_thread()`, `ctx.request_context.lifespan_context`, error string convention |
| Security surface | PASS | Global DB path resolved from trusted config (`owlbear-project.json`); no user-controlled path input; sandbox_path not needed (global path is intentionally outside workspace) |
| Single domain | PASS | All within knowledge domain |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| sync_from_global | Global path unresolvable | N/A | Yes (error: string) | Clear error message |
| sync_from_global | Global DB file missing | N/A | Yes (error: string) | Clear error message |
| sync_from_global | Global DB corrupt/wrong schema | sqlite3.Error | Yes (via `_do_import` catch) | Error string returned |
| sync_to_global | Global path unresolvable | N/A | Yes (error: string) | Clear error message |
| sync_to_global | Global DB dir missing (new file) | os error | Builder must mkdir parents=True before init_db | Auto-created |
| sync_to_global | `_do_import` fails mid-transaction | sqlite3.Error | Yes (atomic rollback via `with dest_conn:`) | No partial writes |

### Challenge Results
- Challenger: proceed (Approach A — `source_scope` param — recommended; zero-param design acceptable; concurrency safe)
- Architect response: accepted; refinements incorporated

### Builder Guidance
**Files to modify:**
- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — add `source_scope` kwarg to `_do_import`; optionally refactor return type
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — add `sync_from_global` and `sync_to_global` tools, register in `__all__`

**Patterns to follow:**
- `import_scope` MCP tool (server.py L451-471) for async wrapping pattern
- `_do_import` try/finally connection close pattern (scope_transfer.py L330-333)
- `init_db` for creating new global DB schema (scope_transfer.py L14)

### Verdict: APPROVE (with refinements noted above)
### Action Taken: AC refinements documented in Architecture Review; advanced to todo
[[2026-04-13]]
## Test-Writer Notes

**Test file:** `tests/test_sync_global_tools_860.py`

**Classes and counts:**

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_DoImportSourceScope` | happy/edge/boundary | 7 |
| `TestFromAC_SyncToolRegistration` | happy | 6 |
| `TestFromAC_SyncToolAnnotations` | happy | 4 |
| `TestFromAC_SyncFromGlobal` | happy/error/edge | 6 |
| `TestFromAC_SyncToGlobal` | happy/error/edge | 6 |

**Total: 29 tests — all FAIL (confirmed via pytest run)**

**Failure modes:**
- `TestFromAC_DoImportSourceScope`: `TypeError: _do_import() got an unexpected keyword argument 'source_scope'` or assertion on missing parameter
- `TestFromAC_SyncToolRegistration`: `hasattr` returns False; `ImportError` on direct import
- `TestFromAC_SyncToolAnnotations`: tool not in `_tool_manager`, `ann is None` assertion fails
- `TestFromAC_SyncFromGlobal` / `TestFromAC_SyncToGlobal`: `ImportError: cannot import name 'sync_from_global'/'sync_to_global'`

**AC coverage:**

| AC item | Tests |
|---------|-------|
| `_do_import` source_scope kwarg (arch-review refinement) | 6 — signature, default None, no-filter backward-compat, filters by scope, zero-match, child-row exclusion |
| `sync_from_global` registered + zero user params | 3 |
| `sync_to_global` registered + zero user params | 3 |
| ToolAnnotations readOnlyHint=False, destructiveHint=False | 4 (2 per tool) |
| `sync_from_global` error: path unresolvable | 1 |
| `sync_from_global` error: global DB not found | 1 |
| `sync_from_global` happy path return format | 2 |
| `sync_from_global` content-hash dedup | 1 |
| `sync_from_global` imported docs land under scope='global' | 1 |
| `sync_to_global` error: path unresolvable | 1 |
| `sync_to_global` creates global DB if not exists | 1 |
| `sync_to_global` scope filter (only global docs) | 1 |
| `sync_to_global` return format (Exported ... to global DB) | 2 |
| `sync_to_global` content-hash dedup | 1 |

**Patch targets for builder:** `owlbear_mcp_knowledge.server.resolve_global_db_path` — builder must import this at module level from `owlbear_knowledge.scope_transfer` (added by #858) for the patches in behavior tests to work.