"""BookmarkToolset — agent tools for evaluating and listing bookmarks.

Provides two tools:

* ``bookmark_source`` — evaluate a URL via :class:`BookmarkPipeline` and save it.
* ``list_bookmarks`` — list stored bookmarks with optional tag/score filters.

Usage::

    from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

    toolset = BookmarkToolset(pipeline=pipeline, store=store)
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from typing import ClassVar

    from owlbear.memory.knowledge.bookmark import BookmarkStore
    from owlbear.memory.knowledge.bookmark_pipeline import BookmarkPipeline

__all__ = ["BookmarkToolset"]

logger = logging.getLogger(__name__)


class BookmarkToolset(FunctionToolset):
    """FunctionToolset exposing bookmark_source and list_bookmarks tools.

    Args:
        pipeline: :class:`BookmarkPipeline` for URL evaluation and storage.
        store: :class:`BookmarkStore` for querying saved bookmarks.
    """

    tool_alias: ClassVar[str] = "bookmark"

    def __init__(
        self,
        pipeline: BookmarkPipeline,
        store: BookmarkStore,
    ) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._store = store
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register bookmark tools on this toolset."""
        self.add_function(
            self._bookmark_source,
            name="bookmark_source",
            description=(
                "Evaluate a URL for relevance, optionally ingest it into the "
                "knowledge base, and save it as a bookmark. Returns a readable "
                "summary of the result."
            ),
        )
        self.add_function(
            self._list_bookmarks,
            name="list_bookmarks",
            description=(
                "List saved bookmarks, optionally filtered by tag and/or minimum relevance score."
            ),
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _bookmark_source(
        self,
        url: str,
        reason: str | None = None,
    ) -> str:
        """Evaluate and bookmark a URL.

        Args:
            url: The URL to evaluate and bookmark.
            reason: Optional reason for bookmarking this URL.

        Returns:
            Human-readable summary of the bookmark result.
        """
        try:
            result = await self._pipeline.process(url, reason=reason)
        except Exception:  # noqa: BLE001
            logger.warning("BookmarkPipeline error for %s", url, exc_info=True)
            return f"Error: failed to process {url}"

        # Skipped (duplicate or extraction failure)
        if result.skipped_reason:
            return f"Skipped: {url}\nReason: {result.skipped_reason}"

        # Normal result — format readable output
        bm = result.bookmark
        title = bm.title if bm else url
        score = f"{result.evaluation.relevance_score}" if result.evaluation else "N/A"
        tags = ", ".join(bm.tags) if bm and bm.tags else "none"
        status = "ingested" if result.ingested else "not ingested (bookmarked only)"

        lines = [
            f"Bookmarked: {url}",
            f"Title: {title}",
            f"Score: {score}",
            f"Tags: {tags}",
            f"Status: {status}",
        ]
        if result.evaluation and result.evaluation.summary:
            lines.append(f"Summary: {result.evaluation.summary}")
        return "\n".join(lines)

    def _list_bookmarks(
        self,
        tag: str | None = None,
        min_score: float | None = None,
    ) -> str:
        """List saved bookmarks with optional filters.

        Args:
            tag: Filter bookmarks by this tag.
            min_score: Minimum relevance score threshold.

        Returns:
            Formatted list of bookmarks, or a message if none found.
        """
        bookmarks = self._store.list(tag=tag, min_score=min_score)

        if not bookmarks:
            return "No bookmarks found."

        lines: list[str] = []
        for bm in bookmarks:
            tags = ", ".join(bm.tags) if bm.tags else "none"
            lines.append(f"- [{bm.title}]({bm.url}) — score: {bm.relevance_score}, tags: {tags}")
        return "\n".join(lines)
