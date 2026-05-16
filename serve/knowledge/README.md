# owlbear-knowledge — Knowledge Engine

Graph-augmented vector retrieval engine for the OwlBear pipeline. Provides document ingestion, entity extraction, semantic search, and per-turn context injection for agent prompts.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

No standalone launch. Used as a library by `owlbear-mcp-knowledge` and consumer code.

```python
from owlbear_knowledge import (
    GraphAugmentedRetriever,
    KnowledgeQueryService,
    RetrievalResult,
    StructuredSearchResult,
)
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.schema import init_db

conn = init_db("path/to/knowledge.db")
vector_store = QdrantVectorStore(location=":memory:")
graph_store = GraphStore(conn)
embedding_provider = BgeM3EmbeddingProvider()   # ~2.3 GB download on first use

retriever = GraphAugmentedRetriever(
    vector_store=vector_store,
    graph_store=graph_store,
    embedding_provider=embedding_provider,
)
service = KnowledgeQueryService(
    vector_store=vector_store,
    graph_store=graph_store,
    embedding_provider=embedding_provider,
    retriever=retriever,
)

context: str | None = service.query_for_context("What is OwlBear?")
results: list[StructuredSearchResult] = service.search("What is OwlBear?")
```

### Module groups

| Group | Key exports |
|-------|-------------|
| Data stores | `DocumentStore`, `GraphStore`, `StatusStore`, `KnowledgeSourceStore` |
| Ingestion | `IngestPipeline`, `IngestResult`, `TextChunker` |
| Retrieval | `GraphAugmentedRetriever`, `KnowledgeQueryService`, `RetrievalResult`, `StructuredSearchResult` |
| Embeddings | `BgeM3EmbeddingProvider`, `EmbeddingProvider` |
| Graph | `IntraDocGraphBuilder`, `InterDocGraphBuilder` |
| Utilities | `CancelSignal`, `SourceEvaluator` |

Active operational API is intentionally narrow. Bookmark, scope-transfer, and
consolidation surfaces have been retired and removed from this package.

## Configuration

No environment variables at the library level. Configuration is passed via constructor arguments. See `serve/mcp-knowledge/README.md` for the MCP server's environment variables.

### Qdrant storage modes

| Mode | `location` value |
|------|-----------------|
| In-memory | `":memory:"` |
| Filesystem | `"/path/to/dir"` |
| Remote HTTP | `"http://localhost:6333"` |

## Dependencies

### Required

| Package | Purpose |
|---------|---------|
| `pydantic` | Model validation |
| `strictyaml` | YAML parsing for source config |

### Optional extras

Install with `uv pip install -e "serve/knowledge[<extra>]"`:

| Extra | Packages | Purpose |
|-------|----------|---------|
| `qdrant` | `qdrant-client` | Persistent vector store |
| `embedding` | `FlagEmbedding` | BGE-M3 embedding provider (~2.3 GB model download on first use) |
| `intake` | `httpx` | HTTP URL ingestion |
| `llm` | `openai` | LLM-based entity extraction |
| `full` | all of the above | All features |
