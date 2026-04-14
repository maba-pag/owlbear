"""Inter-document graph builder — DI-based implementation.

:class:`InterDocGraphBuilder` uses vector pre-filtering to find candidate
entity pairs across documents, deduplicates against existing graph edges,
batches pairs for LLM inference via an injected :class:`StructuredExtractor`,
and stamps all returned edges with ``weight=0.4`` and
``metadata["source"]="inter_doc_inference"``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from owlbear_knowledge.graph_builder import GraphBuildResult

if TYPE_CHECKING:
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.models import Edge, Entity
    from owlbear_knowledge.protocol import StructuredExtractor, VectorStoreProtocol

logger = logging.getLogger(__name__)

_INTER_BATCH_SIZE = 40
_INTER_WEIGHT = 0.4
_INTER_SOURCE = "inter_doc_inference"
_MIN_ENTITIES = 2
_DEFAULT_TOP_K = 10
_DEFAULT_COSINE_THRESHOLD = 0.70

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


def _stamp_inter_edge(
    edge: Edge,
    entity_by_id: dict[str, Entity],
    source_by_entity: dict[str, str | None],
) -> Edge:
    """Return a copy of *edge* stamped with inter-doc weight, source, doc_pair, and source_pair."""
    ent_a = entity_by_id.get(edge.source_id)
    ent_b = entity_by_id.get(edge.target_id)
    doc_id_a = ent_a.document_id if ent_a is not None else None
    doc_id_b = ent_b.document_id if ent_b is not None else None
    src_a = source_by_entity.get(edge.source_id)
    src_b = source_by_entity.get(edge.target_id)
    doc_pair = sorted(d for d in [doc_id_a, doc_id_b] if isinstance(d, str))
    source_pair = sorted(s for s in [src_a, src_b] if isinstance(s, str))
    return edge.model_copy(update={
        "weight": _INTER_WEIGHT,
        "metadata": {
            **edge.metadata,
            "source": _INTER_SOURCE,
            "doc_pair": doc_pair,
            "source_pair": source_pair,
        },
    })


def _build_inter_prompt(pairs: list[tuple[Entity, Entity]], scope: str) -> str:
    pair_strs = ", ".join(f"({a.name}, {b.name})" for a, b in pairs)
    return f"scope: {scope}\nEntity pairs: {pair_strs}"


class InterDocGraphBuilder:
    """DI-based inter-document graph builder.

    Discovers cross-document entity relationships by:

    1. Calling ``vector_store.get_embedding`` + ``search_similar`` per entity
       to find candidate similar entities across documents.
    2. Filtering out same-document pairs and pairs with existing edges.
    3. Batching remaining candidate pairs in groups of 40 and calling the
       injected ``extractor.extract`` once per batch.
    4. Stamping all returned edges with ``weight=0.4`` and
       ``metadata["source"]="inter_doc_inference"``.

    Args:
        extractor: Injected :class:`StructuredExtractor` for LLM inference.
        vector_store: Backend satisfying :class:`VectorStoreProtocol`.
        graph_store: :class:`GraphStore` instance for edge deduplication.
    """

    def __init__(
        self,
        extractor: StructuredExtractor,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        top_k: int = _DEFAULT_TOP_K,
        cosine_threshold: float = _DEFAULT_COSINE_THRESHOLD,
    ) -> None:
        self._extractor = extractor
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._top_k = top_k
        self._cosine_threshold = cosine_threshold

    def _build_source_map(self, entities: list[Entity]) -> dict[str, str | None]:
        """Return entity_id → source_id by consulting graph_store.get_document().

        Calls get_document for every unique non-None document_id in *entities*.
        Entities with document_id=None map to None (unknown source).
        Orphaned document_ids (get_document returns None) also map to None.
        """
        unique_doc_ids = {e.document_id for e in entities if e.document_id is not None}
        doc_to_source: dict[str, str | None] = {}
        for doc_id in unique_doc_ids:
            doc = self._graph_store.get_document(doc_id)
            doc_to_source[doc_id] = doc.source_id if doc is not None else None
        return {
            entity.id: (
                None if entity.document_id is None else doc_to_source.get(entity.document_id)
            )
            for entity in entities
        }

    def _collect_candidates(
        self,
        entities: list[Entity],
        entity_by_id: dict[str, Entity],
        existing_pairs: set[tuple[str, str]],
        source_by_entity: dict[str, str | None],
    ) -> list[tuple[Entity, Entity]]:
        """Return cross-document candidate pairs, cross-source pairs first.

        Cross-source pairs (both entities have known, distinct source_ids) are
        prioritised over same-source cross-document pairs.  Entities with
        document_id=None or a resolved source_id=None are treated as unknown
        source and never promoted to the cross-source bucket.
        """
        cross_source: list[tuple[Entity, Entity]] = []
        same_source: list[tuple[Entity, Entity]] = []
        for entity in entities:
            embedding = self._vector_store.get_embedding(entity.id)
            similar = self._vector_store.search_similar(embedding, top_k=self._top_k)
            for sim_id, score in similar:
                if score < self._cosine_threshold:
                    continue
                if sim_id not in entity_by_id:
                    continue
                other = entity_by_id[sim_id]
                if entity.document_id == other.document_id:
                    continue
                if (entity.id, other.id) in existing_pairs:
                    continue
                src_a = source_by_entity.get(entity.id)
                src_b = source_by_entity.get(other.id)
                if src_a is not None and src_b is not None and src_a != src_b:
                    cross_source.append((entity, other))
                else:
                    same_source.append((entity, other))
        return cross_source + same_source

    async def build(
        self,
        entities: list[Entity],
        scope: str = "global",
    ) -> GraphBuildResult:
        """Infer inter-document edges for *entities*.

        Returns empty :class:`GraphBuildResult` when fewer than 2 entities
        are provided.
        """
        if len(entities) < _MIN_ENTITIES:
            return GraphBuildResult()

        # Fetch existing edges once for deduplication.
        existing_edges = self._graph_store.list_edges()
        existing_pairs: set[tuple[str, str]] = set()
        for e in existing_edges:
            existing_pairs.add((e.source_id, e.target_id))
            existing_pairs.add((e.target_id, e.source_id))

        entity_by_id: dict[str, Entity] = {e.id: e for e in entities}
        source_by_entity = self._build_source_map(entities)
        candidate_pairs = self._collect_candidates(entities, entity_by_id, existing_pairs, source_by_entity)

        if not candidate_pairs:
            return GraphBuildResult()

        # Batch candidate pairs and call extractor once per batch.
        all_edges: list[Edge] = []
        for i in range(0, len(candidate_pairs), _INTER_BATCH_SIZE):
            batch = candidate_pairs[i : i + _INTER_BATCH_SIZE]
            prompt = _build_inter_prompt(batch, scope)
            result = await self._extractor.extract(prompt)
            all_edges.extend(result.edges)

        stamped = [_stamp_inter_edge(e, entity_by_id, source_by_entity) for e in all_edges]
        return GraphBuildResult(edges=stamped, edges_added=len(stamped))
