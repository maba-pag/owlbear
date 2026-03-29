"""Knowledge query service — stub, not yet implemented (#15)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StructuredSearchResult(BaseModel):
    """Structured knowledge hit for consumers that need raw retrieval fields."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    title: str
    score: float
    snippet: str
    entity_type: str | None
    scope: str


class KnowledgeQueryService:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(  # noqa: PLR0913
        self,
        vector_store: object,
        graph_store: object,
        embedding_provider: object,
        *,
        scopes: list[str] | None = None,
        similarity_threshold: float = 0.3,
        retriever: object | None = None,
        consolidation_conn: object | None = None,
    ) -> None:
        _msg = "KnowledgeQueryService not yet extracted from v1"
        raise NotImplementedError(_msg)

    async def query(
        self,
        prompt: str,
        *,
        top_k: int = 5,
        token_budget: int = 4000,
    ) -> list[StructuredSearchResult]:
        raise NotImplementedError
