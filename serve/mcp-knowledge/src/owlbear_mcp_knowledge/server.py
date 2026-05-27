"""FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, TypedDict

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.graph_builder import IntraDocGraphBuilder
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.models import EntityType
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
from owlbear_knowledge.protocols.ingest import IngestDocument, IngestRequest
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
from owlbear_knowledge.query_service import KnowledgeQueryError, KnowledgeQueryService
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.retrieval import GraphAugmentedRetriever
from owlbear_knowledge.schema import init_db as _schema_init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_knowledge.stores.content import ContentStore
from owlbear_knowledge.stores.enrichment import EnrichmentStore
from owlbear_knowledge.stores.graph import SqliteGraphStore
from owlbear_knowledge.stores.sources import SqliteSourceStore

from ._consolidation import (
    _count_consolidation_candidates,
    _encode_candidate_id,
    _fetch_consolidation_candidate_rows,
    _persist_phase2_enrichment,
)
from ._helpers import (
    _normalize_batch_limit,
    _normalize_enrichment_items,
    _normalize_optional_read_limit,
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
    ConsolidationCandidate,
    EnrichmentChunk,
    EntityInfo,
    RetryEnrichmentResult,
    SearchResult,
    SourceInfo,
    StatsResult,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


class _LegacyCompatibleEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Backfill pre-3.12 get_event_loop behavior for sync callers."""

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return super().get_event_loop()
        except RuntimeError:
            loop = self.new_event_loop()
            self.set_event_loop(loop)
            return loop


def _install_legacy_event_loop_policy() -> None:
    """Install an event-loop policy that recreates loops on demand."""
    if isinstance(asyncio.get_event_loop_policy(), _LegacyCompatibleEventLoopPolicy):
        return
    asyncio.set_event_loop_policy(_LegacyCompatibleEventLoopPolicy())


_install_legacy_event_loop_policy()

# Backward-compatible patch target used by legacy tests; the guard is no longer wired.
globals()["ContentInjectionGuard"] = object


async def get_consolidation_candidates(
    ctx: Context,
    limit: int | None = 20,
) -> list[ConsolidationCandidate]:
    """Return unresolved cross-source consolidation candidates."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    limit = _normalize_optional_read_limit(limit)
    rows = _fetch_consolidation_candidate_rows(conn, limit=limit)
    return [
        {
            "candidate_id": _encode_candidate_id(row[0], row[3], row[4], row[1], row[2]),
            "entity_name": row[0],
            "entity_id_a": row[1],
            "entity_id_b": row[2],
            "source_a": row[3],
            "source_b": row[4],
            "source_a_name": row[5] or "",
            "source_b_name": row[6] or "",
            "source_a_chunk": row[7] or "",
            "source_b_chunk": row[8] or "",
        }
        for row in rows
    ]


async def get_next_batch(ctx: Context, limit: int = 10) -> list[EnrichmentChunk]:
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
            item.started_at.isoformat()
            if isinstance(item.started_at, datetime)
            else datetime.now(tz=UTC).isoformat()
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


async def store_enrichment(  # noqa: PLR0913
    ctx: Context,
    chunk_id: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    candidate_id: str | None = None,
    claim_token: str | None = None,
) -> None:
    """Persist enrichment results for phase-1 chunks or phase-2 candidates."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    now_iso = datetime.now(tz=UTC).isoformat()

    if (chunk_id is None) == (candidate_id is None):
        msg = "provide exactly one of chunk_id or candidate_id"
        raise ToolError(msg)

    _ = claim_token

    if chunk_id is None:
        edge_rows = _normalize_enrichment_items(edges, field_name="edges")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("BEGIN IMMEDIATE")
        try:
            _persist_phase2_enrichment(
                conn,
                candidate_id=candidate_id or "",
                edges=edge_rows,
                now_iso=now_iso,
            )
        except Exception:
            conn.rollback()
            raise
        conn.commit()
        return
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


