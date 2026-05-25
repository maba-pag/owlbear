"""Intra-document graph relationship builder.

:class:`IntraDocGraphBuilder` uses an injected :class:`StructuredExtractor`
to infer edges within a document.  Pass ``extractor=`` for real inference;
omit it for backward-compatible no-op behaviour.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

if TYPE_CHECKING:
    from owlbear_knowledge.protocol import StructuredExtractor

logger = logging.getLogger(__name__)

_INTRA_BATCH_THRESHOLD = 80
_INTRA_WEIGHT = 0.5
_INTRA_SOURCE = "intra_doc_inference"
_MIN_ENTITIES = 2

GRAPH_BUILDER_PROMPT = """\
You are a knowledge-graph relationship-inference engine.

Given a list of entities extracted from a single document, infer implicit
relationships between them that are not already captured as edges. Only use
these relation types: {relation_types}.

Each inferred edge needs:
  - source_id: the id of the source entity
  - target_id: the id of the target entity
  - relation: one of {relation_types}

Only propose relationships that are strongly implied by the entity names and
descriptions. Do NOT hallucinate edges that lack evidence. When in doubt, omit.

Return your findings as JSON matching the ExtractionResult schema. Leave the
entities list empty — only return edges.
"""


def _stamp_intra_edge(edge: Edge) -> Edge:
    """Return a copy of *edge* stamped with intra-doc weight and source."""
    return edge.model_copy(
        update={
            "weight": _INTRA_WEIGHT,
            "metadata": {**edge.metadata, "source": _INTRA_SOURCE},
        }
    )


def _build_intra_prompt(entities: list[Entity], scope: str, document_id: str) -> str:
    names = ", ".join(e.name for e in entities)
    return f"scope: {scope}\ndocument_id: {document_id}\nEntities: {names}"


class GraphBuildResult(BaseModel):
    """Result of intra- or inter-document graph building."""

    model_config = ConfigDict(frozen=True)

    edges_added: int = 0
    edges: list[Edge] = Field(default_factory=list)


class IntraDocGraphBuilder:
    """Intra-document relationship builder with optional injected extractor.

    When ``extractor`` is provided, ``build()`` calls the extractor once for
    ≤ 80 entities, or once per entity type for > 80 entities, and stamps all
    returned edges with ``weight=0.5`` and ``metadata["source"]="intra_doc_inference"``.

    When ``extractor`` is omitted, returns empty results (backward-compatible
    no-op, accepts the legacy ``model=`` positional argument).

    Args:
        model: Ignored — kept for backward compatibility.
        extractor: Injected :class:`StructuredExtractor` for LLM inference.
    """

    def __init__(
        self,
        model: str | object | None = None,
        *,
        extractor: StructuredExtractor | None = None,
        **_kwargs: object,
    ) -> None:
        self._model = model
        self._extractor = extractor

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",
        document_id: str = "",
    ) -> GraphBuildResult:
        """Infer intra-document edges for *entities*.

        Returns an empty :class:`GraphBuildResult` when fewer than 2 entities
        are provided or no extractor is wired.
        """
        if len(entities) < _MIN_ENTITIES:
            return GraphBuildResult()
        if self._extractor is None:
            logger.debug(
                "IntraDocGraphBuilder.build called — returning empty result (no-op), document_id=%s",
                document_id,
            )
            return GraphBuildResult()

        all_edges: list[Edge] = []
        if len(entities) <= _INTRA_BATCH_THRESHOLD:
            prompt = _build_intra_prompt(entities, scope, document_id)
            result = await self._extractor.extract(prompt)
            all_edges.extend(result.edges)
        else:
            by_type: dict[str, list[Entity]] = defaultdict(list)
            for ent in entities:
                by_type[ent.entity_type].append(ent)
            for etype_entities in by_type.values():
                prompt = _build_intra_prompt(etype_entities, scope, document_id)
                result = await self._extractor.extract(prompt)
                all_edges.extend(result.edges)

        stamped = [_stamp_intra_edge(e) for e in all_edges]
        return GraphBuildResult(edges=stamped, edges_added=len(stamped))
