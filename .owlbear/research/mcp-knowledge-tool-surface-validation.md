# MCP Knowledge Tool Surface Validation

> **Owning task:** #1334 — P4-18: Tests — Tool surface validation
> **Date:** 2026-05-07 **Status:** Complete

## 1. Context and Question

Task #1334 requires TDD RED tests that validate the MCP knowledge server exposes exactly 8 active tools, excludes 5 removed tools, and keeps 4 scope stubs as internal functions not exposed to agents. These tests will fail against the current 16-tool server and pass after #1335 implements the cleanup.

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| server.py | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Current tool registrations (16 total) | 1.0 |
| test_tool_annotations_501.py | `serve/mcp-knowledge/tests/test_tool_annotations_501.py` | Pattern: `mcp._tool_manager.list_tools()` | 0.9 |
| Brief §4.9 | `.owlbear/briefs/draft-knowledge-activation/brief.md` | Target 8 active + 4 stubs | 1.0 |
| Decision D11 | `.owlbear/briefs/draft-knowledge-activation/decisions.md` | Tool surface rationale | 0.8 |
| Decision D12/D16 | Same file | Scope stubs deferred | 0.8 |

## 3. Analysis

### Current vs. Target Tool Surface

| Tool | Current Status | Target Status |
|------|---------------|---------------|
| `search_knowledge` | @mcp.tool | Active (keep) |
| `list_sources` | @mcp.tool | Active (keep) |
| `get_stats` | @mcp.tool | Active (keep) |
| `ingest_document` | @mcp.tool | Active (keep) |
| `refresh_source` | @mcp.tool | Active (keep) |
| `get_next_batch` | post-def registered | Active (keep) |
| `get_consolidation_candidates` | **bare function** | Active (**must register**) |
| `store_enrichment` | post-def registered | Active (keep) |
| `list_entities` | @mcp.tool | **Remove** |
| `bookmark_source` | @mcp.tool | **Remove** |
| `list_bookmarks` | @mcp.tool | **Remove** |
| `update_bookmark_tags` | @mcp.tool | **Remove** |
| `consolidate_knowledge` | @mcp.tool | **Remove** |
| `import_scope` | @mcp.tool | **Remove decorator, keep function** |
| `export_scope` | @mcp.tool | **Remove decorator, keep function** |
| `sync_from_global` | @mcp.tool | **Remove decorator, keep function** |
| `sync_to_global` | @mcp.tool | **Remove decorator, keep function** |

### Test Implementation Approach

**Mechanism:** `mcp._tool_manager.list_tools()` returns tool objects with `.name` attribute. Established pattern in `test_tool_annotations_501.py`.

**5 test cases:**

1. **Tool count** — `len(tool_names) == 8`
2. **Active tools present** — all 8 expected names in set
3. **Removed tools absent** — 5 removed names not in set
4. **Scope stubs exist** — `hasattr(server_module, name)` and `callable()` for 4 scope functions
5. **Scope stubs not exposed** — 4 scope names not in tool set

### Risk: `get_consolidation_candidates` Not Yet Registered

Currently a bare async function (line 266). Task #1335 must register it via post-definition pattern like `get_next_batch`. The test will correctly fail until this is done.

## 4. Recommendation

Confidence: 0.95 — Straightforward TDD RED. Well-established test patterns exist. No architectural decisions needed.

Challenge: SKIPPED — trivial test task, no recommendation with alternatives to challenge.

## 5. Follow-up Tasks

No new tasks needed. #1334 proceeds directly to test-writer (TDD RED) → #1335 implements cleanup (TDD GREEN).
