"""MCPServer application for knowledge ingestion and search tools."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Context  # noqa: TC002 - MCPServer evaluates tool annotations at registration.
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider, EmbeddingProvider
from owlbear_knowledge.fetcher import HttpResponseFetcher, HttpxContentFetcher
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.common import (
    EntityType as ProtocolEntityType,
)
from owlbear_knowledge.protocols.common import (
    RelationType as ProtocolRelationType,
)
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentParams,
    ExtractedEntity,
    ExtractedRelation,
)
from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeOperationError
from owlbear_knowledge.protocols.ingest import IngestDocument, IngestRequest, RefreshError, RefreshRequest
from owlbear_knowledge.protocols.query import EntityLookupRequest, QueryRequest, QueryResult
from owlbear_knowledge.protocols.sources import (
    FetchTransport,
    InlineConfig,
    SourceKind,
    SourceRegistration,
    SourceState,
)
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_facade import QueryFacade
from owlbear_knowledge.source_fetcher import CompositeSourceFetcher
from owlbear_knowledge.stores.content import ContentStore
from owlbear_knowledge.stores.enrichment import EnrichmentStore
from owlbear_knowledge.stores.graph import SqliteGraphStore
from owlbear_knowledge.stores.sources import SqliteSourceStore

from ._helpers import (
    _normalize_batch_limit,
    _normalize_enrichment_items,
    _normalize_optional_scope,
    _normalize_read_limit,
    _normalize_scope_list,
    _sanitize_error,
    _serialize_graph_context,
    _serialize_related_sources,
    _serialize_search_entities,
    _serialize_source,
    select_content_fetcher,
)
from ._types import (
    _DEFAULT_KB_PATH,
    _DEFAULT_QDRANT_PATH,
    _MAX_ENRICHMENT_BATCH_SIZE,
    EnrichmentChunk,
    RetryEnrichmentResult,
    SearchResult,
    SourceInfo,
    StatsResult,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

logger = logging.getLogger(__name__)
_WORKSPACE_MARKER = Path(".owlbear")


async def claim_enrichment_batch(ctx: Context, limit: int = 10) -> list[EnrichmentChunk]:
    """Atomically claim a batch of chunks ready for enrichment.

    Chunks are eligible when state is pending, or when a previous claim lease
    is stale (>10 minutes). Chunks from sources with enrich=0 are excluded.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    limit = _normalize_batch_limit(limit)
    batch = app_ctx.enrichment_store.claim_batch(EnrichmentParams(batch_size=limit))

    doc_titles: dict[str, str] = {}
    source_names: dict[str, str] = {}
    response: list[EnrichmentChunk] = []

    for item in batch.items:
        chunk = app_ctx.content_store.get_chunk(item.chunk_id)
        if chunk is None:
            continue

        document_id = chunk.document_id
        source_id = item.source_id

        if document_id not in doc_titles:
            document = app_ctx.content_store.get_document(document_id)
            title = getattr(document, "title", "")
            doc_titles[document_id] = title if isinstance(title, str) else ""

        if source_id not in source_names:
            source = app_ctx.source_store_v2.get_source(source_id)
            name = getattr(source, "name", "")
            source_names[source_id] = name if isinstance(name, str) else ""

        section_parts = getattr(chunk, "section_path", None)
        section_path = "/".join(section_parts) if section_parts else None

        scope = getattr(chunk, "scope", None)
        claimed_at = (
            item.started_at.isoformat() if isinstance(item.started_at, datetime) else datetime.now(tz=UTC).isoformat()
        )

        response.append(
            {
                "chunk_id": item.chunk_id,
                "text": chunk.text,
                "doc_title": doc_titles[document_id],
                "section_path": section_path,
                "source_name": source_names[source_id],
                "document_id": document_id,
                "source_id": source_id,
                "scope": scope if isinstance(scope, str) and scope else "global",
                "claim_token": batch.batch_id,
                "claimed_at": claimed_at,
            }
        )

    return response


