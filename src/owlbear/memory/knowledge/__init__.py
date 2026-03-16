"""Knowledge graph — models, schema, CRUD store, vector storage, and extraction.

All imports are lazy to avoid a circular-import chain
(ingest → intake → core.retry → core.errors → tools → core.retry).
"""

from __future__ import annotations

import importlib

__all__ = [
    "BookmarkStore",
    "Document",
    "DocumentStatus",
    "Edge",
    "EmbeddingProvider",
    "Entity",
    "EntityType",
    "GraphStore",
    "IngestPipeline",
    "IngestResult",
    "KnowledgeQueryService",
    "RelationType",
    "VectorStoreProtocol",
    "init_db",
]

# Lazy import map: attribute name → (relative submodule, attribute name).
# Covers all 14 public symbols AND legacy symbols for back-compat.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BgeM3EmbeddingProvider": (".embeddings", "BgeM3EmbeddingProvider"),
    "Bookmark": (".bookmark", "Bookmark"),
    "BookmarkPipeline": (".bookmark_pipeline", "BookmarkPipeline"),
    "BookmarkResult": (".bookmark_pipeline", "BookmarkResult"),
    "BookmarkStore": (".bookmark", "BookmarkStore"),
    "BookmarkToolset": (".bookmark_toolset", "BookmarkToolset"),
    "Chunk": (".chunker", "Chunk"),
    "ConsolidationService": (".consolidation", "ConsolidationService"),
    "Document": (".models", "Document"),
    "DocumentStatus": (".document_store", "DocumentStatus"),
    "DocumentStore": (".document_store", "DocumentStore"),
    "Edge": (".models", "Edge"),
    "Embedding": (".protocol", "Embedding"),
    "EmbeddingProvider": (".embeddings", "EmbeddingProvider"),
    "Entity": (".models", "Entity"),
    "EntityExtractor": (".extractor", "EntityExtractor"),
    "EntityType": (".models", "EntityType"),
    "EvaluationResult": (".evaluator", "EvaluationResult"),
    "ExtractionResult": (".extractor", "ExtractionResult"),
    "GraphAugmentedRetriever": (".retrieval", "GraphAugmentedRetriever"),
    "GraphBuildResult": (".graph_builder", "GraphBuildResult"),
    "GraphEnricher": (".enrichment", "GraphEnricher"),
    "GraphStore": (".graph", "GraphStore"),
    "HybridEmbedding": (".protocol", "HybridEmbedding"),
    "IngestPipeline": (".ingest", "IngestPipeline"),
    "IngestResult": (".ingest", "IngestResult"),
    "InterDocGraphBuilder": (".inter_doc_graph_builder", "InterDocGraphBuilder"),
    "IntraDocGraphBuilder": (".graph_builder", "IntraDocGraphBuilder"),
    "KnowledgeQueryService": (".query_service", "KnowledgeQueryService"),
    "RelationType": (".models", "RelationType"),
    "RetrievalResult": (".retrieval", "RetrievalResult"),
    "SourceEvaluator": (".evaluator", "SourceEvaluator"),
    "SparseVector": (".protocol", "SparseVector"),
    "TextChunker": (".chunker", "TextChunker"),
    "VectorStoreProtocol": (".protocol", "VectorStoreProtocol"),
    "compute_content_hash": (".document_store", "compute_content_hash"),
    "init_db": (".schema", "init_db"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        submodule, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(submodule, __name__)
        val = getattr(mod, attr)
        globals()[name] = val  # cache for subsequent access
        return val
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
