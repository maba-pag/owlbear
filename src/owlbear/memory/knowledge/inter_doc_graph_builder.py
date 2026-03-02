"""Cross-document relationship inference using embedding similarity pre-filtering.

Uses a PydanticAI agent to discover implicit relationships between
entities extracted from different documents. Pre-filters candidate pairs
using vector similarity, then batches them for LLM inference.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph_builder import GraphBuildResult
from owlbear.memory.knowledge.models import Edge, Entity, RelationType

if TYPE_CHECKING:
    from pydantic_ai.models import Model

    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)

_BATCH_SIZE = 40
"""Number of entity pairs per LLM batch call."""

INTER_DOC_PROMPT = """\
You are a knowledge-graph relationship-inference engine.

Given pairs of entities extracted from DIFFERENT documents, infer implicit
cross-document relationships between them. Only use these relation types:
{relation_types}.

Each inferred edge needs:
  - source_id: the id of the source entity
  - target_id: the id of the target entity
  - relation: one of {relation_types}

Only propose relationships that are strongly implied by the entity names,
descriptions, and types. These entities come from separate documents, so
focus on conceptual, dependency, or implementation relationships that
bridge document boundaries. Do NOT hallucinate edges that lack evidence.
When in doubt, omit.

Return your findings as JSON matching the ExtractionResult schema. Leave the
entities list empty — only return edges.
"""


class InterDocGraphBuilder:
    """Discover cross-document relationships using embedding pre-filtering + LLM inference.

    Uses vector similarity to identify candidate entity pairs from different
    documents, then runs a PydanticAI agent to infer relationships between them.

    Usage::

        builder = InterDocGraphBuilder(
            model="openai:gpt-4o",
            vector_store=qdrant_store,
            graph_store=graph_store,
            top_k=10,
            cosine_threshold=0.70,
        )
        result = await builder.build(entities, scope="global")
        print(result.edges_added, result.edges)
    """

    def __init__(
        self,
        model: str | Model,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        top_k: int = 10,
        cosine_threshold: float = 0.70,
    ) -> None:
        relation_types = ", ".join(rt.value for rt in RelationType)
        self._agent: Agent[None, ExtractionResult] = Agent(
            model,
            output_type=ExtractionResult,
            system_prompt=INTER_DOC_PROMPT.format(relation_types=relation_types),
        )
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._top_k = top_k
        self._cosine_threshold = cosine_threshold

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",
        document_id: str | None = None,  # noqa: ARG002
    ) -> GraphBuildResult:
        """Infer cross-document relationships for *entities*.

        Parameters
        ----------
        entities:
            Entities to find cross-document relationships for.
        scope:
            Scope tag applied to all inferred edges.
        document_id:
            Optional document identifier for logging/provenance.

        Returns
        -------
        GraphBuildResult:
            The inferred edges and a count of edges added.
        """
        _min_entities = 2
        if len(entities) < _min_entities:
            return GraphBuildResult()

        # Build entity lookup
        entity_map = {e.id: e for e in entities}

        # Step 1: Find candidate cross-document pairs via embedding similarity
        pairs = self._find_candidate_pairs(entities, entity_map, scope)

        if not pairs:
            return GraphBuildResult()

        # Step 2: Batch pairs and run LLM inference
        batches = self._batch_pairs(pairs)

        all_edges: list[Edge] = []
        for batch in batches:
            prompt = self._format_prompt(batch, entity_map)
            try:
                result = await self._agent.run(prompt)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Inter-document graph inference failed for batch in scope %s",
                    scope,
                    exc_info=True,
                )
                continue

            stamped = self._stamp_edges(result.output.edges, batch, entity_map, scope)
            all_edges.extend(stamped)

        return GraphBuildResult(edges_added=len(all_edges), edges=all_edges)

    # -- internal ------------------------------------------------------------

    def _find_candidate_pairs(
        self,
        entities: list[Entity],
        entity_map: dict[str, Entity],  # noqa: ARG002
        scope: str,
    ) -> list[tuple[str, str]]:
        """Find cross-document entity pairs using embedding similarity."""
        seen_pairs: set[tuple[str, str]] = set()
        pairs: list[tuple[str, str]] = []

        for entity in entities:
            embedding = self._vector_store.get_embedding(entity.id)
            if embedding is None:
                continue

            candidates = self._vector_store.search_similar(
                embedding,
                top_k=self._top_k,
                embedding_type="entity",
                scopes=[scope],
            )

            for matched_id, score in candidates:
                # Skip if below cosine threshold
                if score < self._cosine_threshold:
                    continue

                # Skip if matched entity not in our working set
                matched_entity = self._graph_store.get_entity(matched_id)
                if matched_entity is None:
                    continue

                # Cross-doc filter: skip same-document entities
                if matched_entity.document_id == entity.document_id:
                    continue

                # Normalize pair order for deduplication
                pair = tuple(sorted([entity.id, matched_id]))
                if pair in seen_pairs:
                    continue

                # Check if inter-doc edge already exists
                if self._has_existing_inter_doc_edge(pair[0], pair[1]):
                    continue

                seen_pairs.add(pair)  # type: ignore[arg-type]
                pairs.append(pair)  # type: ignore[arg-type]

        return pairs

    def _has_existing_inter_doc_edge(self, entity_a: str, entity_b: str) -> bool:
        """Check if an inter-doc edge already exists between two entities."""
        edges = self._graph_store.list_edges(source_id=entity_a, target_id=entity_b)
        for edge in edges:
            if edge.metadata.get("source") == "inter_doc_inference":
                return True

        edges = self._graph_store.list_edges(source_id=entity_b, target_id=entity_a)
        return any(
            edge.metadata.get("source") == "inter_doc_inference" for edge in edges
        )

    @staticmethod
    def _batch_pairs(
        pairs: list[tuple[str, str]],
    ) -> list[list[tuple[str, str]]]:
        """Split pairs into batches of ~_BATCH_SIZE."""
        return [pairs[i : i + _BATCH_SIZE] for i in range(0, len(pairs), _BATCH_SIZE)]

    @staticmethod
    def _format_prompt(
        batch: list[tuple[str, str]],
        entity_map: dict[str, Entity],
    ) -> str:
        """Build a user prompt listing entity pairs for the LLM."""
        lines = [f"Entity pairs for cross-document relationship inference ({len(batch)} pairs):"]
        for source_id, target_id in batch:
            src = entity_map.get(source_id)
            tgt = entity_map.get(target_id)
            if src and tgt:
                lines.append(
                    f"- [{src.id}] {src.name} ({src.entity_type}): {src.description}"
                    f"  <-> [{tgt.id}] {tgt.name} ({tgt.entity_type}): {tgt.description}"
                )
        return "\n".join(lines)

    @staticmethod
    def _stamp_edges(
        edges: list[Edge],
        batch: list[tuple[str, str]],
        entity_map: dict[str, Entity],
        scope: str,
    ) -> list[Edge]:
        """Stamp all edges with weight=0.4, inter_doc metadata, and scope."""
        # Collect doc_ids for the batch to populate doc_pair metadata
        batch_doc_ids: set[str] = set()
        for src_id, tgt_id in batch:
            src = entity_map.get(src_id)
            tgt = entity_map.get(tgt_id)
            if src and src.document_id:
                batch_doc_ids.add(src.document_id)
            if tgt and tgt.document_id:
                batch_doc_ids.add(tgt.document_id)

        doc_pair = sorted(batch_doc_ids)

        return [
            Edge(
                id=edge.id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                relation=edge.relation,
                weight=0.4,
                metadata={
                    "source": "inter_doc_inference",
                    "doc_pair": doc_pair,
                },
                scope=scope,
            )
            for edge in edges
        ]
