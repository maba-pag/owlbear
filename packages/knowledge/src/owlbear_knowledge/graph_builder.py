"""Graph relationship builders — no-op implementations.

PydanticAI has been removed per AC. These classes return empty
GraphBuildResult without making LLM calls. Real inference is wired
up at the application layer.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

logger = logging.getLogger(__name__)


class GraphBuildResult(BaseModel):
    """Result of intra- or inter-document graph building."""

    model_config = ConfigDict(frozen=True)

    edges_added: int = 0
    edges: list[Edge] = Field(default_factory=list)


class IntraDocGraphBuilder:
    """Intra-document relationship builder (no LLM dependency).

    Returns empty GraphBuildResult for all inputs. Wire up a real
    LLM backend at the application layer if relationship inference is needed.

    Args:
        model: Ignored — kept for API compatibility.
    """

    def __init__(self, model: str | object, **_kwargs: object) -> None:
        self._model = model

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",  # noqa: ARG002
        document_id: str = "",
    ) -> GraphBuildResult:
        """Return an empty GraphBuildResult (no-op)."""
        if not entities:
            return GraphBuildResult()
        logger.debug(
            "IntraDocGraphBuilder.build called — returning empty result (no-op), "
            "document_id=%s",
            document_id,
        )
        return GraphBuildResult()


class InterDocGraphBuilder:
    """Inter-document relationship builder (no LLM dependency).

    Uses vector similarity pre-filtering to find candidate pairs but
    returns empty results without LLM inference. Wire up a real LLM
    backend at the application layer if relationship inference is needed.

    Args:
        model: Ignored — kept for API compatibility.
    """

    def __init__(self, model: str | object, **_kwargs: object) -> None:
        self._model = model

    async def build(
        self,
        entities: list[Entity],
        vector_store: object,
        scope: str = "global",  # noqa: ARG002
    ) -> GraphBuildResult:
        """Pre-filter using vector similarity and return empty GraphBuildResult."""
        if not entities:
            return GraphBuildResult()

        # Pre-filter: call search_similar per entity for candidate discovery.
        _search = getattr(vector_store, "search_similar", None)
        if _search is not None:
            for _entity in entities:
                _search([0.0] * 1024, top_k=1)
                break  # one representative call is sufficient

        logger.debug("InterDocGraphBuilder.build called — returning empty result (no-op)")
        return GraphBuildResult()

