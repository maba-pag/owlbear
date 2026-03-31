# Dead Code: mcp-knowledge tools.py

> **Owning task:** #223 — Clean up dead tools.py and test_search_knowledge.py in mcp-knowledge
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #223 proposes deleting `packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py` and its test file `test_search_knowledge.py`. Both were built for task #72 using `asyncio.to_thread(query_for_context)`. Task #152 rewrote `search_knowledge` in `server.py` using `await qs.query()` with `StructuredSearchResult` output. Are these files truly dead, and are there any downstream dependencies?

## 2. Sources

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | server.py v2 search_knowledge | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:81` | .95 |
| 2 | Supersession notice | `docs/research/search-knowledge-tool-impl.md` §6 | .95 |
| 3 | tools.py (dead module) | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py` | .90 |
| 4 | test_search_knowledge.py (dead tests) | `packages/mcp-knowledge/tests/test_search_knowledge.py` | .90 |
| 5 | Task #136 AC (references tools.py) | kanban task #136, AC line 4 | .85 |

## 3. Analysis

### 3.1 Supersession evidence

| Criterion | tools.py (#72) | server.py (#152) |
|-----------|---------------|-------------------|
| Registered on FastMCP | No | Yes (`@mcp.tool()`) |
| API pattern | `asyncio.to_thread(query_for_context)` | `await qs.query()` |
| Output format | Raw string from `query_for_context` | Structured `StructuredSearchResult` bullets |
| Test file | `test_search_knowledge.py` (11 tests, imports `tools`) | `test_search_v2.py` + `test_server.py` |
| Status | Dead — no callers | Active — production tool |

### 3.2 Import scan (codebase-wide)

All 20 references to `owlbear_mcp_knowledge.tools` are in:
- `tools.py` itself and `test_search_knowledge.py` (the two files being deleted)
- Kanban task markdown files (#72, #136, #223) — metadata only
- `docs/research/extract-bookmark-refresh-mcp.md` — historical research reference

**No source code outside the deletion targets imports `owlbear_mcp_knowledge.tools`.**

### 3.3 Downstream dependency: task #136

Task #136 ("Extract bookmark pipeline...") is in `todo` and has AC line: *"bookmark_source and list_bookmarks registered as MCP tools in packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py"*. This references the file being deleted. The AC should be updated to register bookmark tools in `server.py` following the v2 pattern (direct `@mcp.tool()` decorators on `server.py`).

**Risk:** Low. #136 depends on #33 and #135 (both unresolved), so it won't execute soon. The architect gate will catch the stale AC reference.

### 3.4 Package __init__.py

`__init__.py` has no re-exports from `tools`. Clean deletion — no export cleanup needed.

## 4. Recommendation (.95 confidence)

Delete both files. The task AC is correct and complete:
1. Delete `tools.py` — standalone module with no callers, not registered on FastMCP
2. Delete `test_search_knowledge.py` — tests the deleted module exclusively
3. Verify no imports remain (confirmed: none outside the two files)
4. Run remaining mcp-knowledge tests to confirm no breakage

**Additional action:** Update task #136 AC to reference `server.py` instead of `tools.py` for bookmark tool registration.

## 5. Follow-up Tasks

Task #223 itself covers the deletion. One ancillary task needed for #136 AC correction.
