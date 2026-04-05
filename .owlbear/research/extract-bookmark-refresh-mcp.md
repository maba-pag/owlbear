# Extract BookmarkPipeline, RefreshOrchestrator, and Bookmark MCP Tools

> **Owning task:** #136 — Extract bookmark pipeline, refresh orchestrator, and bookmark MCP tools
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #136 (Group B from #130 split) extracts three components into v2:
(a) BookmarkPipeline — multi-stage URL→evaluate→ingest→store orchestrator (265 LOC),
(b) RefreshOrchestrator — source-type dispatcher for knowledge refresh (331 LOC),
(c) Bookmark MCP tools — two thin wrappers replacing v1's PydanticAI `BookmarkToolset`.

Key questions: what v2 gaps remain before extraction, what changes from v1→v2,
and how to register MCP tools in the existing mcp-knowledge server.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 bookmark_pipeline.py | Local `v1/src/owlbear/memory/knowledge/bookmark_pipeline.py` (265 LOC) | 1.0 |
| 2 | v1 refresh.py | Local `v1/src/owlbear/memory/knowledge/refresh.py` (331 LOC) | 1.0 |
| 3 | v1 bookmark_toolset.py | Local `v1/src/owlbear/memory/knowledge/bookmark_toolset.py` (143 LOC) | 1.0 |
| 4 | v2 mcp-knowledge tools.py | Local `packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py` | .95 |
| 5 | v2 KnowledgeSourceStore | Local `packages/knowledge/src/owlbear_knowledge/source_store.py` | .95 |
| 6 | FastMCP Tools docs | `gofastmcp.com/servers/tools` | .85 |
| 7 | Parent research | `docs/research/extract-knowledge-secondary-features.md` | .90 |
| 8 | Cooperative cancellation | `docs/research/cooperative-cancellation.md` | .85 |

## 3. Analysis

### 3.1 Dependency Readiness

| Dependency | Task | Status | Provides | Blocks |
|------------|------|--------|----------|--------|
| IngestPipeline + IngestResult | #33 | ideation | Pipeline interface for ingest/ingest_text | BookmarkPipeline, RefreshOrchestrator |
| CancelSignal + LinkedCancelSignal | #135 | ideation | Cooperative cancellation protocol | Both modules |
| sandbox_path | #135 | ideation | Path-traversal guard | RefreshOrchestrator `_handle_file_glob` |
| SourceEvaluator + EvaluationResult | #135 | ideation | LLM relevance evaluator | BookmarkPipeline |
| BookmarkStore | v2 ✓ | done | CRUD for bookmarks table | BookmarkPipeline, MCP tools |
| KnowledgeSourceStore | v2 ✓ | done | CRUD for sources table | RefreshOrchestrator |

**Critical:** Both #33 and #135 are at `ideation`. #136 cannot start building until both land.

### 3.2 v2 Gaps to Fill Before or During Extraction

