# Knowledge Toolset — Expose query/ingest tools to agents

> **Owning task:** #291 — Knowledge toolset — expose query/ingest tools to agents
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

The knowledge pipeline (`graph.py`, `qdrant.py`, `ingest.py`, `embeddings.py`) is fully
built and tested, but agents have no tool to interact with it. Task #291 proposes a
`KnowledgeToolset(FunctionToolset)` exposing `query_knowledge`, `ingest_document`, and
`list_knowledge_sources`. This research validates the approach, surveys prior art, and
defines the implementation path.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI RAG example | <https://ai.pydantic.dev/examples/rag/> | .90 | Official RAG pattern: `@agent.tool` → embed query → vector search → format results |
| PydanticAI FunctionToolset docs | <https://ai.pydantic.dev/toolsets/> | .95 | `FunctionToolset` subclass API, `add_function()` registration, toolset composition |
| OwlBear TerminalToolset | `src/owlbear/tools/terminal.py` | .95 | Canonical `__init__→_register_tools→add_function` pattern with async wrappers |
| OwlBear FileToolset | `src/owlbear/tools/filesystem.py` | .90 | `_safe_path()` sandboxing pattern, sync tools (PydanticAI wraps in executor) |
| OwlBear BrowserToolset | `src/owlbear/tools/browser/toolset.py` | .85 | Lifecycle (`setup`/`teardown`) for heavy resources |
| OwlBear bootstrap.py `build_toolsets()` | `src/owlbear/bootstrap.py:171-230` | .95 | Registration pattern: append to `raw`, wrap in `HookedToolset` |
| OwlBear IngestPipeline | `src/owlbear/memory/knowledge/ingest.py` | .95 | Async `ingest()`, `ingest_text()`, delta checking, scope param |
| OwlBear QdrantVectorStore | `src/owlbear/memory/knowledge/qdrant.py` | .95 | `search_similar()` with hybrid embedding, scope/type filters |
| OwlBear GraphStore | `src/owlbear/memory/knowledge/graph.py` | .90 | `list_documents()` for source listing |
| OwlBear test_knowledge_ingest.py | `tests/test_knowledge_ingest.py` | .85 | Mock patterns: `MagicMock` for graph/vector/chunker, `AsyncMock` for extractor |

## 3. Analysis

### 3.1 Theoretical Validity

The FunctionToolset pattern is sound. All 7 existing OwlBear toolsets subclass
`FunctionToolset`, register tools via `add_function()`, and store dependencies as
instance attributes injected through `__init__`. A KnowledgeToolset fits this pattern
exactly — it holds references to `IngestPipeline`, `QdrantVectorStore`, `GraphStore`,
and `EmbeddingProvider` and exposes thin async wrappers.

### 3.2 Architecture Fit — Dependency Injection

The knowledge pipeline requires 6 objects (conn, graph_store, vector_store,
embedding_provider, entity_extractor, text_chunker). Two injection strategies:

| Strategy | Complexity | KISS | Verdict |
|----------|-----------|------|---------|
| **A: Inject pre-built components** — pass IngestPipeline + QdrantVectorStore + GraphStore directly | Low | High | **Recommended (.85)** |
| B: Build components inside toolset from settings | Medium | Medium | Over-couples toolset to construction logic |
| C: Lazy-build via factory callback | Medium | Low | YAGNI — no need for deferred construction |

**Recommendation (.85):** Strategy A. The `build_toolsets()` function in `bootstrap.py`
already constructs all toolsets — it should build the knowledge components and pass
them in. This follows the existing pattern where `TerminalToolset` receives
`workspace_root` and `FileToolset` receives `workspace_root`.

### 3.3 Tool Function Signatures

Comparing PydanticAI RAG example with existing OwlBear toolsets:

| Aspect | PydanticAI RAG example | OwlBear toolsets |
|--------|----------------------|------------------|
| Tool return type | `str` | `str` (all tools return formatted strings) |
| Async | Yes | Yes (terminal, browser) or sync (filesystem, PydanticAI wraps) |
| Error handling | Exceptions propagate | Exceptions propagate → model sees error |
| Sandboxing | N/A | `_safe_path()` in FileToolset |

Proposed tool signatures:

```python
query_knowledge(query: str, top_k: int = 5) -> str
ingest_document(source: str, doc_type: str = "text") -> str
list_knowledge_sources() -> str
```

The `query_knowledge` tool needs to: (1) embed the query, (2) search via
`QdrantVectorStore.search_similar()`, (3) resolve document IDs back to content via
`GraphStore.get_document()`, (4) format results as readable text.

The `ingest_document` tool handles three source types:

- `doc_type="text"` → `IngestPipeline.ingest_text(source)`
- `doc_type="file"` → sandbox check + `IngestPipeline.ingest(Path(source))`
- `doc_type="url"` → `IngestPipeline.ingest(source)` (URL auto-detected)