async def store_enrichment(
    ctx: Context,
    chunk_id: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    claim_token: str | None = None,
) -> None:
    """Persist enrichment results for a chunk."""
    app_ctx: AppContext = ctx.request_context.lifespan_context

    _ = claim_token

    if chunk_id is None:
        msg = "chunk_id is required"
        raise ToolError(msg)

    enrichment_store = app_ctx.enrichment_store
    if enrichment_store is None:
        msg = "enrichment store not available"
        raise ToolError(msg)

    entity_rows = _normalize_enrichment_items(entities, field_name="entities")
    edge_rows = _normalize_enrichment_items(edges, field_name="edges")

    try:
        parsed_entities = tuple(_parse_extracted_entity(item) for item in entity_rows)
        parsed_relations = tuple(_parse_extracted_relation(item) for item in edge_rows)
    except (ToolError, ValidationError, ValueError, TypeError, KeyError) as exc:
        error_str = str(exc)
        try:
            enrichment_store.mark_failed(chunk_id, error_str)
        except LookupError:
            logger.debug("chunk %s was not in progress during parse failure mark", chunk_id)
        raise ToolError(error_str) from exc

    try:
        enrichment_store.submit_extractions(chunk_id, parsed_entities, parsed_relations)
    except ValueError as exc:
        error_str = str(exc)
        try:
            enrichment_store.mark_failed(chunk_id, error_str)
        except LookupError:
            logger.debug(
                "chunk %s was not in progress during submit_extractions value error mark",
                chunk_id,
            )
        raise ToolError(error_str) from exc
    except LookupError as exc:
        raise ToolError(str(exc)) from exc


def _parse_extracted_entity(entity: dict[str, Any]) -> ExtractedEntity:
    """Map a phase-1 entity payload into ExtractedEntity for submit_extractions."""
    local_ref_raw = entity.get("id")
    if not isinstance(local_ref_raw, str) or not local_ref_raw.strip():
        msg = "entity id is required"
        raise ValueError(msg)

    name_raw = entity.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        msg = "entity name is required"
        raise ValueError(msg)

    entity_type = _parse_protocol_entity_type(entity)
    description_raw = entity.get("description", "")
    if not isinstance(description_raw, str):
        msg = "entity description must be a string"
        raise TypeError(msg)

    metadata_raw = entity.get("metadata", {})
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    confidence_raw = entity.get("confidence", 1.0)
    confidence = float(confidence_raw)

    return ExtractedEntity(
        local_ref=local_ref_raw.strip(),
        name=name_raw.strip(),
        entity_type=entity_type,
        description=description_raw,
        confidence=confidence,
        metadata=metadata,
    )


def _parse_protocol_entity_type(entity: dict[str, Any]) -> ProtocolEntityType:
    """Validate entity_type against the protocol enum used by ExtractedEntity."""
    raw = entity.get("entity_type")
    if not isinstance(raw, str) or not raw.strip():
        alias_raw = entity.get("type")
        raw = alias_raw if isinstance(alias_raw, str) else ""
    if not isinstance(raw, str) or not raw.strip():
        return ProtocolEntityType.CONCEPT

    value = raw.strip().lower()
    try:
        return ProtocolEntityType(value)
    except ValueError as exc:
        valid = ", ".join(item.value for item in ProtocolEntityType)
        msg = f"unsupported entity_type {value!r}; valid values: {valid}"
        raise ValueError(msg) from exc


def _parse_extracted_relation(edge: dict[str, Any]) -> ExtractedRelation:
    """Map a phase-1 edge payload into ExtractedRelation for submit_extractions."""
    source_ref_raw = edge.get("source_id")
    if not isinstance(source_ref_raw, str) or not source_ref_raw.strip():
        msg = "edge source_id is required"
        raise ValueError(msg)

    target_ref_raw = edge.get("target_id")
    if not isinstance(target_ref_raw, str) or not target_ref_raw.strip():
        msg = "edge target_id is required"
        raise ValueError(msg)

    relation_type = _parse_protocol_relation_type(edge)
    metadata_raw = edge.get("metadata", {})
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    weight_raw = edge.get("weight", 1.0)
    confidence_raw = edge.get("confidence", 1.0)

    return ExtractedRelation(
        source_ref=source_ref_raw.strip(),
        target_ref=target_ref_raw.strip(),
        relation_type=relation_type,
        weight=float(weight_raw),
        confidence=float(confidence_raw),
        metadata=metadata,
    )