| Gap | Details | Recommendation |
|-----|---------|----------------|
| `list_enabled` missing from v2 `KnowledgeSourceStore` | v1 has `list_enabled(scope)` filtering `enabled=1 ORDER BY priority DESC`; v2 only has `list_all` | Add `list_enabled` to `KnowledgeSourceStore` as part of #136 (~15 LOC) |
| `_default_web_read` depends on `owlbear.web_extract` and `owlbear.core.retry` | Neither exists in v2 | Make `web_read_fn` required (no default). KISS — callers inject their own HTTP reader. The default was a convenience, not domain logic |
| `_supports_cancel_kwarg` duplicated | Identical static method in both BookmarkPipeline and RefreshOrchestrator | Extract to `cancellation.py` as `supports_cancel_kwarg()` utility (under #135) |
| `AppContext` in mcp-knowledge needs extension | Currently only holds `query_service` | Add `bookmark_pipeline` and `bookmark_store` fields |
| IngestPipeline has no v2 Protocol | Both modules import concrete v1 class | Define `IngestPipelineProtocol` in knowledge package (under #33 scope) |

### 3.3 BookmarkPipeline v1→v2 Changes

| Aspect | v1 | v2 recommendation |
|--------|----|--------------------|
| SourceEvaluator | PydanticAI Agent | Async callable injection (from #135) |
| `_default_web_read` | httpx + trafilatura + TRANSIENT_RETRY | Drop default; `web_read_fn` becomes required constructor arg |
| CancelSignal | v1 cancellation module | v2 cancellation module (from #135) |
| IngestPipeline | v1 concrete class | Protocol from #33 |
| BookmarkStore/Bookmark | v1 models | v2 models (already extracted) |
| EvaluationResult import | v1 evaluator | v2 evaluator (from #135) |

The pipeline logic itself (dedup→extract→evaluate→ingest→store with cancel checks) is **unchanged**.

### 3.4 RefreshOrchestrator v1→v2 Changes

| Aspect | v1 | v2 recommendation |
|--------|----|--------------------|
| sandbox_path | `owlbear.paths` | `owlbear_knowledge._paths` (from #135) |
| IngestPipeline | v1 concrete class | Protocol from #33 |
| KnowledgeSourceStore | v1 store | v2 store (already extracted, but needs `list_enabled`) |
| CancelSignal | v1 cancellation | v2 cancellation (from #135) |
| `_update_source_record` | Uses v1 store.update() | v2 store.update() already exists |

The dispatch logic (url_list/crawl/file_glob handlers) is **unchanged**.

### 3.5 MCP Tool Design

v1's `BookmarkToolset` wraps 2 functions with zero domain logic. The MCP equivalent:

| Tool | Params | Returns | readOnlyHint |
|------|--------|---------|-------------|
| `bookmark_source` | `url: str, reason: str \| None` | Formatted summary string | False |
| `list_bookmarks` | `tag: str \| None, min_score: float \| None` | Formatted bookmark list | True |

Registration pattern: `@mcp.tool` decorator on async functions in `tools.py`,
following the existing `search_knowledge` pattern. `AppContext` gains
`bookmark_pipeline: BookmarkPipeline \| None` and `bookmark_store: BookmarkStore \| None`.

### 3.6 Testing Strategy

| Module | Test approach | Mocks |
|--------|--------------|-------|
| BookmarkPipeline | In-memory SQLite BookmarkStore, AsyncMock evaluator, AsyncMock ingest | web_read_fn, SourceEvaluator.evaluate, IngestPipeline.ingest_text |
| RefreshOrchestrator | In-memory SQLite SourceStore, AsyncMock pipeline | IngestPipeline.ingest, crawl_handler |
| MCP bookmark tools | Mock AppContext with mock pipeline/store | BookmarkPipeline.process, BookmarkStore.list |

All existing v1 test patterns can be reused with import path changes.

## 4. Recommendation (.85 confidence)

Proceed with extraction once #33 and #135 land. Key decisions:

1. **Drop `_default_web_read`** — make `web_read_fn` required. Avoids pulling in httpx/trafilatura/retry deps.
2. **Add `list_enabled` to v2 `KnowledgeSourceStore`** — ~15 LOC, same SQL as v1.
3. **Extract `_supports_cancel_kwarg` to cancellation module** — deduplicate across both modules (update #135 AC).
4. **Extend `AppContext`** in mcp-knowledge for bookmark pipeline/store references.
5. **Register MCP tools** with `@mcp.tool` decorator, `readOnlyHint` for list_bookmarks.

**Risks:**
- #33 timeline unknown (still at ideation) — blocks all of #136.
- `web_read_fn` becoming required means the caller must provide HTTP reading — but this is correct for a library package.

## 5. Follow-up Tasks

Updates to existing tasks (not new creates):
- **#135 AC update:** Add `_supports_cancel_kwarg` utility to cancellation module scope.
- **#136 AC update:** Add `list_enabled` method to KnowledgeSourceStore; make `web_read_fn` required.
