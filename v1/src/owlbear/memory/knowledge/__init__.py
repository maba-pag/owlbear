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
    "StructuredSearchResult",
    "VectorStoreProtocol",
    "init_db",
]

# Lazy import map: attribute name → (relative submodule, attribute name).
# Covers only the 14 public symbols declared in __all__.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BookmarkStore": (".bookmark", "BookmarkStore"),
    "Document": (".models", "Document"),
    "DocumentStatus": (".document_store", "DocumentStatus"),
    "Edge": (".models", "Edge"),
    "EmbeddingProvider": (".embeddings", "EmbeddingProvider"),
    "Entity": (".models", "Entity"),
    "EntityType": (".models", "EntityType"),
    "GraphStore": (".graph", "GraphStore"),
    "IngestPipeline": (".ingest", "IngestPipeline"),
    "IngestResult": (".ingest", "IngestResult"),
    "KnowledgeQueryService": (".query_service", "KnowledgeQueryService"),
    "RelationType": (".models", "RelationType"),
    "StructuredSearchResult": (".query_service", "StructuredSearchResult"),
    "VectorStoreProtocol": (".protocol", "VectorStoreProtocol"),
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
