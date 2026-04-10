"""FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline
from owlbear_knowledge.bookmark_store import BookmarkStore
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.consolidation import ConsolidationService, TextCompletionFn
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.evaluator import EvaluateFn, EvaluationResult, SourceEvaluator
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.llm_extractor import LLMExtractor
from owlbear_knowledge.models import EntityType
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.retrieval import GraphAugmentedRetriever
from owlbear_knowledge.schema import init_db as _schema_init_db
from owlbear_knowledge.scope_transfer import export_scope as _core_export_scope
from owlbear_knowledge.scope_transfer import import_scope as _core_import_scope
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
    entity_type: str | None


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

    conn: sqlite3.Connection
    query_service: KnowledgeQueryService | None
    graph_store: GraphStore | None
    ingest_pipeline: IngestPipeline | None
    source_store: KnowledgeSourceStore | None
    bookmark_pipeline: BookmarkPipeline | None
    bookmark_store: BookmarkStore | None
    refresh_orchestrator: RefreshOrchestrator | None = None
    consolidation_service: ConsolidationService | None = None


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


def make_text_completion_fn(model: str) -> TextCompletionFn:
    """Return a TextCompletionFn backed by a PydanticAI Agent with output_type=str.

    Falls back to a no-op stub when pydantic-ai is absent.
    """
    try:
        import pydantic_ai  # noqa: PLC0415

        agent = pydantic_ai.Agent(model, output_type=str)

        async def _complete(prompt: str) -> str:
            result = await agent.run(prompt)
            return result.output

    except Exception:  # noqa: BLE001

        async def _complete(_prompt: str) -> str:  # type: ignore[misc]
            return ""

    return _complete


def make_evaluate_fn(model: str) -> EvaluateFn:
    """Return an EvaluateFn callable for the given model name.

    Delegates to ``make_pydantic_evaluate_fn`` when pydantic-ai is installed.
    Falls back to a neutral no-op stub when pydantic-ai is absent.
    """
    try:
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # noqa: PLC0415

        return make_pydantic_evaluate_fn(model)
    except Exception:  # noqa: BLE001

        async def _evaluate(_prompt: str) -> EvaluationResult:
            return EvaluationResult(
                relevance_score=0.5,
                summary="No project context available -- neutral evaluation.",
                worth_ingesting=True,
            )

        return _evaluate


async def _web_read(url: str) -> str | None:
    """Fetch a URL via httpx. Only http/https schemes allowed; redirects not followed."""
    from urllib.parse import urlparse  # noqa: PLC0415

    if urlparse(url).scheme.lower() not in {"http", "https"}:
        return None
    try:
        import httpx  # noqa: PLC0415

        async with httpx.AsyncClient(follow_redirects=False, timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception:  # noqa: BLE001
        return None


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
        model = os.environ.get("OWLBEAR_MODEL", _DEFAULT_MODEL)
        try:
            llm_extractor = LLMExtractor(model)
            extractor = EntityExtractor(model, extractor=llm_extractor)
        except Exception:  # noqa: BLE001
            extractor = EntityExtractor(model)
        gar = GraphAugmentedRetriever(vs, gs, emb)
        qs = KnowledgeQueryService(vector_store=vs, graph_store=gs, embedding_provider=emb, retriever=gar)
        doc_store = DocumentStore(conn, gs, vs, emb)
        chunker = TextChunker()
        pipeline = IngestPipeline(doc_store, extractor, chunker)
        source_store = KnowledgeSourceStore(conn)
        bookmark_store = BookmarkStore(conn)
        evaluator = SourceEvaluator(llm_fn=make_evaluate_fn(model))

        bookmark_pipeline = BookmarkPipeline(
            bookmark_store=bookmark_store,
            evaluator=evaluator,
            ingest_pipeline=pipeline,
            web_read_fn=_web_read,
        )
        refresh_orchestrator = RefreshOrchestrator(
            store=source_store,
            pipeline=pipeline,
            workspace_root=Path.cwd(),
        )
        try:
            consolidation_service: ConsolidationService | None = ConsolidationService(
                conn, make_text_completion_fn(model)
            )
        except Exception:  # noqa: BLE001
            consolidation_service = None
        ctx = AppContext(
            conn=conn,
            query_service=qs,
            graph_store=gs,
            ingest_pipeline=pipeline,
            source_store=source_store,
            bookmark_pipeline=bookmark_pipeline,
            bookmark_store=bookmark_store,
            refresh_orchestrator=refresh_orchestrator,
            consolidation_service=consolidation_service,
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
    "bookmark_source",
    "consolidate_knowledge",
    "export_scope",
    "get_stats",
    "import_scope",
    "ingest_document",
    "init_db",
    "list_bookmarks",
    "list_entities",
    "list_sources",
    "mcp",
    "refresh_source",
    "search_knowledge",
    "update_bookmark_tags",
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
    results = await qs.query(query, top_k=limit, scopes=scopes)
    return [{"title": r.title, "score": r.score, "snippet": r.snippet, "entity_type": r.entity_type} for r in results]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    sources = await asyncio.to_thread(store.list_all, scope=scope)
    return [{"name": s.name, "source_type": s.source_type, "scope": s.scope} for s in sources]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def ingest_document(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
    scope: str = "global",
) -> str:
    """Ingest a text document into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"
    try:
        result = await pipeline.ingest_text(text, metadata=metadata, scope=scope)
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
    scopes: list[str] | None = None,
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
    if gs is None:
        msg = "graph store not available"
        raise ToolError(msg)
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return {"documents": doc_count, "entities": entity_count, "edges": edge_count}


