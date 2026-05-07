# P4-19: Tool Surface Cleanup + Scope Stubs — Pre-Complete

> **Owning task:** #1335 — P4-19: Tool surface cleanup + scope stubs
> **Date:** 2026-05-07 **Status:** Complete

## 1. Context and Question

Task #1335 requires reducing the mcp-knowledge tool surface to 8 active MCP tools, removing 5 deprecated tools from registration, adding 4 scope stubs as internal callables (not exposed via MCP), and ensuring all #1334 tests pass.

**Key question:** What implementation work remains?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (current) | Codebase | 1.0 |
| `tests/test_mcp_knowledge_tool_surface_1334.py` | Codebase | 1.0 |
| Git commit `430ccbdd` ("feat: reduce mcp-knowledge tool surface to 8 active tools (#1334, builder)") | VCS | 1.0 |
| `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.9 | Brief | 0.9 |

## 3. Analysis

### Current State vs. ACs

| AC | Requirement | Current State | Status |
|----|-------------|---------------|--------|
| AC1 | Only 8 active tools registered | 8 tools: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment | ✅ GREEN |
| AC2 | Removed: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge | All 5 exist as plain functions without `@mcp.tool()` | ✅ GREEN |
| AC3 | 4 scope stubs registered internally | import_scope, export_scope, sync_from_global, sync_to_global exist as callable functions | ✅ GREEN |
| AC4 | Scope stubs not exposed to agents | None of the 4 appear in `mcp._tool_manager.list_tools()` | ✅ GREEN |
| AC5 | All #1334 tests pass | 4/4 pass (`uv run pytest tests/test_mcp_knowledge_tool_surface_1334.py`) | ✅ GREEN |

### Root Cause: Pre-Completion

Commit `430ccbdd` (attributed to "#1334, builder") implemented the full tool surface reduction. The builder who implemented #1334's tests also made the server changes GREEN in the same pass. This means #1335's implementation work was already delivered.

## 4. Recommendation

**No implementation work required.** All 5 ACs are satisfied by the current codebase. Confidence: **0.95**.

The 0.05 gap: "registered internally" (AC3) could theoretically mean an explicit internal registry beyond "function exists in module." However, the #1334 tests define the contract as `callable(fn) AND fn_name not in tool_names`, and those tests pass — so the AC is satisfied per its verification criteria.

Challenge: SKIP — trivial pre-complete finding, no recommendation to challenge.

## 5. Follow-up Tasks

None required. Task can advance directly through the pipeline (backlog → done) with a note that implementation was delivered in `430ccbdd` under #1334.
