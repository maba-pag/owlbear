# Wire LLMExtractor into MCP Knowledge Server app_lifespan

> **Owning task:** #690 — Wire LLMExtractor into MCP knowledge server app_lifespan
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

`app_lifespan()` in `server.py` creates `EntityExtractor(model)` — passing a model
string but no `StructuredExtractor` via `extractor=`. This makes entity extraction a
no-op. Once #689 (LLMExtractor) completes, this task wires it in.

**Question:** What changes are needed to activate LLM-backed entity extraction in the
MCP server, satisfy graceful degradation, and deliver graph expansion in search results?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L148-188 | Codebase | 1.0 |
| 2 | `serve/knowledge/src/owlbear_knowledge/extractor.py` L64-100 | Codebase | 1.0 |
| 3 | `serve/knowledge/src/owlbear_knowledge/protocol.py` L87-98 | Codebase | 0.9 |
| 4 | `serve/knowledge/src/owlbear_knowledge/retrieval.py` L36-115 | Codebase | 0.9 |
| 5 | `serve/knowledge/src/owlbear_knowledge/query_service.py` L33-84 | Codebase | 0.9 |
| 6 | `v1/src/owlbear/memory/knowledge/extractor.py` — PydanticAI v1 pattern | Codebase | 0.8 |
| 7 | `.owlbear/research/wire-structuredextractor-knowledge-graph.md` | Research | 0.8 |

## 3. Analysis

### 3.1 Wiring Pattern (AC1)

Current (`server.py:162`):
```python
extractor = EntityExtractor(model)
```
Required:
```python
llm_extractor = LLMExtractor(model)
extractor = EntityExtractor(extractor=llm_extractor)
```

`EntityExtractor.__init__` already accepts `extractor: StructuredExtractor | None`.
When `extractor=None`, it returns empty `ExtractionResult()` (existing no-op).
One-line logical change; DI slot is pre-built.

### 3.2 Dependency Declaration (AC2)

| File | Current | Required |
|------|---------|----------|
| `serve/mcp-knowledge/pyproject.toml` | `"owlbear-knowledge"` | `"owlbear-knowledge[llm]"` |
| `serve/knowledge/pyproject.toml` | No `llm` extras group | `[project.optional-dependencies] llm = ["pydantic-ai>=0.1"]` |

The `llm` extras group is created by #689. This task only updates the MCP server dep.

### 3.3 Graph Expansion in Search (AC4) — Scope Ambiguity

| Approach | Change | Graph context | LOC | Risk |
|----------|--------|--------------|-----|------|
| **A: Wire GraphAugmentedRetriever** | Create `GraphAugmentedRetriever` in `app_lifespan`, pass as `retriever=` to `KnowledgeQueryService` | Vector pre-filtering + entity resolution | ~5 | Low — retriever is already implemented |
| **B: Include entity_type in SearchResult** | Add `entity_type` to `SearchResult` TypedDict and response dict | Entity type from graph | ~3 | Low — field already in StructuredSearchResult |
| **C: Full expansion text in response** | Modify `search_knowledge` to call `query_for_context()` or expose `expansion_text` | Full neighbor expansion text | ~15 | Medium — changes tool response shape |

**Finding:** `KnowledgeQueryService._search_chunks()` delegates to `GraphAugmentedRetriever`
when `retriever=` is set, but drops `expansion_text` from `RetrievalResult`. The `query()`
method resolves entity types via `list_entities_for_document()` but `search_knowledge`
drops `entity_type` from `StructuredSearchResult`.

**Recommendation:** Apply A + B. Wire `GraphAugmentedRetriever` so search benefits from
graph structure, and include `entity_type` in the tool response. This satisfies AC4 without
changing the tool's response shape contract. Option C is a separate enhancement.

### 3.4 Graceful Degradation (AC5)

| Failure mode | Mitigation |
|-------------|------------|
| `pydantic-ai` not installed | `try: from ... import LLMExtractor` / `except ImportError` → `extractor=None` |
| `LLMExtractor(model)` construction fails | Catch in same try block → fall back to no extractor |
| LLM call fails at runtime | Handled by `LLMExtractor` itself (#689 AC5) — returns empty `ExtractionResult()` |
| `OWLBEAR_MODEL` unset | `_DEFAULT_MODEL` fallback already provides `"gpt-4o-mini"` |

Pattern — lazy import with try/except:
```python
try:
    from owlbear_knowledge.llm_extractor import LLMExtractor

    llm_extractor = LLMExtractor(model)
except Exception:
    logger.info("LLMExtractor unavailable — vector-only mode")
    llm_extractor = None
extractor = EntityExtractor(extractor=llm_extractor)
```

### 3.5 Metadata Defects (inherited from #676 review)

This task has incorrect metadata that the orchestrator must fix before dispatching:
- `depends_on`: currently `[676]`, should be `[699, 689]`
- `parent`: currently `null`, should be `676`
- `tags`: `scope:knowledge` should be `scope:mcp-knowledge`

## 4. Recommendation

**Wire LLMExtractor + GraphAugmentedRetriever in `app_lifespan()`** (confidence: 0.85)

Implementation is ~15 lines of production code across 2 files:
1. `server.py`: import LLMExtractor (with try/except), create instance, wire into
   EntityExtractor, wire GraphAugmentedRetriever into KnowledgeQueryService, add
   entity_type to SearchResult response
2. `pyproject.toml`: change dep to `owlbear-knowledge[llm]`

Challenge: FALLBACK — challenger agent not available.

Risks:
- **Upstream dependency**: #689 (LLMExtractor) must complete first — still in research
- **AC4 scope**: if "graph expansion context" means full expansion text in response,
  a follow-up task is needed for Option C
- **Import weight**: `pydantic-ai` transitive deps loaded at server startup — mitigated
  by optional extras pattern

## 5. Follow-up Tasks

No new follow-up tasks needed — the decomposition from #676 already covers all work:
- #699 (TDD RED for this task) — exists at backlog
- #690 (this task) — advances to backlog after research
- AC4 Option C (expansion text in response) is out-of-scope enhancement if needed later
