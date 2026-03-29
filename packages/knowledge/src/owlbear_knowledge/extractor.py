"""Entity extraction pipeline — stub, not yet implemented (#15)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

_NOT_IMPL = "EntityExtractor not yet extracted from v1"


class ExtractionResult(BaseModel):
    """Result of entity extraction — entities and relationships found in text."""

    model_config = ConfigDict(frozen=True)

    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class EntityExtractor:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(self, model: str | object, **kwargs: object) -> None:
        raise NotImplementedError(_NOT_IMPL)

    async def extract(self, text: str) -> ExtractionResult:
        raise NotImplementedError
