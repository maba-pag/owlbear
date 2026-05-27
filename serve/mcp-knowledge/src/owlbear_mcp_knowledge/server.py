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
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

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
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryError, KnowledgeQueryService
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.retrieval import GraphAugmentedRetriever
from owlbear_knowledge.schema import init_db as _schema_init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_knowledge.stores.content import ContentStore
from owlbear_knowledge.stores.enrichment import EnrichmentStore
from owlbear_knowledge.stores.sources import SqliteSourceStore

from ._consolidation import (
    _count_consolidation_candidates,
    _encode_candidate_id,
    _fetch_consolidation_candidate_rows,
    _persist_phase2_enrichment,
)
from ._enrichment import _mark_failed_chunk_claim, _persist_phase1_enrichment
from ._helpers import (
    _extract_section_path,
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
    conn = app_ctx.conn
    limit = _normalize_batch_limit(limit)
    now = datetime.now(tz=UTC)
    now_iso = now.isoformat()
    claim_token = uuid4().hex

    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.content,
                d.title,
                c.metadata,
                ks.name,
                d.id,
                d.source_id,
                d.scope
            FROM chunks AS c
            JOIN documents AS d ON d.id = c.document_id
            JOIN knowledge_sources AS ks ON ks.id = d.source_id
                        WHERE ks.enrich = 1
                            AND ks.enabled = 1
              AND (
                c.enrichment_state = 'pending'
                OR (
                    c.enrichment_state = 'claimed'
                    AND c.claimed_at IS NOT NULL
                                        AND (strftime('%s', ?) - strftime('%s', c.claimed_at)) > 600
                )
              )
            ORDER BY c.created_at ASC, c.id ASC
            LIMIT ?
            """,
            (now_iso, limit),
        ).fetchall()

        if rows:
            chunk_ids = [row[0] for row in rows]
            placeholders = ",".join("?" for _ in chunk_ids)
            update_sql = (
                "UPDATE chunks SET enrichment_state='claimed', claimed_at=?, claim_token=? "  # noqa: S608
                f"WHERE id IN ({placeholders})"
            )
            conn.execute(
                update_sql,
                (now_iso, claim_token, *chunk_ids),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return [
        {
            "chunk_id": row[0],
            "text": row[1],
            "doc_title": row[2] if isinstance(row[2], str) else "",
            "section_path": _extract_section_path(row[3]),
            "source_name": row[4] if isinstance(row[4], str) else "",
            "document_id": row[5],
            "source_id": row[6],
            "scope": row[7] if isinstance(row[7], str) and row[7] else "global",
            "claim_token": claim_token,
            "claimed_at": now_iso,
        }
        for row in rows
    ]


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

    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        entity_rows = _normalize_enrichment_items(entities, field_name="entities")
        edge_rows = _normalize_enrichment_items(edges, field_name="edges")
        _persist_phase1_enrichment(
            conn,
            chunk_id=chunk_id,
            claim_token=claim_token,
            entities=entity_rows,
            edges=edge_rows,
            now_iso=now_iso,
        )
    except Exception as exc:
        conn.rollback()
        conn.execute("BEGIN IMMEDIATE")
        try:
            _mark_failed_chunk_claim(
                conn,
                chunk_id=chunk_id,
                claim_token=claim_token,
                reason=str(exc),
                now_iso=now_iso,
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
        raise
    conn.commit()


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
    content_store: ContentStore | None = None
    enrichment_store: EnrichmentStore | None = None
    source_store_v2: SqliteSourceStore | None = None
    ingest_coordinator: IngestCoordinator | None = None
    vector_store: QdrantVectorStore | None = None
    refresh_orchestrator: RefreshOrchestrator | None = None
    structured_extractor: object | None = None
    intra_doc_builder: IntraDocGraphBuilder | None = None


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
        content_store = ContentStore(
            db=conn,
            vector_store=vs,
            embedding_provider=emb,
            chunker=chunker,
        )
        enrichment_store = EnrichmentStore(db=conn, graph=gs)
        ingest_coordinator = IngestCoordinator(
            sources=source_store_v2,
            content=content_store,
            enrichment=enrichment_store,
            graph=gs,
        )
        source_store_v2.ensure_tables()
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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def search_knowledge(
    ctx: Context,
    query: str,
    limit: int = 5,
    scopes: list[str] | None = None,
) -> list[SearchResult] | str:
    """Search the knowledge base for relevant context."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    qs = app_ctx.query_service
    if qs is None:
        return "error: Knowledge service not available."
    limit = _normalize_read_limit(limit)
    scopes = _normalize_scope_list(scopes)
    try:
        results = await qs.query(query, top_k=limit, scopes=scopes)
    except KnowledgeQueryError as exc:
        return f"error: {exc}"
    serialized: list[SearchResult] = []
    for r in results:
        retrieval_path = getattr(r, "retrieval_path", "vector")
        serialized.append(
            {
                "title": r.title,
                "score": r.score,
                "snippet": r.snippet,
                "entity_type": r.entity_type,
                "retrieval_path": (retrieval_path if isinstance(retrieval_path, str) else "vector"),
                "graph_context": _serialize_graph_context(getattr(r, "graph_context", "")),
                "entities": _serialize_search_entities(getattr(r, "entities", [])),
                "related_sources": _serialize_related_sources(getattr(r, "related_sources", [])),
                "source": _serialize_source(getattr(r, "source", None)),
            }
        )
    return serialized


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    scope = _normalize_optional_scope(scope)
    sources = await asyncio.to_thread(store.list_all, scope=scope)
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": str(s.source_type),
            "scope": s.scope,
            "last_refreshed_at": s.last_refreshed_at,
            "last_checked_at": s.last_checked_at,
            "last_error": _sanitize_error(s.last_error),
            "enabled": s.enabled,
            "refreshable": s.refreshable,
            "enrich": s.enrich,
            "fetch_method": s.fetch_method,
        }
        for s in sources
    ]


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
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"
    try:
        result = await pipeline.ingest_text(
            text,
            metadata=metadata,
            scope=scope,
            source_url=source_url,
        )
    except Exception as exc:  # noqa: BLE001
        return f"error: ingestion failed: {exc}"
    else:
        if result.status == "failed":
            return f"error: ingestion failed for document {result.document_id}"
        warning_text = f", warnings: {'; '.join(result.warnings)}" if result.warnings else ""
        return (
            f"Ingested: {result.document_id}, {result.chunk_count} chunks, "
            f"{result.entity_count} entities, {result.edge_count} edges "
            f"(status: {result.status}{warning_text})"
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
    gs = app_ctx.graph_store
    conn = app_ctx.conn
    if gs is None:
        msg = "graph store not available"
        raise ToolError(msg)
    doc_count, entity_count, edge_count = gs.get_counts()

    total_sources = conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0]
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    enriched_chunks = conn.execute("SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'enriched'").fetchone()[0]
    state_counts = {
        str(row[0] or "pending"): int(row[1])
        for row in conn.execute(
            "SELECT COALESCE(enrichment_state, 'pending'), COUNT(*) FROM chunks GROUP BY enrichment_state"
        ).fetchall()
    }
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
    chunks_enriched_ratio = float(enriched_chunks) / float(total_chunks) if total_chunks else 0.0
    consolidation_candidates_remaining = _count_consolidation_candidates(conn)

    return {
        "documents": doc_count,
        "entities": entity_count,
        "edges": edge_count,
        "total_sources": total_sources,
        "total_chunks": total_chunks,
        "chunks_pending": state_counts.get("pending", 0),
        "chunks_claimed": state_counts.get("claimed", 0),
        "chunks_failed": state_counts.get("failed", 0),
        "chunks_enriched": state_counts.get("enriched", 0),
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
async def remove_source(ctx: Context, source_id: str) -> dict[str, int]:
    """Delete a source after removing vectors; abort on vector deletion exceptions."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)

    source = store.get(source_id)
    if source is None:
        msg = f"Source '{source_id}' not found"
        raise ToolError(msg)

    conn = app_ctx.conn
    vector_store = app_ctx.vector_store
    if vector_store is None:
        msg = "vector store not available"
        raise ToolError(msg)

    doc_count_row = conn.execute("SELECT COUNT(*) FROM documents WHERE source_id = ?", (source_id,)).fetchone()
    chunk_count_row = conn.execute(
        """
        SELECT COUNT(*)
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.source_id = ?
        """,
        (source_id,),
    ).fetchone()
    entity_count_row = conn.execute(
        """
        SELECT COUNT(*)
        FROM entities e
        JOIN documents d ON e.document_id = d.id
        WHERE d.source_id = ?
        """,
        (source_id,),
    ).fetchone()

    chunk_rows = conn.execute(
        """
        SELECT c.id
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.source_id = ?
        """,
        (source_id,),
    ).fetchall()
    chunk_ids = [str(row[0]) for row in chunk_rows]
    entity_rows = conn.execute(
        """
        SELECT e.id
        FROM entities e
        JOIN documents d ON e.document_id = d.id
        WHERE d.source_id = ?
        """,
        (source_id,),
    ).fetchall()
    entity_ids = [str(row[0]) for row in entity_rows]

    try:
        for vector_id in [*chunk_ids, *entity_ids]:
            vector_store.delete_embedding(vector_id)
    except Exception as exc:
        msg = f"Failed to delete vectors for source '{source_id}': {exc}"
        raise ToolError(msg) from exc

    doc_count = int(doc_count_row[0] if doc_count_row is not None else 0)
    chunk_count = int(chunk_count_row[0] if chunk_count_row is not None else 0)
    entity_count = int(entity_count_row[0] if entity_count_row is not None else 0)
    logger.info(
        "remove_source audit source_id=%s source_name=%s documents=%d chunks=%d entities=%d",
        source_id,
        source.name,
        doc_count,
        chunk_count,
        entity_count,
    )
    store.delete_cascade(source_id)
    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "entities": entity_count,
    }
