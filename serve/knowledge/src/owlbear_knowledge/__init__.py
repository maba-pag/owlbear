"""OwlBear knowledge package."""

from __future__ import annotations

from owlbear_knowledge.cancellation import CancelSignal, LinkedCancelSignal
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline, IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import PageStatus, SourcePage
from owlbear_knowledge.query_service import (
    KnowledgeQueryError,
    KnowledgeQueryService,
    StructuredSearchResult,
)
from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult
from owlbear_knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_knowledge.status_store import (
    DocumentStatus,
    StatusStore,
    compute_content_hash,
)

__all__ = [
    "CancelSignal",
    "DocumentStatus",
    "DocumentStore",
    "GraphAugmentedRetriever",
    "GraphStore",
    "IngestPipeline",
    "IngestResult",
    "IntakeResult",
    "KnowledgeQueryError",
    "KnowledgeQueryService",
    "KnowledgeSourceStore",
    "LinkedCancelSignal",
    "PageStatus",
    "RefreshOrchestrator",
    "RefreshResult",
    "RetrievalResult",
    "SourcePage",
    "StatusStore",
    "StructuredSearchResult",
    "compute_content_hash",
    "init_db",
]