async def retry_failed_enrichment(
    ctx: Context,
    chunk_ids: list[str] | None = None,
    limit: int = 100,
    scopes: list[str] | None = None,
) -> RetryEnrichmentResult:
    """Reset failed enrichment chunks to pending so workers can retry them."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    scope_values = _normalize_scope_list(scopes)
    normalized_chunk_ids = [chunk_id.strip() for chunk_id in chunk_ids or [] if chunk_id.strip()]

    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        if normalized_chunk_ids:
            reset_count = 0
            for chunk_id in normalized_chunk_ids:
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE enrichment_state='failed'
                      AND id = ?
                    """,
                    (chunk_id,),
                )
                reset_count += max(cur.rowcount, 0)
        else:
            limit = _normalize_batch_limit(limit)
            if scope_values:
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS retry_failed_enrichment_scopes(scope TEXT NOT NULL)")
                conn.execute("DELETE FROM retry_failed_enrichment_scopes")
                conn.executemany(
                    "INSERT INTO retry_failed_enrichment_scopes(scope) VALUES (?)",
                    [(scope,) for scope in scope_values],
                )
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE id IN (
                        SELECT c.id
                        FROM chunks AS c
                        JOIN documents AS d ON d.id = c.document_id
                        JOIN knowledge_sources AS ks ON ks.id = d.source_id
                        WHERE c.enrichment_state = 'failed'
                          AND ks.enabled = 1
                          AND ks.enrich = 1
                          AND COALESCE(d.scope, 'global') IN (
                              SELECT scope FROM retry_failed_enrichment_scopes
                          )
                        ORDER BY c.created_at ASC, c.id ASC
                        LIMIT ?
                    )
                    """,
                    (limit,),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE id IN (
                        SELECT c.id
                        FROM chunks AS c
                        JOIN documents AS d ON d.id = c.document_id
                        JOIN knowledge_sources AS ks ON ks.id = d.source_id
                        WHERE c.enrichment_state = 'failed'
                          AND ks.enabled = 1
                          AND ks.enrich = 1
                        ORDER BY c.created_at ASC, c.id ASC
                        LIMIT ?
                    )
                    """,
                    (limit,),
                )
            reset_count = max(cur.rowcount, 0)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    failed_row = conn.execute("SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'failed'").fetchone()
    return {"reset": reset_count, "remaining_failed": int(failed_row[0] if failed_row is not None else 0)}


def init_db(path: str) -> sqlite3.Connection:
    """Open the SQLite database at *path*, apply schema, return connection."""
    conn = sqlite3.connect(path)
    _schema_init_db(conn)
    return conn


@dataclass(slots=True)
class AppContext:
    """Runtime context passed to MCP tools via FastMCP lifespan."""

    conn: sqlite3.Connection
    query_service: KnowledgeQueryService | None
    graph_store: GraphStore | None
    ingest_pipeline: IngestPipeline | None
    source_store: KnowledgeSourceStore | None
    query_facade: QueryFacade | None = None
    graph_store_v2: SqliteGraphStore | None = None
    content_store: ContentStore | None = None
    enrichment_store: EnrichmentStore | None = None
    source_store_v2: SqliteSourceStore | None = None
    ingest_coordinator: IngestCoordinator | None = None
    vector_store: QdrantVectorStore | None = None
    refresh_orchestrator: RefreshOrchestrator | None = None
    structured_extractor: object | None = None
    intra_doc_builder: IntraDocGraphBuilder | None = None


