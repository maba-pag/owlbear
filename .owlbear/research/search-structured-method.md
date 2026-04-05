# Add search_structured Method to KnowledgeQueryService

> **Owning task:** #70 — Add search_structured method to KnowledgeQueryService
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #70 adds a public `search_structured(query, top_k)` method to `KnowledgeQueryService` returning typed result objects with `doc_id`, `title`, `score`, and `entity_type`. Driven by #54 research: `query_for_context()` returns pre-formatted text, losing structured data (scores, entity types) needed by MCP consumers.

## 2. Sources

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear v1 query_service.py | `v1/src/owlbear/memory/knowledge/query_service.py` | .95 |
| 2 | OwlBear v1 retrieval.py (RetrievalResult) | `v1/src/owlbear/memory/knowledge/retrieval.py` | .90 |
| 3 | OwlBear v1 models.py (Document, Entity) | `v1/src/owlbear/memory/knowledge/models.py` | .95 |
| 4 | LlamaIndex NodeWithScore schema | <https://developers.llamaindex.ai/python/framework-api-reference/schema/> | .85 |
| 5 | Qdrant MCP Server find tool | <https://github.com/qdrant/mcp-server-qdrant> | .80 |
| 6 | OwlBear v1 protocol.py (VectorStoreProtocol) | `v1/src/owlbear/memory/knowledge/protocol.py` | .90 |

## 3. Analysis

### 3.1 Current Internal Pipeline

`query_for_context()` calls `_search_chunks()` → `_format_docs()`. The structured data exists mid-pipeline but is discarded during formatting:

| Step | Method | Input | Output | Data preserved |
|------|--------|-------|--------|----------------|
| 1 | `_search_chunks()` | query string | `list[tuple[str, float]]` | doc_id, score |
| 2 | threshold filter | scored pairs | filtered pairs | doc_id, score |
| 3 | `_format_docs()` | pairs | formatted string | **title, snippet only — score lost** |

`search_structured()` needs steps 1–2 but replaces step 3 with structured resolution.

### 3.2 Entity Type Resolution

The AC asks for `entity_type` per result. Entities link to documents via `Entity.document_id` (Src 3). Challenge: a document may have 0, 1, or many linked entities.

| Approach | Complexity | KISS | Coverage |
|----------|------------|------|----------|
| A: Skip entity_type entirely | Low | High | Violates AC |
| B: `list_entities()` + dict lookup | Medium | Medium | Full — O(n) over all entities |
| C: New `GraphStore.get_entities_by_doc_id()` | Medium | Medium | Full — O(1) lookup |

**Approach B** is simplest without modifying GraphStore. `list_entities(scopes=...)` is already called in `retrieval.py` (Src 2, line 176). For small knowledge bases (laptop-resident), the O(n) scan is acceptable. If perf becomes an issue, add a SQL index and dedicated method later (YAGNI).

For multiple entities per document, take the first match. The `entity_type` field should be `str | None` — None when no entity is linked.

### 3.3 Result Type Design

Prior art comparison for structured search results:

| Library | Result type | Fields | Score handling |
|---------|-------------|--------|----------------|
| LlamaIndex (Src 4) | `NodeWithScore` | node (BaseNode) + score (float) | Separate from data |
| Qdrant MCP (Src 5) | `list[str]` | XML-tagged entries | Implicit (sorted) |
| OwlBear retrieval.py (Src 2) | `RetrievalResult` | chunks, expansion_text, entities_found | Score in tuple |

**Recommendation (.85):** Flat frozen Pydantic BaseModel. Matches project conventions (Src 2, Src 3 use `BaseModel` + `ConfigDict(frozen=True)`):

```python
class StructuredSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    doc_id: str
    title: str
    score: float
    snippet: str
    entity_type: str | None
    scope: str
```

### 3.4 Error Handling Pattern

`query_for_context()` catches all exceptions and returns None (Src 1, L96). For a structured API, two options:

| Pattern | Return on error | KISS | Composable |
|---------|-----------------|------|------------|
| Return `None` (like query_for_context) | None | High | Low — caller must handle None |
| Return empty list | `[]` | High | High — uniform iterable |

**Recommendation (.80):** Return empty list on error. An empty list is the natural "no results" value for a list-returning method and avoids `None` checks at every call site. Log warning same as `query_for_context()`.

### 3.5 Method Signature

```python
def search_structured(self, query: str, *, top_k: int = 5) -> list[StructuredSearchResult]:
```

No `max_tokens` parameter — structured results don't have a token budget (that's the caller's concern). The `top_k` default matches `query_for_context()`.

## 4. Recommendation (.85 confidence)

1. **New frozen Pydantic model** `StructuredSearchResult` in `query_service.py` — keeps the result type co-located with the method
2. **Reuse `_search_chunks()`** — same embed + search pipeline, no duplication
3. **Entity type via `list_entities()` dict lookup** — O(n) but KISS, no GraphStore changes
4. **Return `list[StructuredSearchResult]`** — empty list on error or no results
5. **Snippet from `doc.content[:500]`** — same truncation as `_format_docs()`

Risk: entity_type resolution adds a `list_entities()` call per search. For laptop-scale knowledge bases (~1K entities) this is <10ms. Document if the caller wants to skip entity resolution in the future, the method could accept `include_entity_type=True`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Test: Add search_structured method to KnowledgeQueryService" --priority important --status ideation --tags "phase-2,scope:knowledge,test" --body "## Objective\nWrite failing tests (TDD RED) for search_structured() before the builder implements #70.\n\n## Acceptance Criteria\n- [ ] tests/test_knowledge_query_service.py extended or new file\n- [ ] Test: search_structured returns list[StructuredSearchResult] with doc_id, title, score, snippet, entity_type, scope\n- [ ] Test: search_structured returns empty list when no results\n- [ ] Test: search_structured returns empty list when all below threshold\n- [ ] Test: search_structured resolves entity_type from linked entities (None when no entity linked)\n- [ ] Test: search_structured catches exceptions and returns empty list with WARNING log\n- [ ] Test: search_structured respects top_k parameter\n- [ ] Test: search_structured does not break existing query_for_context() tests\n- [ ] All tests FAIL at this point (RED phase)\n\n## Context\nPreceding test task for #70. See docs/research/search-structured-method.md."
```
