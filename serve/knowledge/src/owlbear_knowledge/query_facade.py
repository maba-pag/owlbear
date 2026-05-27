"""Query facade implementation for combined content and graph search."""

from __future__ import annotations

from owlbear_knowledge.protocols.content import ContentChunk, ContentSearchQuery, ContentSearchResult, ContentStore
from owlbear_knowledge.protocols.graph import (
    EdgeRecord,
    EntityQuery,
    EntityRecord,
    GraphStore,
    TraversalQuery,
    TraversalResult,
)
from owlbear_knowledge.protocols.query import (
    ContextRenderRequest,
    EntityLookupRequest,
    EntityLookupResult,
    Provenance,
    QueryRequest,
    QueryResult,
    RenderedContext,
)


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

    def lookup_entity(self, request: EntityLookupRequest) -> EntityLookupResult:
        """Look up an entity by ID or name and optionally expand neighbours."""
        entity = self._resolve_entity(request)
        if entity is None:
            if request.entity_id:
                msg = f"entity_id not found: {request.entity_id}"
            else:
                msg = f"entity_name not found: {request.entity_name}"
            raise LookupError(msg)

        neighbourhood: TraversalResult | None = None
        if request.expand_hops > 0:
            neighbourhood = self._graph.traverse(
                TraversalQuery(
                    entity_id=entity.id,
                    max_hops=request.expand_hops,
                    relation_types=request.relation_types,
                )
            )

        related_chunks = self._load_related_chunks(entity.id)
        return EntityLookupResult(
            entity=entity,
            neighbourhood=neighbourhood,
            related_chunks=related_chunks,
        )

    def render_context(self, request: ContextRenderRequest) -> RenderedContext:
        """Render query/entity results into a prompt-friendly text block."""
        if request.query_result is None and request.entity_result is None:
            msg = "Provide at least one of query_result or entity_result"
            raise ValueError(msg)

        lines: list[str] = []
        entity_ids: set[str] = set()
        chunk_count = 0

        if request.query_result is not None:
            query_lines, query_entity_ids, query_chunks = self._render_query_result(
                request.query_result,
                include_provenance=request.include_provenance,
            )
            lines.extend(query_lines)
            entity_ids.update(query_entity_ids)
            chunk_count += query_chunks

        if request.entity_result is not None:
            entity_lines, lookup_entity_ids, lookup_chunks = self._render_entity_result(
                request.entity_result,
                include_provenance=request.include_provenance,
            )
            lines.extend(entity_lines)
            entity_ids.update(lookup_entity_ids)
            chunk_count += lookup_chunks

        text = "\n".join(lines).strip()
        if not text:
            text = "(no context)"

        truncated = len(text) > request.max_chars
        if truncated:
            text = text[: request.max_chars]

        return RenderedContext(
            text=text,
            char_count=len(text),
            chunk_count=chunk_count,
            entity_count=len(entity_ids),
            truncated=truncated,
        )

    def _resolve_entity(self, request: EntityLookupRequest) -> EntityRecord | None:
        if request.entity_id is not None:
            return self._graph.get_entity(request.entity_id)

        matches = self._graph.find_entities(
            EntityQuery(
                name=request.entity_name,
                entity_type=request.entity_type,
            )
        )
        return matches[0] if matches else None

    def _load_related_chunks(self, entity_id: str) -> tuple[ContentChunk, ...]:
        return tuple(
            chunk
            for chunk_id in self._graph.chunk_ids_for_entity(entity_id)
            if (chunk := self._content.get_chunk(chunk_id)) is not None
        )

    def _render_query_result(
        self,
        query_result: QueryResult,
        *,
        include_provenance: bool,
    ) -> tuple[list[str], set[str], int]:
        lines = ["## Search Results"]
        entity_ids: set[str] = set()
        chunk_count = 0

        if query_result.search_results:
            for index, result in enumerate(query_result.search_results, start=1):
                lines.append(f"- [{index}] {result.chunk.text}")
                chunk_count += 1
        else:
            lines.append("- None")

        if query_result.graph_context is not None:
            lines.append("## Graph Context")
            for entity in query_result.graph_context.entities:
                entity_ids.add(entity.id)
                lines.append(f"- {entity.name} ({entity.entity_type})")

        if include_provenance and query_result.provenance:
            lines.append("## Sources")
            lines.extend(
                f"- {provenance.source_id} :: {provenance.title} (chunk={provenance.chunk_id})"
                for provenance in query_result.provenance
            )

        return lines, entity_ids, chunk_count

    def _render_entity_result(
        self,
        entity_result: EntityLookupResult,
        *,
        include_provenance: bool,
    ) -> tuple[list[str], set[str], int]:
        lines = ["## Entity Lookup"]
        entity_ids: set[str] = set()
        chunk_count = 0

        entity = entity_result.entity
        if entity is not None:
            entity_ids.add(entity.id)
            lines.append(f"- Entity: {entity.name} ({entity.entity_type}) id={entity.id}")

        if entity_result.neighbourhood is not None:
            lines.append("### Neighbourhood")
            for neighbour in entity_result.neighbourhood.entities:
                entity_ids.add(neighbour.id)
                lines.append(f"- {neighbour.name} ({neighbour.entity_type})")

        if entity_result.related_chunks:
            lines.append("### Related Chunks")
            if include_provenance:
                lines.extend(f"- [{chunk.source_id}] {chunk.text}" for chunk in entity_result.related_chunks)
            else:
                lines.extend(f"- {chunk.text}" for chunk in entity_result.related_chunks)
            chunk_count = len(entity_result.related_chunks)

        return lines, entity_ids, chunk_count

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
