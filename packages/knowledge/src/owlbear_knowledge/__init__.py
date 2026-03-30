"""OwlBear knowledge package."""

from __future__ import annotations

from owlbear_knowledge.bookmark_store import Bookmark, BookmarkStore
from owlbear_knowledge.consolidation import ConsolidationInsight, ConsolidationService
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.evaluator import EvaluationResult, SourceEvaluator
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline, IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_knowledge.status_store import DocumentStatus, StatusStore, compute_content_hash

__all__ = [
    "Bookmark",
    "BookmarkStore",
    "ConsolidationInsight",
    "ConsolidationService",
    "DocumentStatus",
    "DocumentStore",
    "EvaluationResult",
    "GraphStore",
    "IngestPipeline",
    "IngestResult",
    "IntakeResult",
    "KnowledgeSourceStore",
    "SourceEvaluator",
    "StatusStore",
    "compute_content_hash",
    "init_db",
]