def _parse_protocol_relation_type(edge: dict[str, Any]) -> ProtocolRelationType:
    """Validate relation/relationship against the protocol enum used by ExtractedRelation."""
    raw = edge.get("relation")
    if not isinstance(raw, str) or not raw.strip():
        alias_raw = edge.get("relationship")
        raw = alias_raw if isinstance(alias_raw, str) else ""
    if not isinstance(raw, str) or not raw.strip():
        msg = "edge relation is required (use 'relation' or 'relationship')"
        raise ValueError(msg)

    value = raw.strip().lower()
    try:
        return ProtocolRelationType(value)
    except ValueError as exc:
        valid = ", ".join(item.value for item in ProtocolRelationType)
        msg = f"unsupported edge relation {value!r}; valid values: {valid}"
        raise ValueError(msg) from exc


async def retry_enrichment(
    ctx: Context,
    chunk_ids: list[str] | None = None,
    limit: int = 100,
    scopes: list[str] | None = None,
) -> RetryEnrichmentResult:
    """Reset failed enrichment chunks to pending so workers can retry them."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    enrichment_store = app_ctx.enrichment_store
    if enrichment_store is None:
        msg = "enrichment store not available"
        raise ToolError(msg)

    scope_values = _normalize_scope_list(scopes)
    normalized_chunk_ids = tuple(chunk_id.strip() for chunk_id in chunk_ids or [] if chunk_id.strip())
    normalized_limit = _normalize_batch_limit(limit)
    result = enrichment_store.reset_failed(
        chunk_ids=normalized_chunk_ids or None,
        limit=normalized_limit,
        scopes=tuple(scope_values) if scope_values else None,
    )
    return {"reset": result.reset, "remaining_failed": result.remaining_failed}


@dataclass(slots=True)
class AppContext:
    """Runtime context passed to MCP tools via MCPServer lifespan."""

    conn: sqlite3.Connection
    query_facade: QueryFacade | None = None
    graph_store_v2: SqliteGraphStore | None = None
    content_store: ContentStore | None = None
    enrichment_store: EnrichmentStore | None = None
    source_store_v2: SqliteSourceStore | None = None
    ingest_coordinator: IngestCoordinator | None = None
    vector_store: object | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeRuntimeFactories:
    """Factories for runtime dependencies below the Knowledge composition root."""

    http_response_fetcher_factory: Callable[[], HttpResponseFetcher]
    embedding_provider_factory: Callable[[], EmbeddingProvider]
    vector_store_factory: Callable[[str], object]


def build_app_context(
    *,
    workspace_root: Path,
    conn: sqlite3.Connection,
    factories: KnowledgeRuntimeFactories,
) -> AppContext:
    """Assemble the Knowledge service graph for production or deterministic tests."""
    vector_store = factories.vector_store_factory(str(workspace_root / _DEFAULT_QDRANT_PATH))
    source_store_v2 = SqliteSourceStore(conn)
    graph_store_v2 = SqliteGraphStore(conn)
    content_store = ContentStore(
        db=conn,
        vector_store=vector_store,
        embedding_provider=factories.embedding_provider_factory(),
        chunker=TextChunker(),
    )
    query_facade = QueryFacade(content=content_store, graph=graph_store_v2)
    enrichment_store = EnrichmentStore(db=conn, graph=graph_store_v2)
    source_fetcher = CompositeSourceFetcher(
        workspace_root=workspace_root,
        content_fetcher_factory=select_content_fetcher,
        http_response_fetcher_factory=factories.http_response_fetcher_factory,
    )
    ingest_coordinator = IngestCoordinator(
        sources=source_store_v2,
        content=content_store,
        enrichment=enrichment_store,
        graph=graph_store_v2,
        fetcher=source_fetcher,
    )
    source_store_v2.ensure_tables()
    graph_store_v2.ensure_tables()
    content_store.ensure_tables()
    enrichment_store.ensure_tables()
    return AppContext(
        conn=conn,
        query_facade=query_facade,
        graph_store_v2=graph_store_v2,
        vector_store=vector_store,
        content_store=content_store,
        enrichment_store=enrichment_store,
        source_store_v2=source_store_v2,
        ingest_coordinator=ingest_coordinator,
    )


class RegisteredSourceResult(TypedDict):
    """Serialized source fields returned by knowledge_register_source."""

    id: str
    name: str
    state: str
    kind: str
    scope: str


class KnowledgeFailureResult(TypedDict):
    """Redacted failure fields returned by Knowledge MCP tools."""

    stage: str
    code: str
    retryable: bool
    message: str


class RefreshErrorResult(KnowledgeFailureResult):
    """A redacted refresh failure with source context."""

    source_id: str
    timestamp: str


class RefreshToolResult(TypedDict):
    """Refresh counts and structured per-source failures."""

    source_id: str
    sources_refreshed: int
    documents_created: int
    documents_replaced: int
    documents_unchanged: int
    chunks_created: int
    chunks_replaced: int
    errors: list[RefreshErrorResult]


def _serialize_knowledge_failure(failure: KnowledgeFailure) -> KnowledgeFailureResult:
    """Project a core failure without reclassifying or exposing exception text."""
    return {
        "stage": failure.stage.value,
        "code": failure.code,
        "retryable": failure.retryable,
        "message": failure.message,
    }


def _serialize_refresh_error(error: RefreshError) -> RefreshErrorResult:
    """Add refresh context to a typed core failure."""
    failure = error.failure
    if failure is None:
        msg = "refresh result contained an untyped failure"
        raise ToolError(msg)
    return {
        **_serialize_knowledge_failure(failure),
        "source_id": error.source_id,
        "timestamp": error.timestamp.isoformat(),
    }


@asynccontextmanager
async def app_lifespan(_server: MCPServer) -> AsyncGenerator[AppContext]:
    """Initialise knowledge-base services; close the DB connection on exit."""
    workspace_root = Path.cwd().resolve()
    if not (workspace_root / _WORKSPACE_MARKER).is_dir():
        message = f"OwlBear workspace marker not found: {_WORKSPACE_MARKER}"
        raise RuntimeError(message)
    db_path = workspace_root / _DEFAULT_KB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        ctx = build_app_context(
            workspace_root=workspace_root,
            conn=conn,
            factories=KnowledgeRuntimeFactories(
                http_response_fetcher_factory=HttpxContentFetcher,
                embedding_provider_factory=BgeM3EmbeddingProvider,
                vector_store_factory=lambda location: QdrantVectorStore(location=location),
            ),
        )
        yield ctx
    finally:
        conn.close()


mcp = MCPServer("owlbear-knowledge", lifespan=app_lifespan)

claim_enrichment_batch = mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))(
    claim_enrichment_batch
)
store_enrichment = mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))(store_enrichment)
retry_enrichment = mcp.tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)
)(retry_enrichment)


__all__ = [
    "_MAX_ENRICHMENT_BATCH_SIZE",
    "AppContext",
    "KnowledgeFailureResult",
    "RefreshErrorResult",
    "RefreshToolResult",
    "app_lifespan",
    "claim_enrichment_batch",
    "delete_knowledge_source",
    "knowledge_ingest",
    "knowledge_search",
    "knowledge_stats",
    "list_knowledge_sources",
    "lookup_knowledge_entity",
    "mcp",
    "refresh_knowledge_source",
    "register_knowledge_source",
    "retry_enrichment",
    "select_content_fetcher",
    "store_enrichment",
]


def _serialize_query_facade_results(app_ctx: AppContext, result: QueryResult) -> list[SearchResult]:
    """Serialize QueryFacade.search output into SearchResult items."""
    graph_entities = []
    graph_context = result.graph_context
    if graph_context is not None:
        graph_entities = [
            {
                "name": str(getattr(entity, "name", "")),
                "type": str(getattr(entity, "entity_type", "")),
            }
            for entity in getattr(graph_context, "entities", ())
        ]
    serialized_entities = _serialize_search_entities(graph_entities)

    graph_context_text = ""
    if graph_context is not None:
        entity_count = len(getattr(graph_context, "entities", ()))
        edge_count = len(getattr(graph_context, "edges", ()))
        graph_context_text = f"graph expansion: {entity_count} entities, {edge_count} edges"

    retrieval_path = "vector+graph" if graph_context is not None else "vector"
    provenance_by_chunk = {item.chunk_id: item for item in result.provenance}

    serialized: list[SearchResult] = []
    for item in result.search_results:
        chunk = item.chunk
        provenance = provenance_by_chunk.get(chunk.id)
        title = provenance.title if provenance is not None else ""

        source_name = provenance.source_id if provenance is not None else ""
        source_obj: object = SimpleNamespace(name=source_name, url="")
        if provenance is not None:
            source_store_v2 = getattr(app_ctx, "source_store_v2", None)
            if source_store_v2 is not None:
                source_record = source_store_v2.get_source(provenance.source_id)
                if source_record is not None:
                    source_obj = source_record
            if isinstance(source_obj, SimpleNamespace):
                source_obj.url = provenance.uri or ""

        related_candidates = [
            {
                "name": (other.title or other.source_id),
                "relationship": "related",
                "entity": serialized_entities[0]["name"] if serialized_entities else "",
            }
            for other in result.provenance
            if other.chunk_id != chunk.id and (other.title or other.source_id)
        ]

        serialized.append(
            {
                "title": title,
                "score": item.score,
                "snippet": chunk.text,
                "entity_type": None,
                "retrieval_path": retrieval_path,
                "graph_context": _serialize_graph_context(graph_context_text),
                "entities": serialized_entities,
                "related_sources": _serialize_related_sources(related_candidates),
                "source": _serialize_source(source_obj),
            }
        )
    return serialized


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
async def knowledge_search(
    ctx: Context,
    query: str,
    limit: int = 5,
    scopes: list[str] | None = None,
) -> list[SearchResult] | KnowledgeFailureResult:
    """Search the knowledge base or return a typed operational failure."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    query_facade = app_ctx.query_facade

    if query_facade is None:
        msg = "Knowledge service not available"
        raise ToolError(msg)
    limit = _normalize_read_limit(limit)
    normalized_scopes = _normalize_scope_list(scopes)
    try:
        request = QueryRequest(
            text=query,
            top_k=limit,
            scopes=tuple(normalized_scopes or ()),
        )
        result = await query_facade.search(request)
    except KnowledgeOperationError as exc:
        return _serialize_knowledge_failure(exc.failure)
    except ValueError as exc:
        msg = "invalid search request"
        raise ToolError(msg) from exc
    return _serialize_query_facade_results(app_ctx, result)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
