"""Graph builders — stub, not yet implemented (#15)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

_NOT_IMPL_INTRA = "IntraDocGraphBuilder not yet extracted from v1"
_NOT_IMPL_INTER = "InterDocGraphBuilder not yet extracted from v1"


class GraphBuildResult(BaseModel):
    """Result of intra- or inter-document graph building."""

    model_config = ConfigDict(frozen=True)

    edges_added: int = 0
    edges: list[Edge] = Field(default_factory=list)


class IntraDocGraphBuilder:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(self, model: str | object, **kwargs: object) -> None:
        raise NotImplementedError(_NOT_IMPL_INTRA)

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",
        document_id: str = "",
    ) -> GraphBuildResult:
        raise NotImplementedError


class InterDocGraphBuilder:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(self, model: str | object, **kwargs: object) -> None:
        raise NotImplementedError(_NOT_IMPL_INTER)

    async def build(
        self,
        entities: list[Entity],
        vector_store: object,
        scope: str = "global",
    ) -> GraphBuildResult:
        raise NotImplementedError
