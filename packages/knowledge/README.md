# owlbear-knowledge

Knowledge engine for OwlBear: graph-augmented vector retrieval, document ingestion, entity extraction, and per-turn context injection.

## Install

```bash
uv pip install -e packages/knowledge
```

## Optional dependencies

Install only the extras you need:

```bash
# Qdrant vector store backend
uv pip install -e "packages/knowledge[qdrant]"

# BGE-M3 embedding provider (requires ~2.3 GB model download on first use)
uv pip install -e "packages/knowledge[embedding]"

# HTTP intake (fetch URLs via httpx)
uv pip install -e "packages/knowledge[intake]"

# All optional dependencies at once
uv pip install -e "packages/knowledge[full]"
```

## BGE-M3 model download

The `BgeM3EmbeddingProvider` uses `BAAI/bge-m3` from Hugging Face. The model (~2.3 GB) is downloaded on first use and cached in your HuggingFace cache directory (`~/.cache/huggingface/hub` by default). No manual download step is needed — the first call to `embed()` or `embed_hybrid()` triggers it automatically.

## Module overview

Modules are grouped by concern. All 22 public modules are importable without optional deps.

### Data stores
| Module | Classes / Functions |
|--------|-------------------|
| `document_store` | `DocumentStore` |
| `graph_store` | `GraphStore` |
| `status_store` | `DocumentStatus`, `StatusStore`, `compute_content_hash` |
| `source_store` | `KnowledgeSourceStore` |
| `bookmark_store` | `Bookmark`, `BookmarkStore` |

### Schema / models
| Module | Classes / Functions |
|--------|-------------------|
| `schema` | `init_db` |
| `models` | internal data models |
| `protocol` | `VectorStoreProtocol`, `HybridEmbedding` |

### Ingestion pipeline
| Module | Classes / Functions |
|--------|-------------------|
| `ingest` | `IngestPipeline`, `IngestResult` |
| `intake` | `IntakeResult` (optional: httpx) |
| `loader` | file/URL loading utilities |
| `chunker` | text chunking utilities |
| `extractor` | entity extraction |

### Graph construction
| Module | Classes / Functions |
|--------|-------------------|
| `graph_builder` | graph-building utilities |
| `inter_doc_graph_builder` | `InterDocGraphBuilder` (canonical definition) |

### Retrieval and search
| Module | Classes / Functions |
|--------|-------------------|
| `retrieval` | `GraphAugmentedRetriever`, `RetrievalResult` |
| `query_service` | `KnowledgeQueryService`, `StructuredSearchResult` |
| `embeddings` | `EmbeddingProvider`, `BgeM3EmbeddingProvider` (optional: FlagEmbedding) |
| `qdrant` | `QdrantVectorStore` (optional: qdrant-client) |

### Utilities
| Module | Classes / Functions |
|--------|-------------------|
| `cancellation` | `CancelSignal`, `LinkedCancelSignal` |
| `consolidation` | `ConsolidationService`, `ConsolidationInsight` |
| `evaluator` | `SourceEvaluator`, `EvaluationResult` |

## Qdrant setup modes

`QdrantVectorStore` accepts a `location` argument that determines the storage backend:

| Mode | `location` value | Notes |
|------|-----------------|-------|
| In-memory | `":memory:"` | Default; data lost on exit. Useful for testing. |
| Filesystem | `"/path/to/dir"` | Persistent local storage. |
| HTTP server | `"http://localhost:6333"` | Remote Qdrant instance. |
| HTTPS server | `"https://host:6333"` | Remote Qdrant instance with TLS. |

```python
from owlbear_knowledge.qdrant import QdrantVectorStore

# In-memory (testing / prototyping)
vs = QdrantVectorStore(location=":memory:")

# Persistent filesystem
vs = QdrantVectorStore(location="/data/qdrant")

# Remote Qdrant server
vs = QdrantVectorStore(location="http://localhost:6333")
```

## Basic usage

```python
from owlbear_knowledge import (
    GraphAugmentedRetriever,
    KnowledgeQueryService,
    RetrievalResult,
    StructuredSearchResult,
)
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider

vector_store = QdrantVectorStore(location=":memory:")
graph_store = GraphStore(conn)
embedding_provider = BgeM3EmbeddingProvider()  # model downloaded on first use

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

# Returns a formatted context string for injection into an LLM prompt
context: str | None = service.query_for_context("What is OwlBear?")
if context:
    print(context)

# Or get structured results
results: list[StructuredSearchResult] = service.search("What is OwlBear?")
```
