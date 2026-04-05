"""FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import EntityType
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.schema import init_db as _schema_init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_DEFAULT_KB_PATH = "store/knowledge/knowledge.db"
_DEFAULT_MODEL = "gpt-4o-mini"


class SearchResult(TypedDict):
    """A single knowledge-base search result."""

    title: str
    score: float
    snippet: str


class SourceInfo(TypedDict):
    """A registered knowledge source entry."""

    name: str
    source_type: str
    scope: str


class EntityInfo(TypedDict):
    """A knowledge-graph entity entry."""

    name: str
    entity_type: str
    description: str


class StatsResult(TypedDict):
    """Knowledge-base summary statistics."""

    documents: int
    entities: int
    edges: int


def init_db(path: str) -> sqlite3.Connection:
    """Open the SQLite database at *path*, apply schema, return connection."""
    conn = sqlite3.connect(path)
    _schema_init_db(conn)
    return conn


@dataclass(slots=True)
class AppContext:
    """Runtime context passed to MCP tools via FastMCP lifespan."""

    query_service: KnowledgeQueryService | None
    graph_store: GraphStore | None
    ingest_pipeline: IngestPipeline | None
    source_store: KnowledgeSourceStore | None


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


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Initialise knowledge-base services; close the DB connection on exit."""
    global _app_context  # noqa: PLW0603
    path = os.environ.get("OWLBEAR_KB_PATH", _DEFAULT_KB_PATH)
    conn = init_db(path)
    try:
        gs = GraphStore(conn)
        vs = QdrantVectorStore()
        emb = BgeM3EmbeddingProvider()
        qs = KnowledgeQueryService(vector_store=vs, graph_store=gs, embedding_provider=emb)
        doc_store = DocumentStore(conn, gs, vs, emb)
        model = os.environ.get("OWLBEAR_MODEL", _DEFAULT_MODEL)
        extractor = EntityExtractor(model)
        chunker = TextChunker()
        pipeline = IngestPipeline(doc_store, extractor, chunker)
        source_store = KnowledgeSourceStore(conn)
        ctx = AppContext(
            query_service=qs,
            graph_store=gs,
            ingest_pipeline=pipeline,
            source_store=source_store,
        )
        _app_context = ctx
        _apply_tool_exclusions(_server)
        yield ctx
    finally:
        _app_context = None
        conn.close()


mcp = FastMCP("owlbear-knowledge", lifespan=app_lifespan)

__all__ = [
    "AppContext",
    "_apply_tool_exclusions",
    "app_lifespan",
    "get_stats",
    "ingest_document",
    "init_db",
    "list_entities",
    "list_sources",
    "mcp",
    "search_knowledge",
]

# Module-level context so zero-arg @mcp.resource handlers can access graph_store.
_app_context: AppContext | None = None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def search_knowledge(ctx: Context, query: str, limit: int = 5) -> list[SearchResult] | str:
    """Search the knowledge base for relevant context."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    qs = app_ctx.query_service
    if qs is None:
        return "error: Knowledge service not available."
    results = await qs.query(query, top_k=limit)
    return [{"title": r.title, "score": r.score, "snippet": r.snippet} for r in results]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "error: source store not available"
        raise ToolError(msg)
    sources = await asyncio.to_thread(store.list_all, scope=scope)
    return [{"name": s.name, "source_type": s.source_type, "scope": s.scope} for s in sources]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def ingest_document(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Ingest a text document into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"
    try:
        result = await pipeline.ingest_text(text, metadata=metadata)
    except Exception as exc:  # noqa: BLE001
        return f"error: ingestion failed: {exc}"
    else:
        return (
            f"Ingested: {result.document_id}, {result.chunk_count} chunks, "
            f"{result.entity_count} entities, {result.edge_count} edges "
            f"(status: {result.status})"
        )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_entities(
    ctx: Context,
    entity_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[EntityInfo] | str:
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
        entities = await asyncio.to_thread(gs.list_entities, entity_type=et)
    else:
        entities = await asyncio.to_thread(gs.list_entities)

    page = entities[offset : offset + limit]
    return [
        {"name": e.name, "entity_type": e.entity_type, "description": e.description}
        for e in page
    ]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_stats(ctx: Context) -> StatsResult:
    """Get knowledge base summary statistics."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    if gs is None:
        msg = "error: graph store not available"
        raise ToolError(msg)
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return {"documents": doc_count, "entities": entity_count, "edges": edge_count}


async def knowledge_stats(ctx: Context) -> str:
    """Return knowledge base statistics (callable directly with ctx for testing)."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return (
        f"Knowledge base: {doc_count} documents, {entity_count} entities, "
        f"{edge_count} edges"
    )


@mcp.resource("knowledge://stats")
async def _knowledge_stats_bridge() -> str:
    """MCP-registered concrete resource for knowledge://stats (zero-arg for FastMCP compat)."""
    if _app_context is None or _app_context.graph_store is None:
        return "Knowledge base: 0 documents, 0 entities, 0 edges"
    gs = _app_context.graph_store
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return (
        f"Knowledge base: {doc_count} documents, {entity_count} entities, "
        f"{edge_count} edges"
    )


async def knowledge_stats_resource(ctx: Context | None = None) -> str:
    """Return knowledge base statistics; accepts optional ctx for direct invocation."""
    if ctx is not None:
        app_ctx: AppContext = ctx.request_context.lifespan_context
        gs = app_ctx.graph_store
        counts_fn = gs.get_counts
    else:
        counts_fn = lambda: (0, 0, 0)  # noqa: E731
    doc_count, entity_count, edge_count = await asyncio.to_thread(counts_fn)
    return (
        f"Knowledge base: {doc_count} documents, {entity_count} entities, "
        f"{edge_count} edges"
    )