async def list_knowledge_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store_v2
    if store is None:
        msg = "source store v2 not available"
        raise ToolError(msg)
    scope = _normalize_optional_scope(scope)
    sources = store.list_sources(scope=scope)
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": str(getattr(s, "kind", "")),
            "scope": s.scope,
            "last_refreshed_at": getattr(s, "last_refreshed_at", None),
            "last_checked_at": getattr(s, "last_checked_at", None),
            "last_error": _sanitize_error(getattr(s, "last_error", None)),
            "enabled": bool(getattr(s, "state", "") == "active"),
            "refreshable": bool(getattr(s, "refreshable", False)),
            "enrich": bool(getattr(s, "enrich", False)),
            "fetch_method": str(getattr(s, "fetch_method", "")),
        }
        for s in sources
    ]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
async def lookup_knowledge_entity(
    ctx: Context,
    entity_id: str | None = None,
    entity_name: str | None = None,
    entity_type: str | None = None,
    expand_hops: int = 1,
) -> dict[str, Any]:
    """Look up a graph entity and neighborhood through QueryFacade."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    query_facade = app_ctx.query_facade
    if query_facade is None:
        msg = "query facade not available"
        raise ToolError(msg)

    try:
        request = EntityLookupRequest(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type,
            expand_hops=expand_hops,
        )
        result = query_facade.lookup_entity(request)
    except (ValidationError, ValueError) as exc:
        msg = "invalid entity lookup request"
        raise ToolError(msg) from exc
    except LookupError as exc:
        msg = "entity not found"
        raise ToolError(msg) from exc

    neighborhood = result.neighbourhood
    return {
        "entity": {
            "id": getattr(result.entity, "id", ""),
            "name": getattr(result.entity, "name", ""),
            "entity_type": str(getattr(result.entity, "entity_type", "")),
            "description": getattr(result.entity, "description", ""),
        },
        "neighbourhood": {
            "entities": [
                {
                    "id": item.id,
                    "name": item.name,
                    "entity_type": str(item.entity_type),
                }
                for item in (neighborhood.entities if neighborhood is not None else ())
            ],
            "edges": [
                {
                    "id": item.id,
                    "source_entity_id": item.source_entity_id,
                    "target_entity_id": item.target_entity_id,
                    "relation_type": str(item.relation_type),
                    "weight": item.weight,
                }
                for item in (neighborhood.edges if neighborhood is not None else ())
            ],
        },
        "related_chunks": [
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "source_id": chunk.source_id,
                "text": chunk.text,
                "scope": chunk.scope,
                "uri": chunk.uri,
            }
            for chunk in result.related_chunks
        ],
    }


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
async def register_knowledge_source(  # noqa: PLR0913
    ctx: Context,
    name: str,
    kind: str,
    fetch_method: str,
    config: dict[str, Any],
    *,
    scope: str = "global",
    enrich: bool = False,
    refreshable: bool = True,
    priority: int = 0,
    metadata: dict[str, Any] | None = None,
) -> RegisteredSourceResult:
    """Register a source in the v2 source store."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store_v2
    if store is None:
        msg = "source store v2 not available"
        raise ToolError(msg)

    try:
        registration = SourceRegistration.model_validate(
            {
                "name": name,
                "kind": kind,
                "fetch_method": fetch_method,
                "config": config,
                "scope": scope,
                "enrich": enrich,
                "refreshable": refreshable,
                "priority": priority,
                "metadata": {} if metadata is None else metadata,
            },
            strict=False,
        )
    except ValidationError as exc:
        raise ToolError(str(exc)) from exc

    try:
        source = store.register_source(registration)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return {
        "id": str(source.id),
        "name": str(source.name),
        "state": str(source.state),
        "kind": str(source.kind),
        "scope": str(source.scope),
    }


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
async def knowledge_ingest(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
    scope: str = "global",
    source_url: str | None = None,
) -> str:
    """Ingest a text document into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    coordinator = app_ctx.ingest_coordinator
    source_store = app_ctx.source_store_v2
    if coordinator is None:
        msg = "ingest coordinator not available"
        raise ToolError(msg)
    if source_store is None:
        msg = "source store not available"
        raise ToolError(msg)

    try:
        source_name = f"mcp-inline-{scope}"
        # SourceStore shares the app lifespan SQLite connection; keep operations
        # on the request thread to avoid cross-thread SQLite access errors.
        sources = source_store.list_sources(
            scope=scope,
            state=SourceState.ACTIVE,
        )
        source = next(
            (item for item in sources if item.name == source_name and item.kind == SourceKind.INLINE),
            None,
        )
        if source is None:
            source = source_store.register_source(
                SourceRegistration(
                    name=source_name,
                    kind=SourceKind.INLINE,
                    fetch_method=FetchTransport.NONE,
                    config=InlineConfig(),
                    scope=scope,
                    enrich=True,
                    refreshable=False,
                ),
            )

        document_metadata = metadata or {}
        request = IngestRequest(
            source_id=source.id,
            documents=(
                IngestDocument(
                    title=document_metadata.get("title", source_url or "Untitled inline document"),
                    text=text,
                    uri=source_url,
                    metadata=document_metadata,
                ),
            ),
            enrich=True,
        )
        result = await coordinator.ingest(request)
    except Exception as exc:  # noqa: BLE001
        return f"error: ingestion failed: {exc}"

    return (
        "Ingested: "
        f"documents_processed={result.documents_processed}, "
        f"chunks_created={result.chunks_created}, "
        f"chunks_enqueued={result.chunks_enqueued}"
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
async def knowledge_stats(ctx: Context) -> StatsResult:
    """Get knowledge base summary statistics."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    coordinator = app_ctx.ingest_coordinator
    enrichment_store = app_ctx.enrichment_store
    conn = app_ctx.conn
    if coordinator is None:
        msg = "ingest coordinator not available"
        raise ToolError(msg)
    if enrichment_store is None:
        msg = "enrichment store not available"
        raise ToolError(msg)

    ingest_stats = coordinator.stats()
    enrichment_stats = enrichment_store.stats()

    now_iso = datetime.now(tz=UTC).isoformat()
    claimable_row = conn.execute(
        """
        SELECT COUNT(*)
                FROM enrich_queue AS eq
                JOIN content_chunks AS cc ON cc.id = eq.chunk_id
                JOIN content_documents AS cd ON cd.document_id = cc.document_id
                JOIN source_registry AS sr ON sr.id = cd.source_id
                WHERE sr.state = 'active'
                    AND COALESCE(sr.enrich, 0) = 1
          AND (
                        eq.state = 'pending'
            OR (
                                eq.state = 'in_progress'
                                AND eq.started_at IS NOT NULL
                                AND (strftime('%s', ?) - strftime('%s', eq.started_at)) > 600
            )
          )
        """,
        (now_iso,),
    ).fetchone()
    total_chunks = ingest_stats.chunks_total
    chunks_enriched = enrichment_stats.completed
    chunks_enriched_ratio = float(chunks_enriched) / float(total_chunks) if total_chunks else 0.0

    return {
        "documents": ingest_stats.documents_total,
        "entities": ingest_stats.graph_entities,
        "edges": ingest_stats.graph_edges,
        "total_sources": ingest_stats.sources_total,
        "total_chunks": total_chunks,
        "chunks_pending": enrichment_stats.pending,
        "chunks_claimed": enrichment_stats.in_progress,
        "chunks_failed": enrichment_stats.failed,
        "chunks_enriched": chunks_enriched,
        "chunks_claimable": int(claimable_row[0] if claimable_row is not None else 0),
        "chunks_enriched_ratio": chunks_enriched_ratio,
    }


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
async def refresh_knowledge_source(
    ctx: Context,
    source_id: str,
) -> RefreshToolResult | KnowledgeFailureResult:
    """Trigger re-ingestion of a registered knowledge source by its ID.

    Returns source_id, sources_refreshed, and serialized refresh errors.

    Raises ToolError when source storage is unavailable or source_id is missing.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store_v2
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    source = store.get_source(source_id)
    if source is None:
        msg = "source not found"
        raise ToolError(msg)

    if source.state != SourceState.ACTIVE:
        msg = "source is not active"
        raise ToolError(msg)

    coordinator = app_ctx.ingest_coordinator
    if coordinator is None:
        msg = "ingest coordinator not available"
        raise ToolError(msg)

    try:
        result = await coordinator.refresh(RefreshRequest(source_ids=(source_id,)))
    except KnowledgeOperationError as exc:
        return _serialize_knowledge_failure(exc.failure)
    documents_created = sum(item.documents_created for item in result.ingest_results)
    documents_replaced = sum(item.documents_replaced for item in result.ingest_results)
    documents_unchanged = sum(item.documents_unchanged for item in result.ingest_results)
    chunks_created = sum(item.chunks_created for item in result.ingest_results)
    chunks_replaced = sum(item.chunks_replaced for item in result.ingest_results)
    return {
        "source_id": source_id,
        "sources_refreshed": result.sources_refreshed,
        "documents_created": documents_created,
        "documents_replaced": documents_replaced,
        "documents_unchanged": documents_unchanged,
        "chunks_created": chunks_created,
        "chunks_replaced": chunks_replaced,
        "errors": [_serialize_refresh_error(error) for error in result.errors],
    }


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True))
async def delete_knowledge_source(ctx: Context, source_id: str) -> dict[str, Any]:
    """Delete a source through ingest-coordinator purge orchestration."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    source_store = app_ctx.source_store_v2
    if source_store is None:
        msg = "source store not available"
        raise ToolError(msg)

    source = source_store.get_source(source_id)
    if source is None:
        msg = f"Source '{source_id}' not found"
        raise ToolError(msg)

    coordinator = app_ctx.ingest_coordinator
    if coordinator is None:
        msg = "ingest coordinator not available"
        raise ToolError(msg)

    purge_result = await coordinator.delete_source(source_id)
    return {
        "status": purge_result.status.value,
        "completed_steps": list(purge_result.completed_steps),
        "failed_step": purge_result.failed_step,
        "error": purge_result.error,
        "source": purge_result.source.model_dump(mode="json"),
        "content": purge_result.content.model_dump(mode="json"),
        "enrichment": purge_result.enrichment.model_dump(mode="json"),
        "graph": purge_result.graph.model_dump(mode="json"),
    }
