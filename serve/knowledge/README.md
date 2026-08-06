# owlbear-knowledge — Knowledge Engine

Graph-augmented vector retrieval engine for the OwlBear pipeline. Provides document ingestion, entity extraction, semantic search, and per-turn context injection for agent prompts.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

No standalone launch. Used as a library by `owlbear-knowledge-mcp` and consumer code.

```python
import sqlite3

from owlbear_knowledge import protocols, stores
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.fetcher import ContentFetcher, HttpxContentFetcher
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.stores.content import ContentStore

conn = sqlite3.connect("path/to/knowledge.db")
source_store: protocols.SourceStore = stores.SqliteSourceStore(conn)
graph_store: protocols.GraphStore = stores.SqliteGraphStore(conn)
vector_store = QdrantVectorStore(location=":memory:")
embedding_provider = BgeM3EmbeddingProvider()   # ~2.3 GB download on first use
chunker = TextChunker()
content_store: protocols.ContentStore = ContentStore(
    db=conn,
    vector_store=vector_store,
    embedding_provider=embedding_provider,
    chunker=chunker,
)

fetcher: ContentFetcher = HttpxContentFetcher()
```

### Module groups

| Group | Key exports |
|-------|-------------|
| Package surface | `protocols`, `stores` |
| Protocols | `ContentStore`, `GraphStore`, `SourceStore`, `QueryFacade`, `IngestCoordinator` |
| Store implementations | `stores.ContentStore`, `stores.SqliteGraphStore`, `stores.SqliteSourceStore` |
| Fetching | `ContentFetcher`, `HttpxContentFetcher` |
| Embeddings | `BgeM3EmbeddingProvider`, `EmbeddingProvider`, `HybridEmbedding` |
| Vector search | `QdrantVectorStore` |

Active operational API is intentionally narrow. Bookmark, scope-transfer, and
consolidation surfaces have been retired and removed from this package.

## Configuration

No environment variables at the library level. Configuration is passed via constructor arguments. See [knowledge-mcp README](../knowledge-mcp/README.md) for the MCP server's environment variables.

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
