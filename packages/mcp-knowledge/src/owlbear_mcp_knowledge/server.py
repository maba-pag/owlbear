"""FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP
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

_DEFAULT_KB_PATH = "data/knowledge/knowledge.db"
_DEFAULT_MODEL = "gpt-4o-mini"


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


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Initialise knowledge-base services; close the DB connection on exit."""
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
        yield AppContext(
            query_service=qs,
            graph_store=gs,
            ingest_pipeline=pipeline,
            source_store=source_store,
        )
    finally:
        conn.close()


mcp = FastMCP("owlbear-knowledge", lifespan=app_lifespan)


@mcp.tool()
async def search_knowledge(ctx: Context, query: str, limit: int = 5) -> str:
    """Search the knowledge base for relevant context."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    qs = app_ctx.query_service
    if qs is None:
        return "Knowledge service not available."
    results = await qs.query(query, top_k=limit)
    if not results:
        return "No relevant knowledge found."
    lines = [f"- {r.title} ({r.score:.2f}): {r.snippet[:200]}" for r in results]
    return "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> str:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    sources = await asyncio.to_thread(store.list_all, scope=scope)
    if not sources:
        return "No sources found."
    lines = [f"- {s.name} ({s.source_type}): scope={s.scope}" for s in sources]
    return "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False))
async def ingest_document(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Ingest a text document into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.ingest_pipeline
    try:
        result = await pipeline.ingest_text(text, metadata=metadata)
    except Exception as exc:  # noqa: BLE001
        return f"Ingestion failed: {exc}"
    else:
        return (
            f"Ingested: {result.document_id}, {result.chunk_count} chunks, "
            f"{result.entity_count} entities, {result.edge_count} edges "
            f"(status: {result.status})"
        )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_entities(
    ctx: Context,
    entity_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> str:
    """List entities in the knowledge graph."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store

    if entity_type is not None:
        try:
            et = EntityType(entity_type)
        except ValueError:
            valid = ", ".join(e.value for e in EntityType)
            return f"Invalid entity_type '{entity_type}'. Valid types: {valid}"
        entities = await asyncio.to_thread(gs.list_entities, entity_type=et)
    else:
        entities = await asyncio.to_thread(gs.list_entities)

    if not entities:
        return "No entities found."

    total = len(entities)
    page = entities[offset : offset + limit]
    header = f"Entities ({offset}-{min(offset + limit, total)} of {total}):"
    lines = [header, *[f"- {e.name} ({e.entity_type}): {e.description}" for e in page]]
    return "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_stats(ctx: Context) -> str:
    """Get knowledge base summary statistics."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return (
        f"Knowledge base: {doc_count} documents, {entity_count} entities, "
        f"{edge_count} edges"
    )


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
async def knowledge_stats_resource() -> str:
    """Register knowledge://stats URI for MCP resource discovery."""
    return "Knowledge base: 0 documents, 0 entities, 0 edges"
