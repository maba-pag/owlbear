"""Cross-chunk relationship inference within a single document.

Uses a PydanticAI agent to discover implicit relationships between
entities extracted from different chunks of the same document.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.models import Edge, Entity, RelationType

if TYPE_CHECKING:
    from pydantic_ai.models import Model

logger = logging.getLogger(__name__)

_BATCH_THRESHOLD = 80
"""Entity count above which we batch by entity_type."""

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


class GraphBuildResult(BaseModel):
    """Result of intra-document graph building."""

    model_config = ConfigDict(frozen=True)

    edges_added: int = 0
    edges: list[Edge] = Field(default_factory=list)


class IntraDocGraphBuilder:
    """Discover cross-chunk relationships within a single document.

    Uses a PydanticAI ``Agent[None, ExtractionResult]`` to infer implicit
    relationships between entities that were extracted from different chunks.

    Usage::

        builder = IntraDocGraphBuilder(model="openai:gpt-4o")
        result = await builder.build(entities, scope="global", document_id="doc-1")
        print(result.edges_added, result.edges)
    """

    def __init__(self, model: str | Model) -> None:
        relation_types = ", ".join(rt.value for rt in RelationType)
        self._agent: Agent[None, ExtractionResult] = Agent(
            model,
            output_type=ExtractionResult,
            system_prompt=GRAPH_BUILDER_PROMPT.format(relation_types=relation_types),
        )

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",
        document_id: str | None = None,
    ) -> GraphBuildResult:
        """Infer cross-chunk relationships for *entities* from a single document.

        Parameters
        ----------
        entities:
            Entities extracted from the document's chunks.
        scope:
            Scope tag applied to all inferred edges.
        document_id:
            Document identifier for logging/provenance.

        Returns
        -------
        GraphBuildResult:
            The inferred edges and a count of edges added.
        """
        _min_entities = 2
        if len(entities) < _min_entities:
            return GraphBuildResult()

        if len(entities) > _BATCH_THRESHOLD:
            return await self._build_batched(entities, scope, document_id)

        return await self._build_single(entities, scope, document_id)

    # -- internal ------------------------------------------------------------

    async def _build_single(
        self,
        entities: list[Entity],
        scope: str,
        document_id: str | None,
    ) -> GraphBuildResult:
        """Run a single LLM call for all entities."""
        prompt = self._format_prompt(entities)
        try:
            result = await self._agent.run(prompt)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Intra-document graph inference failed for document %s",
                document_id,
                exc_info=True,
            )
            return GraphBuildResult()

        edges = self._stamp_edges(result.output.edges, scope)
        return GraphBuildResult(edges_added=len(edges), edges=edges)

    async def _build_batched(
        self,
        entities: list[Entity],
        scope: str,
        document_id: str | None,
    ) -> GraphBuildResult:
        """Batch entities by entity_type and run one LLM call per batch."""
        batches: dict[str, list[Entity]] = defaultdict(list)
        for entity in entities:
            batches[entity.entity_type].append(entity)

        all_edges: list[Edge] = []
        for entity_type, batch in batches.items():
            prompt = self._format_prompt(batch)
            try:
                result = await self._agent.run(prompt)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Intra-document graph inference failed for batch %s in document %s",
                    entity_type,
                    document_id,
                    exc_info=True,
                )
                continue

            all_edges.extend(self._stamp_edges(result.output.edges, scope))

        return GraphBuildResult(edges_added=len(all_edges), edges=all_edges)

    @staticmethod
    def _format_prompt(entities: list[Entity]) -> str:
        """Build a user prompt listing entities for the LLM."""
        lines = [
            f"Entities ({len(entities)}):",
            *(
                f"- [{e.id}] {e.name} ({e.entity_type}): {e.description}"
                for e in entities
            ),
        ]
        return "\n".join(lines)

    @staticmethod
    def _stamp_edges(edges: list[Edge], scope: str) -> list[Edge]:
        """Ensure all edges have weight=0.5, intra_doc metadata, and scope."""
        return [
            Edge(
                id=edge.id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                relation=edge.relation,
                weight=0.5,
                metadata={"source": "intra_doc_inference"},
                scope=scope,
            )
            for edge in edges
        ]