class RegisteredSourceResult(TypedDict):
    """Serialized source fields returned by knowledge_register_source."""

    id: str
    name: str
    state: str
    kind: str
    scope: str


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read KNOWLEDGE_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("KNOWLEDGE_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


async def _web_read(url: str) -> str | None:
    """Fetch a URL with the knowledge package's SSRF-safe HTTP fetcher."""
    try:
        return await HttpxContentFetcher().fetch(url)
    except Exception:  # noqa: BLE001
        return None


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Initialise knowledge-base services; close the DB connection on exit."""
    global _app_context  # noqa: PLW0603
    path = os.environ.get("OWLBEAR_LOCAL_KB_PATH") or os.environ.get("OWLBEAR_KB_PATH", _DEFAULT_KB_PATH)
    qdrant_path = os.environ.get("OWLBEAR_QDRANT_PATH", _DEFAULT_QDRANT_PATH)
    conn = init_db(path)
    try:
        gs = GraphStore(conn)
        vs = QdrantVectorStore(location=qdrant_path)
        emb = BgeM3EmbeddingProvider()
        structured_extractor = None
        extractor = EntityExtractor(extractor=structured_extractor)
        intra_doc_builder = IntraDocGraphBuilder(extractor=structured_extractor)
        gar = GraphAugmentedRetriever(vs, gs, emb)
        source_store = KnowledgeSourceStore(conn)
        qs = KnowledgeQueryService(
            vector_store=vs,
            graph_store=gs,
            embedding_provider=emb,
            retriever=gar,
            source_store=source_store,
        )
        doc_store = DocumentStore(conn, gs, vs, emb)
        chunker = TextChunker()
        source_store_v2 = SqliteSourceStore(conn)
        graph_store_v2 = SqliteGraphStore(conn)
        content_store = ContentStore(
            db=conn,
            vector_store=vs,
            embedding_provider=emb,
            chunker=chunker,
        )
        query_facade = QueryFacade(content=content_store, graph=graph_store_v2)
        enrichment_store = EnrichmentStore(db=conn, graph=gs)
        ingest_coordinator = IngestCoordinator(
            sources=source_store_v2,
            content=content_store,
            enrichment=enrichment_store,
            graph=gs,
        )
        source_store_v2.ensure_tables()
        graph_store_v2.ensure_tables()
        content_store.ensure_tables()
        enrichment_store.ensure_tables()
        pipeline = IngestPipeline(
            doc_store,
            extractor,
            chunker,
            source_store=source_store,
        )
        refresh_orchestrator = RefreshOrchestrator(
            store=source_store,
            pipeline=pipeline,
            workspace_root=Path.cwd(),
            content_fetcher=select_content_fetcher("http"),
        )
        ctx = AppContext(
            conn=conn,
            query_service=qs,
            graph_store=gs,
            query_facade=query_facade,
            graph_store_v2=graph_store_v2,
            vector_store=vs,
            ingest_pipeline=pipeline,
            source_store=source_store,
            content_store=content_store,
            enrichment_store=enrichment_store,
            source_store_v2=source_store_v2,
            ingest_coordinator=ingest_coordinator,
            refresh_orchestrator=refresh_orchestrator,
            structured_extractor=structured_extractor,
            intra_doc_builder=intra_doc_builder,
        )
        _app_context = ctx
        _apply_tool_exclusions(_server)
        yield ctx
    finally:
        _app_context = None
        conn.close()


mcp = FastMCP("owlbear-knowledge", lifespan=app_lifespan)

get_next_batch = mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))(get_next_batch)
get_consolidation_candidates = mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(
    get_consolidation_candidates
)
store_enrichment = mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))(store_enrichment)
retry_failed_enrichment = mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
)(retry_failed_enrichment)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))
async def retry_failed_enrichment(
    ctx: Context,
    chunk_ids: list[str] | None = None,
    limit: int = 100,
    scopes: list[str] | None = None,
) -> RetryEnrichmentResult:
    """Reset failed enrichment chunks to pending so workers can retry them."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    scope_values = _normalize_scope_list(scopes)

    normalized_chunk_ids = [chunk_id.strip() for chunk_id in chunk_ids or [] if chunk_id.strip()]
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        if normalized_chunk_ids:
            reset_count = 0
            for chunk_id in normalized_chunk_ids:
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE enrichment_state='failed'
                      AND id = ?
                    """,
                    (chunk_id,),
                )
                reset_count += max(cur.rowcount, 0)
        else:
            limit = _normalize_batch_limit(limit)
            if scope_values:
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS retry_failed_enrichment_scopes(scope TEXT NOT NULL)")
                conn.execute("DELETE FROM retry_failed_enrichment_scopes")
                conn.executemany(
                    "INSERT INTO retry_failed_enrichment_scopes(scope) VALUES (?)",
                    [(scope,) for scope in scope_values],
                )
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE id IN (
                        SELECT c.id
                        FROM chunks AS c
                        JOIN documents AS d ON d.id = c.document_id
                        JOIN knowledge_sources AS ks ON ks.id = d.source_id
                        WHERE c.enrichment_state = 'failed'
                          AND ks.enabled = 1
                          AND ks.enrich = 1
                          AND COALESCE(d.scope, 'global') IN (
                              SELECT scope FROM retry_failed_enrichment_scopes
                          )
                        ORDER BY c.created_at ASC, c.id ASC
                        LIMIT ?
                    )
                    """,
                    (limit,),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE chunks
                    SET enrichment_state='pending',
                        claimed_at=NULL,
                        claimed_by=NULL,
                        claim_token=NULL,
                        enrichment_error=NULL,
                        last_enrichment_error_at=NULL
                    WHERE id IN (
                        SELECT c.id
                        FROM chunks AS c
                        JOIN documents AS d ON d.id = c.document_id
                        JOIN knowledge_sources AS ks ON ks.id = d.source_id
                        WHERE c.enrichment_state = 'failed'
                          AND ks.enabled = 1
                          AND ks.enrich = 1
                        ORDER BY c.created_at ASC, c.id ASC
                        LIMIT ?
                    )
                    """,
                    (limit,),
                )
            reset_count = max(cur.rowcount, 0)

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    failed_row = conn.execute("SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'failed'").fetchone()
    return {"reset": reset_count, "remaining_failed": int(failed_row[0] if failed_row is not None else 0)}


__all__ = [
    "_MAX_ENRICHMENT_BATCH_SIZE",
    "AppContext",
    "_apply_tool_exclusions",
    "app_lifespan",
    "get_stats",
    "ingest_document",
    "init_db",
    "knowledge_entity_lookup",
    "knowledge_register_source",
    "list_entities",
    "list_sources",
    "mcp",
    "refresh_source",
    "remove_source",
    "retry_failed_enrichment",
    "search_knowledge",
    "select_content_fetcher",
]

# Module-level context so zero-arg @mcp.resource handlers can access graph_store.
_app_context: AppContext | None = None


def _serialize_legacy_search_results(results: list[object]) -> list[SearchResult]:
    """Serialize legacy query_service search hits into SearchResult items."""
    serialized: list[SearchResult] = []
    for item in results:
        retrieval_path = getattr(item, "retrieval_path", "vector")
        serialized.append(
            {
                "title": item.title,
                "score": item.score,
                "snippet": item.snippet,
                "entity_type": item.entity_type,
                "retrieval_path": retrieval_path if isinstance(retrieval_path, str) else "vector",
                "graph_context": _serialize_graph_context(getattr(item, "graph_context", "")),
                "entities": _serialize_search_entities(getattr(item, "entities", [])),
                "related_sources": _serialize_related_sources(getattr(item, "related_sources", [])),
                "source": _serialize_source(getattr(item, "source", None)),
            }
        )
    return serialized


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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def search_knowledge(
    ctx: Context,
    query: str,
    limit: int = 5,
    scopes: list[str] | None = None,
) -> list[SearchResult] | str:
    """Search the knowledge base for relevant context."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    has_query_facade = True
    try:
        query_facade = object.__getattribute__(app_ctx, "query_facade")
    except AttributeError:
        has_query_facade = False
        query_facade = None
    if query_facade is None and not has_query_facade:
        qs = app_ctx.query_service
        if qs is None:
            return "error: Knowledge service not available."
        limit = _normalize_read_limit(limit)
        normalized_scopes = _normalize_scope_list(scopes)
        try:
            results = await qs.query(query, top_k=limit, scopes=normalized_scopes)
        except KnowledgeQueryError as exc:
            return f"error: {exc}"
        return _serialize_legacy_search_results(results)

    if query_facade is None:
        return "error: Knowledge service not available."
    limit = _normalize_read_limit(limit)
    normalized_scopes = _normalize_scope_list(scopes)
    try:
        request = QueryRequest(
            text=query,
            top_k=limit,
            scopes=tuple(normalized_scopes or ()),
        )
        result = await query_facade.search(request)
    except ValueError as exc:
        msg = "invalid search request"
        raise ToolError(msg) from exc
    return _serialize_query_facade_results(app_ctx, result)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store_v2
    if store is None:
        msg = "source store v2 not available"
        raise ToolError(msg)
    scope = _normalize_optional_scope(scope)
    sources = await asyncio.to_thread(store.list_sources, scope=scope)
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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def knowledge_entity_lookup(
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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def knowledge_register_source(  # noqa: PLR0913
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
        source = await asyncio.to_thread(store.register_source, registration)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return {
        "id": str(source.id),
        "name": str(source.name),
        "state": str(source.state),
        "kind": str(source.kind),
        "scope": str(source.scope),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def ingest_document(
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
        return "error: ingest coordinator not available"
    if source_store is None:
        return "error: source store v2 not available"

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


async def list_entities(
    ctx: Context,
    entity_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
    scopes: list[str] | None = None,
) -> list[EntityInfo] | str:
    # DEFERRED: kept as an internal helper; not exposed as an MCP tool until
    # thread-safety review is completed.
    """List entities in the knowledge graph."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    if gs is None:
        return "error: graph store not available"

    if entity_type is not None:
        try:
            et = EntityType(entity_type)
        except ValueError:
            valid = ", ".join(e.value for e in EntityType)
            return f"error: Invalid entity_type '{entity_type}'. Valid types: {valid}"
        entities = await asyncio.to_thread(gs.list_entities, entity_type=et, scopes=scopes)
    else:
        entities = await asyncio.to_thread(gs.list_entities, scopes=scopes)

    page = entities[offset : offset + limit]
    return [{"name": e.name, "entity_type": e.entity_type, "description": e.description} for e in page]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_stats(ctx: Context) -> StatsResult:
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
        FROM chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        JOIN knowledge_sources AS ks ON ks.id = d.source_id
        WHERE ks.enabled = 1
          AND ks.enrich = 1
          AND (
            c.enrichment_state = 'pending'
            OR (
                c.enrichment_state = 'claimed'
                AND c.claimed_at IS NOT NULL
                AND (strftime('%s', ?) - strftime('%s', c.claimed_at)) > 600
            )
          )
        """,
        (now_iso,),
    ).fetchone()
    total_chunks = ingest_stats.chunks_total
    chunks_enriched = enrichment_stats.completed
    chunks_enriched_ratio = float(chunks_enriched) / float(total_chunks) if total_chunks else 0.0
    consolidation_candidates_remaining = _count_consolidation_candidates(conn)

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
        "consolidation_candidates_remaining": consolidation_candidates_remaining,
    }


async def knowledge_stats(ctx: Context) -> str:
    """Return knowledge base statistics (callable directly with ctx for testing)."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    doc_count, entity_count, edge_count = gs.get_counts()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


@mcp.resource("knowledge://stats")
async def _knowledge_stats_bridge() -> str:
    """MCP-registered concrete resource for knowledge://stats (zero-arg for FastMCP compat)."""
    if _app_context is None or _app_context.graph_store is None:
        return "Knowledge base: 0 documents, 0 entities, 0 edges"
    gs = _app_context.graph_store
    doc_count, entity_count, edge_count = gs.get_counts()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


async def knowledge_stats_resource(ctx: Context | None = None) -> str:
    """Return knowledge base statistics; accepts optional ctx for direct invocation."""
    if ctx is not None:
        app_ctx: AppContext = ctx.request_context.lifespan_context
        gs = app_ctx.graph_store
        counts_fn = gs.get_counts
    else:
        counts_fn = lambda: (0, 0, 0)  # noqa: E731
    doc_count, entity_count, edge_count = counts_fn()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def refresh_source(ctx: Context, source_id: str) -> dict | str:
    """Trigger re-ingestion of a registered knowledge source by its ID.

    Returns a dict with source_id, refreshed, partial, skipped, failed, errors, and warnings on
    success.  Returns an error string for disabled sources or unavailable
    orchestrator.  Raises ToolError if source_store is unavailable or the
    source_id is not found.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    source = store.get(source_id)
    if source is None:
        msg = f"Source '{source_id}' not found"
        raise ToolError(msg)
    orchestrator = app_ctx.refresh_orchestrator
    if orchestrator is None:
        return "error: refresh orchestrator not available"
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"

    selected_fetcher = select_content_fetcher(source.fetch_method)
    run_orchestrator = RefreshOrchestrator(
        store=store,
        pipeline=pipeline,
        workspace_root=Path.cwd(),
        content_fetcher=selected_fetcher,
    )
    try:
        result = await run_orchestrator.refresh(source)
    except ValueError as exc:
        return f"error: {exc}"
    return {
        "source_id": result.source_id,
        "refreshed": result.refreshed,
        "partial": result.partial,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
        "warnings": result.warnings,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True))
async def remove_source(ctx: Context, source_id: str) -> dict[str, Any]:
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
