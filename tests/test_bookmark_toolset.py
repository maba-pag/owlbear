"""Tests for BookmarkToolset — agent tools for bookmark management.

Covers bookmark_source and list_bookmarks tool wrappers with mocked
BookmarkPipeline and BookmarkStore. Verifies output formatting,
error handling, and filter delegation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.bookmark import Bookmark
from owlbear.memory.knowledge.bookmark_pipeline import BookmarkResult
from owlbear.memory.knowledge.evaluator import EvaluationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bookmark(  # noqa: PLR0913
    *,
    url: str = "https://example.com",
    title: str = "Example",
    tags: list[str] | None = None,
    relevance_score: float = 0.85,
    reason: str | None = None,
    scope: str = "global",
    document_id: str | None = None,
) -> Bookmark:
    """Build a :class:`Bookmark` with sensible defaults."""
    return Bookmark(
        url=url,
        title=title,
        tags=tags or [],
        relevance_score=relevance_score,
        reason=reason,
        scope=scope,
        document_id=document_id,
        created_at="2026-03-01T10:00:00+00:00",
        updated_at="2026-03-01T10:00:00+00:00",
    )


def _make_evaluation(
    *,
    relevance_score: float = 0.85,
    tags: list[str] | None = None,
    summary: str = "Useful resource about testing.",
    worth_ingesting: bool = True,
) -> EvaluationResult:
    """Build an :class:`EvaluationResult` with sensible defaults."""
    return EvaluationResult(
        relevance_score=relevance_score,
        tags=tags or ["testing"],
        summary=summary,
        worth_ingesting=worth_ingesting,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pipeline() -> MagicMock:
    """Mock satisfying BookmarkPipeline interface."""
    pipeline = MagicMock()
    pipeline.process = AsyncMock()
    return pipeline


@pytest.fixture
def mock_store() -> MagicMock:
    """Mock satisfying BookmarkStore interface."""
    store = MagicMock()
    store.list = MagicMock(return_value=[])
    return store


@pytest.fixture
def toolset(mock_pipeline: MagicMock, mock_store: MagicMock) -> object:
    """Create a BookmarkToolset with mocked dependencies."""
    from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

    return BookmarkToolset(pipeline=mock_pipeline, store=mock_store)


# ---------------------------------------------------------------------------
# Subclass check
# ---------------------------------------------------------------------------

class TestSubclass:
    """BookmarkToolset must subclass FunctionToolset."""

    def test_is_function_toolset_subclass(self, toolset: object) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        assert isinstance(toolset, FunctionToolset)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    """Verify constructor wiring."""

    def test_accepts_pipeline_and_store(
        self,
        mock_pipeline: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts = BookmarkToolset(pipeline=mock_pipeline, store=mock_store)
        assert ts is not None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """Verify exactly 2 tools are registered."""

    def test_registers_two_tools(self, toolset: object) -> None:
        assert len(toolset.tools) == 2  # type: ignore[attr-defined]

    def test_tool_names(self, toolset: object) -> None:
        names = set(toolset.tools.keys())  # type: ignore[attr-defined]
        assert names == {"bookmark_source", "list_bookmarks"}


# ---------------------------------------------------------------------------
# bookmark_source — happy path (high score, ingested)
# ---------------------------------------------------------------------------

class TestBookmarkSourceHappyPath:
    """bookmark_source delegates to pipeline.process and formats result."""

    @pytest.mark.anyio
    async def test_high_score_ingested(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        bm = _make_bookmark(
            url="https://docs.python.org",
            title="Python Docs",
            tags=["python", "docs"],
            relevance_score=0.92,
            document_id="doc-123",
        )
        ev = _make_evaluation(
            relevance_score=0.92,
            tags=["python", "docs"],
            summary="Official Python documentation.",
        )
        mock_pipeline.process.return_value = BookmarkResult(
            url="https://docs.python.org",
            bookmark=bm,
            evaluation=ev,
            ingested=True,
        )

        result = await ts._bookmark_source(
            url="https://docs.python.org",
            reason="Need Python reference",
        )

        # Verify delegation
        mock_pipeline.process.assert_awaited_once_with(
            "https://docs.python.org", reason="Need Python reference",
        )

        # Verify output is a readable string (not raw object repr)
        assert isinstance(result, str)
        assert "https://docs.python.org" in result
        assert "0.92" in result
        assert "ingested" in result.lower()


# ---------------------------------------------------------------------------
# bookmark_source — low score (not ingested but bookmarked)
# ---------------------------------------------------------------------------

class TestBookmarkSourceLowScore:
    """bookmark_source with low score: saved but not ingested."""

    @pytest.mark.anyio
    async def test_low_score_not_ingested(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        bm = _make_bookmark(
            url="https://blog.example.com",
            title="Tangential blog post",
            relevance_score=0.3,
        )
        ev = _make_evaluation(
            relevance_score=0.3,
            summary="Tangential blog post about cooking.",
            worth_ingesting=False,
        )
        mock_pipeline.process.return_value = BookmarkResult(
            url="https://blog.example.com",
            bookmark=bm,
            evaluation=ev,
            ingested=False,
        )

        result = await ts._bookmark_source(url="https://blog.example.com")

        assert isinstance(result, str)
        assert "https://blog.example.com" in result
        assert "0.3" in result
        # Should indicate it was NOT ingested
        assert "not ingested" in result.lower() or "bookmarked" in result.lower()


# ---------------------------------------------------------------------------
# bookmark_source — duplicate URL (skipped)
# ---------------------------------------------------------------------------

class TestBookmarkSourceDuplicate:
    """bookmark_source with duplicate URL: skipped with reason."""

    @pytest.mark.anyio
    async def test_duplicate_skipped(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        existing_bm = _make_bookmark(url="https://already.there")
        mock_pipeline.process.return_value = BookmarkResult(
            url="https://already.there",
            bookmark=existing_bm,
            skipped_reason="Already bookmarked in this scope",
        )

        result = await ts._bookmark_source(url="https://already.there")

        assert isinstance(result, str)
        assert "already" in result.lower() or "skipped" in result.lower()


# ---------------------------------------------------------------------------
# bookmark_source — error handling
# ---------------------------------------------------------------------------

class TestBookmarkSourceError:
    """bookmark_source handles pipeline errors gracefully."""

    @pytest.mark.anyio
    async def test_extraction_failure(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        mock_pipeline.process.return_value = BookmarkResult(
            url="https://broken.site",
            skipped_reason="Failed to extract content from https://broken.site",
        )

        result = await ts._bookmark_source(url="https://broken.site")

        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()

    @pytest.mark.anyio
    async def test_pipeline_exception(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        """When pipeline.process raises, bookmark_source returns error string."""
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        mock_pipeline.process.side_effect = RuntimeError("network timeout")

        result = await ts._bookmark_source(url="https://timeout.site")

        assert isinstance(result, str)
        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# list_bookmarks — with results
# ---------------------------------------------------------------------------

class TestListBookmarksWithResults:
    """list_bookmarks returns formatted list of bookmarks."""

    def test_formats_bookmarks(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        mock_store.list.return_value = [
            _make_bookmark(
                url="https://docs.python.org",
                title="Python Docs",
                tags=["python", "docs"],
                relevance_score=0.92,
            ),
            _make_bookmark(
                url="https://blog.example.com",
                title="Example Blog",
                tags=["blog"],
                relevance_score=0.45,
            ),
        ]

        result = ts._list_bookmarks()

        assert isinstance(result, str)
        assert "https://docs.python.org" in result
        assert "Python Docs" in result
        assert "0.92" in result
        assert "https://blog.example.com" in result
        assert "Example Blog" in result
        assert "0.45" in result


# ---------------------------------------------------------------------------
# list_bookmarks — empty
# ---------------------------------------------------------------------------

class TestListBookmarksEmpty:
    """list_bookmarks returns informative message when empty."""

    def test_no_bookmarks(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]
        mock_store.list.return_value = []

        result = ts._list_bookmarks()

        assert isinstance(result, str)
        assert "no bookmarks" in result.lower()


# ---------------------------------------------------------------------------
# list_bookmarks — tag filter
# ---------------------------------------------------------------------------

class TestListBookmarksTagFilter:
    """list_bookmarks passes tag filter to store.list()."""

    def test_passes_tag_to_store(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]
        mock_store.list.return_value = []

        ts._list_bookmarks(tag="python")

        mock_store.list.assert_called_once_with(tag="python", min_score=None)


# ---------------------------------------------------------------------------
# list_bookmarks — min_score filter
# ---------------------------------------------------------------------------

class TestListBookmarksMinScoreFilter:
    """list_bookmarks passes min_score filter to store.list()."""

    def test_passes_min_score_to_store(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]
        mock_store.list.return_value = []

        ts._list_bookmarks(min_score=0.7)

        mock_store.list.assert_called_once_with(tag=None, min_score=0.7)

    def test_passes_both_filters(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]
        mock_store.list.return_value = []

        ts._list_bookmarks(tag="docs", min_score=0.5)

        mock_store.list.assert_called_once_with(tag="docs", min_score=0.5)


# ---------------------------------------------------------------------------
# Output formatting — readable strings, not raw objects
# ---------------------------------------------------------------------------

class TestOutputFormatting:
    """Tool outputs must be readable strings, not raw object reprs."""

    @pytest.mark.anyio
    async def test_bookmark_source_output_is_readable(
        self,
        toolset: object,
        mock_pipeline: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        bm = _make_bookmark(
            url="https://example.com/article",
            title="Great Article",
            tags=["ai", "ml"],
            relevance_score=0.88,
        )
        ev = _make_evaluation(relevance_score=0.88, tags=["ai", "ml"])
        mock_pipeline.process.return_value = BookmarkResult(
            url="https://example.com/article",
            bookmark=bm,
            evaluation=ev,
            ingested=True,
        )

        result = await ts._bookmark_source(url="https://example.com/article")

        # Must not contain Pydantic model repr
        assert "BookmarkResult(" not in result
        assert "Bookmark(" not in result
        # Must be a human-readable string
        assert "https://example.com/article" in result

    def test_list_bookmarks_output_is_readable(
        self,
        toolset: object,
        mock_store: MagicMock,
    ) -> None:
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset

        ts: BookmarkToolset = toolset  # type: ignore[assignment]

        mock_store.list.return_value = [
            _make_bookmark(url="https://a.com", title="A"),
            _make_bookmark(url="https://b.com", title="B"),
        ]

        result = ts._list_bookmarks()

        # Must not contain Pydantic model repr
        assert "Bookmark(" not in result
        assert "[Bookmark" not in result
        # Must be readable
        assert "https://a.com" in result
        assert "https://b.com" in result