The `list_knowledge_sources` tool → `GraphStore.list_documents()` → format as table.

### 3.4 File Sandboxing

For `doc_type="file"`, the toolset must enforce path sandboxing identical to
`FileToolset._safe_path()`. Resolve relative to `workspace_root`, reject paths that
escape via traversal. Reuse the same resolve+`is_relative_to` guard.

### 3.5 Registration in bootstrap.py

The toolset is **conditional** — it requires the knowledge components to be initialized.
Pattern: construct components from `OwlBearSettings` (knowledge_db_path, embedding
settings), then create `KnowledgeToolset`. If construction fails (e.g., qdrant-client
not installed), log warning and skip — identical to the `GitHubToolset` and
`SkillRegistry` conditional patterns in `build_toolsets()`.

### 3.6 bootstrap.py Construction Logic

The knowledge pipeline requires:

1. `sqlite3.connect(settings.knowledge_db_path)` → `conn`
2. `init_db(conn)` → ensure schema
3. `GraphStore(conn)` → graph_store
4. `QdrantVectorStore(location=str(settings.knowledge_db_path.parent / "qdrant"))` → vector_store
5. `BgeM3EmbeddingProvider(idle_timeout=settings.embedding_idle_timeout)` → embedder
6. `EntityExtractor(...)` → extractor (needs LLM model — may defer)
7. `TextChunker()` → chunker
8. `IngestPipeline(conn, graph_store, vector_store, embedder, extractor, chunker)`

Items 6-7 add complexity. For the toolset, `query_knowledge` only needs the
embedder + vector_store + graph_store. `ingest_document` needs the full pipeline.
**KISS approach:** Build the full pipeline in bootstrap, but handle missing optional
deps (FlagEmbedding) gracefully with try/except.

### 3.7 Comparison: Separate build function vs inline

| Approach | Pros | Cons |
|----------|------|------|
| **`build_knowledge_toolset()` helper** | Testable, contained, follows `build_mcp_registry()` | One more function |
| Inline in `build_toolsets()` | Less indirection | Bloats an already long function |

**Recommendation (.80):** Extract a `build_knowledge_toolset()` helper, consistent
with `build_mcp_registry()` pattern.

## 4. Recommendation (.85 confidence)

Implement `KnowledgeToolset(FunctionToolset)` in `src/owlbear/tools/knowledge.py`:

1. **Constructor** accepts `IngestPipeline`, `QdrantVectorStore`, `GraphStore`,
   `EmbeddingProvider`, `workspace_root: Path`.
2. **3 tools** registered via `add_function()` in `_register_tools()`.
3. **Sandboxing** for file paths via `_safe_path()` (same logic as FileToolset).
4. **Query flow:** embed query → `search_similar(embedding, top_k)` → resolve IDs
   via `get_document()` → format as numbered results.
5. **Registration:** conditional block in `build_toolsets()` with a
   `build_knowledge_toolset()` helper, wrapped in try/except.
6. **Tests:** Mock all knowledge components (MagicMock for graph/vector/chunker,
   AsyncMock for extractor), reuse patterns from `test_knowledge_ingest.py`.

Risks:

- **Embedding latency:** First `query_knowledge` call loads the BGE-M3 model (~3GB).
  Mitigation: existing idle-timeout + lazy loading in `BgeM3EmbeddingProvider`.
- **Entity extractor dependency:** `ingest_document` requires an LLM-backed extractor.
  Mitigation: make extractor optional in the toolset; if None, ingest with
  embeddings only (partial status). Or use a stub extractor for tests.

## 5. Follow-up Tasks

1. **Implement KnowledgeToolset** — `src/owlbear/tools/knowledge.py` with 3 tools
2. **Wire KnowledgeToolset into bootstrap.py** — `build_knowledge_toolset()` helper
3. **Unit tests for KnowledgeToolset** — mock all knowledge deps, ≥90% coverage

## 6. Testing Strategy

Reuse the established mocking patterns from `test_knowledge_ingest.py`:

- `MagicMock()` for `GraphStore` (sync methods)
- `MagicMock()` for `QdrantVectorStore` (sync `search_similar`, `store_embedding`)
- `MagicMock(spec=["embed", "embed_hybrid"])` for `EmbeddingProvider`
- `AsyncMock()` for `EntityExtractor.extract`
- `MagicMock()` for `TextChunker.chunk`
- In-memory SQLite with `init_db()` for `conn`
- `IngestPipeline` constructed with all mocks (as in existing fixtures)

For the toolset itself:

- Instantiate `KnowledgeToolset` with mocked deps
- Call tool wrapper methods directly (they're async)
- Verify correct delegation to underlying components
- Test path sandboxing with traversal attempts
- Test error formatting (failed ingest, empty results)
