"""Query facade implementation for combined content and graph search."""

from __future__ import annotations

from owlbear_knowledge.protocols.content import ContentSearchQuery, ContentSearchResult, ContentStore
from owlbear_knowledge.protocols.graph import EdgeRecord, EntityRecord, GraphStore, TraversalQuery, TraversalResult
from owlbear_knowledge.protocols.query import Provenance, QueryRequest, QueryResult


class QueryFacade:
    """Read-only facade combining Content and Graph query capabilities."""

    def __init__(self, *, content: ContentStore, graph: GraphStore) -> None:
        self._content = content
        self._graph = graph

    async def search(self, request: QueryRequest) -> QueryResult:
        """Run content search and optionally expand results with graph context."""
        if not request.text.strip():
            msg = "request.text must not be empty"
            raise ValueError(msg)

        content_query = ContentSearchQuery(
            text=request.text,
            top_k=request.top_k,
            scopes=request.scopes,
            source_ids=request.source_ids,
            min_score=request.min_score,
        )
        search_results = await self._content.search(content_query)

        graph_context = self._build_graph_context(request=request, search_results=search_results)
        provenance = self._build_provenance(search_results)

        return QueryResult(
            search_results=search_results,
            graph_context=graph_context,
            provenance=provenance,
        )

    def _build_graph_context(
        self,
        *,
        request: QueryRequest,
        search_results: tuple[ContentSearchResult, ...],
    ) -> TraversalResult | None:
        if not request.include_graph or not search_results:
            return None

        seed_ids = self._collect_seed_entity_ids(search_results)
        if not seed_ids:
            return None

        merged = self._traverse_and_merge(
            seed_ids=seed_ids,
            max_hops=request.graph_hops,
            relation_types=request.relation_types,
        )
        if merged is None:
            return None

        if not request.entity_types:
            return merged
        return self._filter_by_entity_types(merged, request.entity_types)

    def _collect_seed_entity_ids(self, search_results: tuple[ContentSearchResult, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for result in search_results:
            claims = self._graph.claims_for_chunk(result.chunk.id)
            for entity_id in claims.entity_ids:
                if entity_id in seen:
                    continue
                seen.add(entity_id)
                ordered.append(entity_id)
        return tuple(ordered)

    def _traverse_and_merge(
        self,
        *,
        seed_ids: tuple[str, ...],
        max_hops: int,
        relation_types: tuple,
    ) -> TraversalResult | None:
        entities_by_id: dict[str, EntityRecord] = {}
        edges_by_id: dict[str, EdgeRecord] = {}

        for seed_id in seed_ids:
            query = TraversalQuery(
                entity_id=seed_id,
                max_hops=max_hops,
                relation_types=relation_types,
            )
            try:
                traversal = self._graph.traverse(query)
            except LookupError:
                continue

            for entity in traversal.entities:
                entities_by_id[entity.id] = entity
            for edge in traversal.edges:
                edges_by_id[edge.id] = edge

        if not entities_by_id and not edges_by_id:
            return None

        return TraversalResult(
            entities=tuple(entities_by_id.values()),
            edges=tuple(edges_by_id.values()),
        )

    def _filter_by_entity_types(
        self,
        traversal: TraversalResult,
        requested_types: tuple,
    ) -> TraversalResult:
        allowed_types = set(requested_types)
        entities = tuple(entity for entity in traversal.entities if entity.entity_type in allowed_types)
        allowed_entity_ids = {entity.id for entity in entities}
        edges = tuple(
            edge
            for edge in traversal.edges
            if edge.source_entity_id in allowed_entity_ids and edge.target_entity_id in allowed_entity_ids
        )
        return TraversalResult(entities=entities, edges=edges)

    def _build_provenance(self, search_results: tuple[ContentSearchResult, ...]) -> tuple[Provenance, ...]:
        provenance: list[Provenance] = []
        for result in search_results:
            chunk = result.chunk
            document = self._content.get_document(chunk.document_id)
            title = document.title if document is not None else ""
            provenance.append(
                Provenance(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    source_id=chunk.source_id,
                    title=title,
                    uri=chunk.uri,
                    exact_text=chunk.text,
                    section_path=chunk.section_path,
                    score=result.score,
                )
            )
        return tuple(provenance)
