"""DEFERRED: Inter-document graph builder — DI-based implementation.

This module is intentionally deferred and remains inactive until
StructuredExtractor integration is activated in the ingest lifecycle.

:class:`InterDocGraphBuilder` uses vector pre-filtering and canonical-name
blocking to find candidate entity pairs across documents, prioritises
cross-source pairs, deduplicates against existing graph edges, batches pairs
for LLM inference via an injected :class:`StructuredExtractor`, and stamps all
returned edges with ``weight=0.4``,
``metadata["source"]="inter_doc_inference"``,
``metadata["doc_pair"]=[doc_a_id, doc_b_id]``, and
``metadata["source_pair"]=[source_a_id, source_b_id]``. Edges are also
forced to the build scope and receive ``metadata["document_id"]`` from the
document pair so SQLite edge provenance remains non-null.
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

Corporate relation type guidance:
- **governs**: Use when a policy or standard entity governs (controls or constrains) another
  entity — e.g., a security policy governs a procedure.
- **supersedes_version**: Use when a document or standard supersedes a prior version of
  itself — e.g., Policy v2.0 supersedes_version Policy v1.0.

Return your findings as JSON matching the ExtractionResult schema. Leave the
entities list empty — only return edges.
"""


def _stamp_inter_edge(
    edge: Edge,
    entity_by_id: dict[str, Entity],
    source_by_entity: dict[str, str | None],
    scope: str,
) -> Edge:
    """Return a scoped edge stamped with inter-doc provenance."""
    ent_a = entity_by_id.get(edge.source_id)
    ent_b = entity_by_id.get(edge.target_id)
    doc_id_a = ent_a.document_id if ent_a is not None else None
    doc_id_b = ent_b.document_id if ent_b is not None else None
    src_a = source_by_entity.get(edge.source_id)
    src_b = source_by_entity.get(edge.target_id)
    doc_pair = sorted(d for d in [doc_id_a, doc_id_b] if isinstance(d, str))
    source_pair = sorted(s for s in [src_a, src_b] if isinstance(s, str))
    metadata = {
        **edge.metadata,
        "source": _INTER_SOURCE,
        "doc_pair": doc_pair,
        "source_pair": source_pair,
    }
    if doc_pair:
        metadata.setdefault("document_id", doc_pair[0])
    return edge.model_copy(
        update={
            "weight": _INTER_WEIGHT,
            "scope": scope,
            "metadata": metadata,
        }
    )


def _build_inter_prompt(pairs: list[tuple[Entity, Entity]], scope: str) -> str:
    pair_lines = []
    for a, b in pairs:
        a_desc = f" — {a.description}" if a.description else ""
        b_desc = f" — {b.description}" if b.description else ""
        pair_lines.append(
            f"  ({a.id} | {a.name} [{a.entity_type.value}]{a_desc}, {b.id} | {b.name} [{b.entity_type.value}]{b_desc})"
        )
    pairs_str = "\n".join(pair_lines)
    return f"scope: {scope}\nEntity pairs (entity_id | name [type]):\n{pairs_str}"


def _pair_key(source_id: str, target_id: str) -> tuple[str, str]:
    """Return an order-insensitive entity-pair key."""
    return (min(source_id, target_id), max(source_id, target_id))


def _candidate_pair_keys(pairs: list[tuple[Entity, Entity]]) -> set[tuple[str, str]]:
    """Return allowed endpoint pairs for an extractor batch."""
    return {_pair_key(source.id, target.id) for source, target in pairs}


def _filter_candidate_edges(edges: list[Edge], allowed_pairs: set[tuple[str, str]]) -> list[Edge]:
    """Drop extractor edges that do not match the prompted candidate pairs."""
    filtered: list[Edge] = []
    for edge in edges:
        if _pair_key(edge.source_id, edge.target_id) in allowed_pairs:
            filtered.append(edge)
        else:
            logger.debug(
                "dropping inter-doc edge outside candidate pairs: %s -> %s",
                edge.source_id,
                edge.target_id,
            )
    return filtered


