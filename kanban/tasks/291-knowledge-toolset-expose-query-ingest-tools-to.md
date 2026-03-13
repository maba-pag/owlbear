---
id: 291
title: Knowledge toolset — expose query/ingest tools to agents
status: archived
priority: critical
created: 2026-03-01T02:51:53.0599074+01:00
updated: 2026-03-01T17:08:15.027447+01:00
started: 2026-03-01T03:20:30.9801286+01:00
completed: 2026-03-01T17:08:15.027447+01:00
tags:
    - phase-11
    - knowledge-graph
    - tools
depends_on:
    - 308
class: standard
---

## Context
The knowledge pipeline (graph.py, qdrant.py, ingest.py, embeddings.py) is fully built and tested but agents have NO tool to use it. Create a KnowledgeToolset(FunctionToolset) in src/owlbear/tools/knowledge.py that exposes query/ingest tools.
See docs/research/knowledge-toolset.md for full research findings.

## Acceptance Criteria

### KnowledgeToolset class (src/owlbear/tools/knowledge.py)
- [ ] KnowledgeToolset(FunctionToolset) subclass
- [ ] Constructor: __init__(self, ingest_pipeline: IngestPipeline, vector_store: VectorStoreProtocol, graph_store: GraphStore, embedding_provider: EmbeddingProvider, workspace_root: Path) -- stores all as instance attributes, calls _register_tools()
- [ ] _register_tools() registers 3 tools via add_function() with name + description
- [ ] _safe_path(user_path: str) -> Path -- resolve against workspace_root, reject via is_relative_to guard (same pattern as FileToolset._safe_path)

### query_knowledge tool
- [ ] Signature: query_knowledge(query: str, top_k: int = 5) -> str
- [ ] Flow: embedding_provider.embed([query])[0] -> vector_store.search_similar(embedding, top_k=top_k, embedding_type='document') -> for each (doc_id, score): graph_store.get_document(doc_id) -> format
- [ ] Output format: numbered list -- 1. [title] (score: 0.85) then content[:500] per result (truncate content to 500 chars)
- [ ] Empty results: return 'No results found.'
- [ ] Missing document (get_document returns None): skip that result gracefully

### ingest_document tool
- [ ] Signature: ingest_document(source: str, doc_type: str = 'text') -> str
- [ ] Dispatch: doc_type='text' -> ingest_pipeline.ingest_text(source); doc_type='file' -> _safe_path(source) then ingest_pipeline.ingest(Path(source)); doc_type='url' -> ingest_pipeline.ingest(source)
- [ ] Invalid doc_type -> raise ValueError
- [ ] Returns formatted IngestResult summary string

### list_knowledge_sources tool
- [ ] Signature: list_knowledge_sources() -> str
- [ ] Delegates to graph_store.list_documents()
- [ ] Output: formatted list with title, id, scope per document
- [ ] Empty: return 'No documents ingested.'

### Bootstrap wiring
- [ ] build_knowledge_toolset(settings, workspace_root) helper function in bootstrap.py
- [ ] Constructs: sqlite3 conn, init_db, GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, EntityExtractor, TextChunker, IngestPipeline
- [ ] Returns KnowledgeToolset or None on failure
- [ ] Called in build_toolsets() inside try/except, appended to raw list
- [ ] Wrapped in HookedToolset like all other toolsets

### Coverage
- [ ] >= 90% coverage on src/owlbear/tools/knowledge.py

## Implementation Notes
- Follow TerminalToolset pattern: __init__ -> _register_tools() -> add_function()
- Use EmbeddingProvider protocol (dense-only via embed()), NOT embed_hybrid() -- KISS, search_similar works with list[float]
- Use VectorStoreProtocol for vector_store param (better testability)
- Use embedding_type='document' in search_similar (search documents, not entities)
- bootstrap construction order: conn -> init_db -> GraphStore -> QdrantVectorStore -> BgeM3EmbeddingProvider -> EntityExtractor -> TextChunker -> IngestPipeline -> KnowledgeToolset
- Reuse MagicMock/AsyncMock patterns from test_knowledge_ingest.py
- Depends on test task #308 (TDD: tests first)