async def knowledge_stats(ctx: Context) -> str:
    """Return knowledge base statistics (callable directly with ctx for testing)."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


@mcp.resource("knowledge://stats")
async def _knowledge_stats_bridge() -> str:
    """MCP-registered concrete resource for knowledge://stats (zero-arg for FastMCP compat)."""
    if _app_context is None or _app_context.graph_store is None:
        return "Knowledge base: 0 documents, 0 entities, 0 edges"
    gs = _app_context.graph_store
    doc_count, entity_count, edge_count = await asyncio.to_thread(gs.get_counts)
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


async def knowledge_stats_resource(ctx: Context | None = None) -> str:
    """Return knowledge base statistics; accepts optional ctx for direct invocation."""
    if ctx is not None:
        app_ctx: AppContext = ctx.request_context.lifespan_context
        gs = app_ctx.graph_store
        counts_fn = gs.get_counts
    else:
        counts_fn = lambda: (0, 0, 0)  # noqa: E731
    doc_count, entity_count, edge_count = await asyncio.to_thread(counts_fn)
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def bookmark_source(ctx: Context, url: str, reason: str | None = None) -> str:
    """Bookmark a URL: evaluate and optionally ingest into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.bookmark_pipeline
    if pipeline is None:
        return f"error: bookmark pipeline not available for {url}"
    result = await pipeline.process(url, reason=reason)
    if result.skipped_reason is not None:
        return f"Skipped {url}: {result.skipped_reason}"
    score = result.evaluation.relevance_score if result.evaluation else "n/a"
    return f"Bookmarked {url} (score: {score}, ingested: {result.ingested})"


class BookmarkInfo(TypedDict):
    """A single bookmark entry."""

    url: str
    title: str | None
    relevance_score: float | None
    tags: list[str]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_bookmarks(
    ctx: Context,
    tag: str | None = None,
    min_score: float | None = None,
) -> list[BookmarkInfo]:
    """List bookmarks, optionally filtered by tag or minimum relevance score."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.bookmark_store
    if store is None:
        return []
    bookmarks = await asyncio.to_thread(store.list, tag=tag, min_score=min_score)
    return [{"url": b.url, "title": b.title, "relevance_score": b.relevance_score, "tags": b.tags} for b in bookmarks]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))
async def update_bookmark_tags(
    ctx: Context,
    url: str,
    tags: list[str],
    scope: str = "global",
) -> BookmarkInfo:
    """Update the tags on an existing bookmark."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.bookmark_store
    if store is None:
        msg = "bookmark store not available"
        raise ToolError(msg)
    bookmark = await asyncio.to_thread(store.get_by_url, url, scope)
    if bookmark is None:
        msg = f"bookmark not found for URL: {url}"
        raise ToolError(msg)
    await asyncio.to_thread(store.update_tags, bookmark.id, tags)
    return {"url": bookmark.url, "title": bookmark.title, "relevance_score": bookmark.relevance_score, "tags": tags}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def import_scope(
    ctx: Context,
    project_name: str,
    path: str | None = None,
) -> str:
    """Import a project-local knowledge snapshot into the global KB.

    Reads a portable SQLite file (default: ``.owlbear/knowledge/knowledge.db``)
    and ingests its documents into the global KB under ``scope="project:{project_name}"``.
    Duplicate documents (same content hash) are skipped.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    src = Path(path) if path is not None else None
    return await asyncio.to_thread(
        _core_import_scope,
        src,
        project_name,
        app_ctx.conn,
        workspace_root=Path.cwd(),
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def export_scope(
    ctx: Context,
    scope: str,
    output_path: str,
) -> str:
    """Export all knowledge for a scope to a portable SQLite file.

    Creates a new SQLite database at *output_path* containing only the rows
    matching *scope*.  Qdrant embeddings are excluded (re-embedded on import).
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await asyncio.to_thread(
        _core_export_scope,
        scope,
        Path(output_path),
        app_ctx.conn,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def refresh_source(ctx: Context, source_id: str) -> dict | str:
    """Trigger re-ingestion of a registered knowledge source by its ID.

    Returns a dict with source_id, refreshed, skipped, and failed counts on
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
    try:
        result = await orchestrator.refresh(source)
    except ValueError as exc:
        return f"error: {exc}"
    return {
        "source_id": result.source_id,
        "refreshed": result.refreshed,
        "skipped": result.skipped,
        "failed": result.failed,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def consolidate_knowledge(ctx: Context, batch_size: int = 50) -> str:
    """Trigger cross-document insight synthesis for unconsolidated knowledge chunks.

    Returns a human-readable summary of the consolidation result.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    svc = app_ctx.consolidation_service
    if svc is None:
        return "error: consolidation service not available"
    result = await svc.consolidate(batch_size=batch_size)
    if result == 0:
        return "No unconsolidated chunks available"
    return f"Consolidated: {result} insight created"