class InterDocGraphBuilder:
    """DI-based inter-document graph builder.

    Discovers cross-document entity relationships by:

    1. Building a source map via ``graph_store.get_document`` to resolve
       each entity's ``source_id`` from its ``document_id``.
    2. Collecting candidates from two parallel paths:

       a. **Canonical-name blocking** — groups entities by
          ``Entity.canonical_name`` (lowercase, whitespace-collapsed,
          article/punct-stripped) and pairs those sharing the same canonical
          form across different documents.
       b. **Vector similarity** — calls ``vector_store.get_embedding`` +
          ``search_similar`` per entity and filters by cosine ≥ 0.70.

       Candidates from both paths are unioned (deduplicated).
    3. Prioritising cross-source candidate pairs (both source IDs known and
       distinct) before same-source cross-document pairs.
    4. Filtering out same-document pairs and pairs with existing edges.
    5. Batching remaining candidate pairs in groups of 40 and calling the
       injected ``extractor.extract`` once per batch.
    6. Stamping all returned edges with ``weight=0.4``,
       ``metadata["source"]="inter_doc_inference"``,
       ``metadata["doc_pair"]=[doc_a_id, doc_b_id]``, and
         ``metadata["source_pair"]=[source_a_id, source_b_id]``. The edge
         scope is forced to the build scope, and ``metadata["document_id"]``
         is set from the document pair for persistence provenance.
       Entity pairs where either source ID is unknown (``None``) are placed
       in the same-source bucket and receive a partial or empty
       ``source_pair``.

    Args:
        extractor: Injected :class:`StructuredExtractor` for LLM inference.
        vector_store: Backend satisfying :class:`VectorStoreProtocol`.
        graph_store: :class:`GraphStore` instance for edge deduplication
            and source-map resolution.
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
            entity.id: (None if entity.document_id is None else doc_to_source.get(entity.document_id))
            for entity in entities
        }

    def _canonical_candidates(
        self,
        entities: list[Entity],
        existing_pairs: set[tuple[str, str]],
    ) -> list[tuple[Entity, Entity]]:
        """Return cross-doc pairs sharing canonical_name (canonical-name blocking)."""
        groups: dict[str, list[Entity]] = {}
        for entity in entities:
            key = entity.canonical_name
            if key:
                groups.setdefault(key, []).append(entity)

        seen: set[tuple[str, str]] = set()
        result: list[tuple[Entity, Entity]] = []
        for group in groups.values():
            if len(group) < _MIN_ENTITIES:
                continue
            for i, a in enumerate(group):
                for b in group[i + 1 :]:
                    if a.document_id == b.document_id:
                        continue
                    if (a.id, b.id) in existing_pairs or (b.id, a.id) in existing_pairs:
                        continue
                    pair_key = (min(a.id, b.id), max(a.id, b.id))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        result.append((a, b))
        return result

    def _collect_candidates(
        self,
        entities: list[Entity],
        entity_by_id: dict[str, Entity],
        existing_pairs: set[tuple[str, str]],
        source_by_entity: dict[str, str | None] | None = None,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Entity]]:
        """Return cross-document candidate pairs, cross-source pairs first.

        Cross-source pairs (both entities have known, distinct source_ids) are
        prioritised over same-source cross-document pairs.  Entities with
        document_id=None or a resolved source_id=None are treated as unknown
        source and never promoted to the cross-source bucket.

        Canonical-name blocking adds cross-doc pairs sharing the same
        ``canonical_name`` even when vector similarity is below threshold
        (union semantics — canonical adds matches beyond vector results).
        """
        if source_by_entity is None:
            source_by_entity = {}

        canonical = self._canonical_candidates(entities, existing_pairs)
        seen: set[tuple[str, str]] = {(min(a.id, b.id), max(a.id, b.id)) for a, b in canonical}
        seen.update((min(source_id, target_id), max(source_id, target_id)) for source_id, target_id in existing_pairs)

        cross_source: list[tuple[Entity, Entity]] = []
        same_source: list[tuple[Entity, Entity]] = []
        for entity in entities:
            for other in self._vector_candidate_peers(entity, entity_by_id, seen, scopes):
                src_a = source_by_entity.get(entity.id)
                src_b = source_by_entity.get(other.id)
                if src_a is not None and src_b is not None and src_a != src_b:
                    cross_source.append((entity, other))
                else:
                    same_source.append((entity, other))

        return canonical + cross_source + same_source

    def _vector_candidate_peers(
        self,
        entity: Entity,
        entity_by_id: dict[str, Entity],
        seen: set[tuple[str, str]],
        scopes: list[str] | None,
    ) -> list[Entity]:
        """Return vector-similar peers for one entity, skipping missing embeddings."""
        embedding = self._vector_store.get_embedding(entity.id)
        if embedding is None:
            return []

        similar = self._vector_store.search_similar(
            embedding,
            top_k=self._top_k,
            embedding_type="entity",
            scopes=scopes,
        )
        peers: list[Entity] = []
        for sim_id, score in similar:
            peer = self._valid_vector_peer(entity, sim_id, score, entity_by_id, seen)
            if peer is not None:
                peers.append(peer)
        return peers

    def _valid_vector_peer(
        self,
        entity: Entity,
        sim_id: str,
        score: float,
        entity_by_id: dict[str, Entity],
        seen: set[tuple[str, str]],
    ) -> Entity | None:
        """Validate and mark one vector candidate peer."""
        if score < self._cosine_threshold or sim_id not in entity_by_id:
            return None
        other = entity_by_id[sim_id]
        if entity.document_id == other.document_id:
            return None
        pair_key = (min(entity.id, other.id), max(entity.id, other.id))
        if pair_key in seen:
            return None
        seen.add(pair_key)
        return other

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
        existing_edges = self._graph_store.list_edges(scopes=[scope])
        existing_pairs: set[tuple[str, str]] = set()
        for e in existing_edges:
            existing_pairs.add((e.source_id, e.target_id))
            existing_pairs.add((e.target_id, e.source_id))

        entity_by_id: dict[str, Entity] = {e.id: e for e in entities}
        source_by_entity = self._build_source_map(entities)
        candidate_pairs = self._collect_candidates(
            entities,
            entity_by_id,
            existing_pairs,
            source_by_entity,
            scopes=[scope],
        )

        if not candidate_pairs:
            return GraphBuildResult()

        # Batch candidate pairs and call extractor once per batch.
        all_edges: list[Edge] = []
        for i in range(0, len(candidate_pairs), _INTER_BATCH_SIZE):
            batch = candidate_pairs[i : i + _INTER_BATCH_SIZE]
            prompt = _build_inter_prompt(batch, scope)
            result = await self._extractor.extract(prompt)
            all_edges.extend(_filter_candidate_edges(result.edges, _candidate_pair_keys(batch)))

        stamped = [_stamp_inter_edge(e, entity_by_id, source_by_entity, scope) for e in all_edges]
        return GraphBuildResult(edges=stamped, edges_added=len(stamped))
