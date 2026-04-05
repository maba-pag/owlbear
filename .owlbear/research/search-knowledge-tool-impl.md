# Implement Real search_knowledge Tool

> **Owning task:** #54 — Implement real search_knowledge tool in mcp-knowledge
> **Date:** 2026-03-26 **Updated:** 2026-03-30 **Status:** Superseded

## 1. Context and Question

Task #54 asks to replace the placeholder `search_knowledge` tool (from #40) with a real implementation using `KnowledgeQueryService`. This research validates the API surface, identifies a critical AC mismatch, analyzes sync/async integration, and recommends an implementation approach.

## 2. Sources

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK v1 README | <https://github.com/modelcontextprotocol/python-sdk> | .95 |
| 2 | Qdrant MCP Server (v0.8.1) | <https://github.com/qdrant/mcp-server-qdrant> | .90 |
| 3 | OwlBear v1 KnowledgeQueryService | `v1/src/owlbear/memory/knowledge/query_service.py` | .95 |
| 4 | OwlBear v1 QdrantVectorStore | `v1/src/owlbear/memory/knowledge/qdrant.py` | .90 |
| 5 | OwlBear scaffold research | `docs/research/scaffold-mcp-knowledge.md` | .85 |

## 3. Analysis

### 3.1 AC Mismatch — No `search()` Method

AC1 says "calls `KnowledgeQueryService.search()`" — **this method does not exist.** The actual public API is:

```python
def query_for_context(self, prompt: str, *, max_tokens: int = 2000, top_k: int = 5) -> str | None
```

This returns pre-formatted text ("Relevant knowledge:\n\n- title: snippet") or None. It catches all exceptions internally (Src 3, line 96). The AC must be corrected to reference `query_for_context()`.

### 3.2 Sync/Async Boundary

**All v1 knowledge engine components are synchronous** (Src 3, Src 4):

| Component | Sync/Async | Notes |
|-----------|------------|-------|
| `KnowledgeQueryService.query_for_context()` | Sync | Catches exceptions, returns `str\|None` |
| `QdrantVectorStore.search_similar()` | Sync | Uses sync `QdrantClient` |
| `BgeM3EmbeddingProvider.embed()` | Sync | Lazy 3 GB model load |
| `GraphStore.get_document()` | Sync | sqlite3 local file I/O |

MCP tools run in an async context (Src 1). Two options:

| Approach | Pros | Cons |
|----------|------|------|
| Direct call (no wrapping) | Simplest, KISS | Blocks event loop during search |
| `asyncio.to_thread()` | Non-blocking | One extra line |

**Recommendation (.85):** Use `asyncio.to_thread()`. The BGE-M3 embedding step can take 100+ ms on first call and the model load takes seconds. Qdrant MCP server (Src 2) uses fully async operations for the same reason. Cost: one wrapper line per call.

### 3.3 Result Format Options

| Approach | Structured? | Scores? | Entity types? | KISS? |
|----------|-------------|---------|---------------|-------|
| A: Use `query_for_context()` as-is | No | No | No | High |
| B: New `search_structured()` on service | Yes | Yes | Yes | Medium |
| C: Call internal `_search_chunks()` + format | Yes | Yes | Partial | Low |

AC2 wants "entity names, types, and relevance scores." `query_for_context()` (Option A) only returns document titles + snippets — no scores, no entity types. But it's the simplest approach.

**Qdrant MCP pattern** (Src 2): `format_entry()` wraps each result in XML tags: `<entry><content>...</content><metadata>...</metadata></entry>`. Returns `list[str]` — one string per result. The LLM receives individual entries as separate content blocks.

**Recommendation (.80):** Option A for v1, with AC refinement. `query_for_context()` already handles embedding, searching, scoring, filtering, and budget-capping. The output is LLM-friendly. The AC should be relaxed: "Results formatted as text with document titles and relevant snippets" instead of requiring entity types/scores. If richer structure is needed later, a `search_structured()` method can be added as a separate task.

### 3.4 Error Handling

`query_for_context()` already wraps all exceptions internally and returns `None` (Src 3, line 95). The tool needs only:

1. Check for `None` return → "No relevant knowledge found for your query."
2. Check for empty `AppContext.query_service` (service not initialized) → "Knowledge service not available."

No additional try/except needed in the tool layer — the service handles it.

### 3.5 BGE-M3 Memory Footprint

The embedding model loads ~3 GB RAM on first query (Src 3, `BgeM3EmbeddingProvider`). This is lazy (not during lifespan). First search will be slow (model load + encode). The idle timeout (default 600s) can unload the model to reclaim memory. Important for the MCP server's resource profile but not a blocker.

### 3.6 Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Tool function | Mock `AppContext.query_service`, verify formatting |
| Unit | Empty results | Mock returns `None`, verify friendly message |
| Unit | Missing service | `AppContext(query_service=None)`, verify error message |
| Integration | Real SQLite + mock vectors | `init_db()` + `GraphStore` + mock `QdrantVectorStore.search_similar()` |

No need to load real BGE-M3 in tests — mock `EmbeddingProvider.embed()`. The Qdrant MCP server (Src 2) tests tool functions directly with mocked connectors.

## 4. Recommendation (.80 confidence)

1. **Use `query_for_context()`** — don't reinvent the search pipeline
2. **Wrap in `asyncio.to_thread()`** — non-blocking for BGE-M3 latency
3. **Refine AC** — replace "entity names, types, and relevance scores" with "document titles and relevant snippets" to match actual API
4. **Tool returns `str`** — pre-formatted context or a "no results" message
5. **Test with mocked service** — no real BGE-M3 or Qdrant needed

**Risk:** AC2 as written cannot be satisfied by `query_for_context()`. The architect should refine AC2 or approve adding a new method to KnowledgeQueryService (which would expand scope beyond #54).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add search_structured method to KnowledgeQueryService" --priority important --status ideation --tags "phase-2,scope:knowledge" --body "## Objective\nAdd a public method returning raw structured results (entity names, types, relevance scores) for MCP and other consumers that need richer output than query_for_context().\n\n## Acceptance Criteria\n- [ ] New search_structured(query, top_k) returns list of typed result objects with doc_id, title, score, entity_type\n- [ ] Does not break existing query_for_context() contract\n- [ ] Unit tests with mock vector store\n\n## Context\nDriven by #54 research finding: query_for_context() returns pre-formatted text without scores or entity types. See docs/research/search-knowledge-tool-impl.md."
```

## 6. Supersession Notice (2026-03-30)

The work described in this document was completed through three successor tasks:

| Task | What it delivered | Status |
|------|------------------|--------|
| #72 | `tools.py` — original `asyncio.to_thread(query_for_context)` implementation + 12 tests | Archived |
| #70 | `KnowledgeQueryService.query()` async method + `StructuredSearchResult` model | Archived |
| #152 | `server.py` v2 — `search_knowledge` rewritten to `await qs.query()` with structured output | Archived |

**Current state:** `server.py` uses `await qs.query()` returning `list[StructuredSearchResult]`, formatted as bullet lines (`- {title} ({score:.2f}): {snippet[:200]}`). This supersedes the original recommendation to use `query_for_context()` via `asyncio.to_thread()`.

**Dead code cleaned up:** `tools.py` and `test_search_knowledge.py` were deleted in #223 (chore: clean up dead tools.py and test_search_knowledge.py).

**Async purity note:** `KnowledgeQueryService.query()` is `async def` but calls sync internals (`embed()`, `search_similar()`, `get_document()`). Acceptable for single-user stdio MCP; noted for future consideration if concurrent requests become relevant.
