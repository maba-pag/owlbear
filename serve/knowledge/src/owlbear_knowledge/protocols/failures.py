"""Typed, redacted failure carriers for the Knowledge boundaries."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from owlbear_knowledge.protocols.common import BoundaryModel


class KnowledgeFailureStage(StrEnum):
    """Pipeline boundary where a knowledge operation failed."""

    ACQUISITION = "acquisition"
    EXTRACTION = "extraction"
    INDEXING = "indexing"
    PERSISTENCE = "persistence"
    QUERY = "query"


KnowledgeFailureCode = Literal[
    "url_rejected",
    "dns_failure",
    "transport_failure",
    "http_status",
    "timeout",
    "response_too_large",
    "unsupported_media_type",
    "content_boundary_missing",
    "extraction_failed",
    "persistence_failed",
    "embedding_failed",
    "vector_write_failed",
    "query_embedding_failed",
    "vector_query_failed",
]


class KnowledgeFailure(BoundaryModel):
    """Redacted, structured description of one knowledge operation failure."""

    stage: KnowledgeFailureStage
    code: KnowledgeFailureCode
    retryable: bool
    message: str


class KnowledgeOperationError(RuntimeError):
    """Raised when a lower knowledge operation fails with a typed carrier."""

    def __init__(self, failure: KnowledgeFailure) -> None:
        self.failure = failure
        super().__init__(failure.message)
