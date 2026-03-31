# owlbear-knowledge

Knowledge engine for OwlBear: graph-augmented vector retrieval, document ingestion, entity extraction, and per-turn context injection.

## Install

```bash
uv pip install -e packages/knowledge
```

## Optional dependencies

- **Qdrant** — vector store backend (`qdrant-client>=1.7`). Install with `uv pip install -e "packages/knowledge[qdrant]"`.
- **Embedding provider** — sentence-transformers or any `EmbeddingProvider` implementation for dense and hybrid embeddings (e.g. `bge-m3`).

## Basic usage

```python
from owlbear_knowledge import GraphAugmentedRetriever, RetrievalResult
from owlbear_knowledge.query_service import KnowledgeQueryService

# Build the retriever
retriever = GraphAugmentedRetriever(
    vector_store=vector_store,
    graph_store=graph_store,
    embedding_provider=embedding_provider,
)

# Query for context (inject into LLM prompt)
service = KnowledgeQueryService(
    vector_store=vector_store,
    graph_store=graph_store,
    embedding_provider=embedding_provider,
    retriever=retriever,
)

context: str | None = service.query_for_context("What is OwlBear?")
if context:
    print(context)
# Relevant knowledge:
#
# - OwlBear overview: OwlBear is an on-demand AI development system...
```
