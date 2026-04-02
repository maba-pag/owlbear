"""Bookmark MCP tools and associated AppContext for owlbear-mcp-knowledge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline
    from owlbear_knowledge.bookmark_store import BookmarkStore
    from owlbear_knowledge.query_service import KnowledgeQueryService


@dataclass
class AppContext:
    """Runtime context for bookmark MCP tools."""

    query_service: KnowledgeQueryService | None = field(default=None)
    bookmark_pipeline: BookmarkPipeline | None = field(default=None)
    bookmark_store: BookmarkStore | None = field(default=None)


async def bookmark_source(
    ctx: AppContext,
    url: str,
    reason: str | None = None,
) -> dict[str, Any] | str:
    """Bookmark a URL by running it through the BookmarkPipeline.

    Args:
        ctx: AppContext with a wired bookmark_pipeline.
        url: The URL to bookmark.
        reason: Optional reason for bookmarking.

    Returns:
        A dict summarising the BookmarkResult, or an error string.
    """
    pipeline = ctx.bookmark_pipeline
    if pipeline is None:
        return "error: bookmark_pipeline not available"
    result = await pipeline.process(url, reason=reason)
    return result.model_dump()


async def list_bookmarks(
    ctx: AppContext,
    tag: str | None = None,
    min_score: float | None = None,
) -> list[dict[str, Any]] | str:
    """List bookmarks, optionally filtered by tag and minimum relevance score.

    Args:
        ctx: AppContext with a wired bookmark_store.
        tag: Optional tag filter.
        min_score: Optional minimum relevance_score threshold.

    Returns:
        A list of bookmark dicts, or an error string.
    """
    store = ctx.bookmark_store
    if store is None:
        return "error: bookmark_store not available"
    bookmarks = store.list(tag=tag, min_score=min_score)
    return [b.model_dump() for b in bookmarks]


__all__ = [
    "AppContext",
    "bookmark_source",
    "list_bookmarks",
]
