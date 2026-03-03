"""Knowledge graph — models, schema, CRUD store, vector storage, and extraction."""

from __future__ import annotations

from owlbear.memory.knowledge.bookmark import Bookmark, BookmarkStore
from owlbear.memory.knowledge.bookmark_pipeline import BookmarkPipeline, BookmarkResult
from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset
from owlbear.memory.knowledge.chunker import Chunk, TextChunker
from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider, EmbeddingProvider
from owlbear.memory.knowledge.evaluator import EvaluationResult, SourceEvaluator
from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.graph_builder import GraphBuildResult, IntraDocGraphBuilder
from owlbear.memory.knowledge.ingest import (
    DocumentStatus,
    IngestPipeline,
    IngestResult,
    compute_content_hash,
)
from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear.memory.knowledge.models import (
    Document,
    Edge,
    Entity,
    EntityType,
    RelationType,
)
from owlbear.memory.knowledge.protocol import (
    Embedding,
    HybridEmbedding,
    SparseVector,
    VectorStoreProtocol,
)
from owlbear.memory.knowledge.qdrant import QdrantVectorStore
from owlbear.memory.knowledge.query_service import KnowledgeQueryService
from owlbear.memory.knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult
from owlbear.memory.knowledge.schema import init_db

__all__ = [
    "BgeM3EmbeddingProvider",
    "Bookmark",
    "BookmarkPipeline",
    "BookmarkResult",
    "BookmarkStore",
    "BookmarkToolset",
    "Chunk",
    "Document",
    "DocumentStatus",
    "Edge",
    "Embedding",
    "EmbeddingProvider",
    "Entity",
    "EntityExtractor",
    "EntityType",
    "EvaluationResult",
    "ExtractionResult",
    "GraphAugmentedRetriever",
    "GraphBuildResult",
    "GraphStore",
    "HybridEmbedding",
    "IngestPipeline",
    "IngestResult",
    "InterDocGraphBuilder",
    "IntraDocGraphBuilder",
    "KnowledgeQueryService",
    "QdrantVectorStore",
    "RelationType",
    "RetrievalResult",
    "SourceEvaluator",
    "SparseVector",
    "TextChunker",
    "VectorStoreProtocol",
    "compute_content_hash",
    "init_db",
]
