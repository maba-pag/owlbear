"""Tests for KnowledgeSourceToolset — agent tools for source management.

Covers add_source, list_sources, refresh_source, tool registration,
constructor, and error handling — all with mocked dependencies.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.models import KnowledgeSource, SourceType
from owlbear.memory.knowledge.refresh import RefreshResult

# ---------------------------------------------------------------------------
# Fixtures — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_source_store() -> MagicMock:
    """Mock satisfying KnowledgeSourceStore interface."""
    store = MagicMock()
    store.create = MagicMock()
    store.list_all = MagicMock(return_value=[])
    store.get_by_name = MagicMock(return_value=None)
    return store


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Mock satisfying RefreshOrchestrator interface."""
    return MagicMock()


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Provide a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def toolset(
    mock_source_store: MagicMock,
    mock_orchestrator: MagicMock,
    workspace_root: Path,
) -> object:
    """Create a KnowledgeSourceToolset with all mocked dependencies."""
    from owlbear.tools.knowledge_source import KnowledgeSourceToolset

    return KnowledgeSourceToolset(
        store=mock_source_store,
        orchestrator=mock_orchestrator,
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# Subclass check
# ---------------------------------------------------------------------------


class TestSubclass:
    """KnowledgeSourceToolset must subclass FunctionToolset."""

    def test_is_function_toolset_subclass(self, toolset: object) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        assert isinstance(toolset, FunctionToolset)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """Verify constructor accepts expected arguments."""

    def test_accepts_required_args(
        self,
        mock_source_store: MagicMock,
        mock_orchestrator: MagicMock,
    ) -> None:
        """Constructor works without workspace_root."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts = KnowledgeSourceToolset(
            store=mock_source_store,
            orchestrator=mock_orchestrator,
        )
        assert ts is not None

    def test_accepts_workspace_root(
        self,
        mock_source_store: MagicMock,
        mock_orchestrator: MagicMock,
        workspace_root: Path,
    ) -> None:
        """Constructor accepts optional workspace_root."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts = KnowledgeSourceToolset(
            store=mock_source_store,
            orchestrator=mock_orchestrator,
            workspace_root=workspace_root,
        )
        assert ts is not None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Verify the toolset registers exactly 3 tools."""

    def test_registers_three_tools(self, toolset: object) -> None:
        assert len(toolset.tools) == 3  # type: ignore[attr-defined]

    def test_tool_names(self, toolset: object) -> None:
        names = set(toolset.tools.keys())  # type: ignore[attr-defined]
        assert names == {"add_source", "list_sources", "refresh_source"}


# ---------------------------------------------------------------------------
# add_source
# ---------------------------------------------------------------------------


class TestAddSource:
    """Test add_source tool."""

    def test_creates_source_via_store(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """add_source should create a KnowledgeSource and return confirmation."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        result = ts._add_source(
            name="my-urls",
            source_type="url_list",
            config_json='{"urls": ["https://example.com"]}',
            scope="global",
        )

        assert result == "Source my-urls (url_list) created."
        mock_source_store.create.assert_called_once()
        created_source = mock_source_store.create.call_args[0][0]
        assert isinstance(created_source, KnowledgeSource)
        assert created_source.name == "my-urls"
        assert created_source.source_type == SourceType.URL_LIST
        assert created_source.config == {"urls": ["https://example.com"]}
        assert created_source.scope == "global"

    def test_default_scope_is_global(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """add_source uses 'global' as default scope."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        result = ts._add_source(
            name="test",
            source_type="file_glob",
            config_json='{"pattern": "*.md"}',
        )

        assert "created" in result
        created_source = mock_source_store.create.call_args[0][0]
        assert created_source.scope == "global"

    def test_invalid_source_type_returns_error(
        self,
        toolset: object,
    ) -> None:
        """add_source with invalid source_type returns error string, not exception."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        result = ts._add_source(
            name="bad",
            source_type="invalid_type",
            config_json="{}",
        )

        assert "error" in result.lower() or "invalid" in result.lower()

    def test_invalid_json_returns_error(
        self,
        toolset: object,
    ) -> None:
        """add_source with malformed JSON returns error string, not exception."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        result = ts._add_source(
            name="bad-json",
            source_type="url_list",
            config_json="not valid json {{{",
        )

        assert "error" in result.lower() or "invalid" in result.lower()

    def test_crawl_source_type(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """add_source correctly creates crawl source type."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        result = ts._add_source(
            name="my-crawl",
            source_type="crawl",
            config_json='{"start_urls": ["https://docs.example.com"]}',
            scope="project:demo",
        )

        assert result == "Source my-crawl (crawl) created."
        created_source = mock_source_store.create.call_args[0][0]
        assert created_source.source_type == SourceType.CRAWL
        assert created_source.scope == "project:demo"


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------


class TestListSources:
    """Test list_sources tool."""

    def test_returns_no_sources_when_empty(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """list_sources returns 'No sources registered.' when empty."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        mock_source_store.list_all.return_value = []

        result = ts._list_sources()

        assert result == "No sources registered."

    def test_returns_formatted_list(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """list_sources returns formatted list with name, type, enabled, last_refreshed_at."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        mock_source_store.list_all.return_value = [
            KnowledgeSource(
                name="docs-urls",
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://example.com"]},
                scope="global",
                enabled=True,
                last_refreshed_at="2026-03-01T12:00:00+00:00",
                created_at="2026-03-01T10:00:00+00:00",
                updated_at="2026-03-01T12:00:00+00:00",
            ),
            KnowledgeSource(
                name="code-files",
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "**/*.py"},
                scope="project:alpha",
                enabled=False,
                last_refreshed_at=None,
                created_at="2026-03-01T10:00:00+00:00",
                updated_at="2026-03-01T10:00:00+00:00",
            ),
        ]

        result = ts._list_sources()

        assert "docs-urls" in result
        assert "url_list" in result
        assert "yes" in result.lower()  # enabled: yes
        assert "2026-03-01T12:00:00+00:00" in result

        assert "code-files" in result
        assert "file_glob" in result
        assert "no" in result.lower()  # enabled: no
        assert "never" in result.lower()  # last refresh: never

    def test_list_sources_with_scope_filter(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """list_sources passes scope filter to store.list_all()."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        mock_source_store.list_all.return_value = []

        ts._list_sources(scope="project:demo")

        mock_source_store.list_all.assert_called_once_with("project:demo")

    def test_list_sources_no_scope_passes_none(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """list_sources without scope passes None to store.list_all()."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        mock_source_store.list_all.return_value = []

        ts._list_sources()

        mock_source_store.list_all.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# refresh_source
# ---------------------------------------------------------------------------


class TestRefreshSource:
    """Test refresh_source tool."""

    @pytest.mark.anyio
    async def test_refreshes_named_source(
        self,
        toolset: object,
        mock_source_store: MagicMock,
        mock_orchestrator: MagicMock,
    ) -> None:
        """refresh_source triggers orchestrator.refresh and returns summary."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        source = KnowledgeSource(
            name="my-urls",
            source_type=SourceType.URL_LIST,
            config={"urls": ["https://example.com"]},
            scope="global",
            created_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        mock_source_store.get_by_name.return_value = source
        from unittest.mock import AsyncMock

        mock_orchestrator.refresh = AsyncMock(
            return_value=RefreshResult(
                source_id=source.id,
                refreshed=3,
                skipped=1,
                failed=0,
            )
        )

        result = await ts._refresh_source(name="my-urls")

        assert result == "Refreshed my-urls: 3 ingested, 1 skipped, 0 failed"
        mock_source_store.get_by_name.assert_called_once_with("my-urls")
        mock_orchestrator.refresh.assert_called_once_with(source)

    @pytest.mark.anyio
    async def test_nonexistent_source_returns_error(
        self,
        toolset: object,
        mock_source_store: MagicMock,
    ) -> None:
        """refresh_source with non-existent name returns error string, not exception."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        mock_source_store.get_by_name.return_value = None

        result = await ts._refresh_source(name="nonexistent")

        assert result == "Source nonexistent not found."

    @pytest.mark.anyio
    async def test_refresh_source_with_failures(
        self,
        toolset: object,
        mock_source_store: MagicMock,
        mock_orchestrator: MagicMock,
    ) -> None:
        """refresh_source summary includes failure counts."""
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset

        ts: KnowledgeSourceToolset = toolset  # type: ignore[assignment]
        source = KnowledgeSource(
            name="flaky",
            source_type=SourceType.URL_LIST,
            config={},
            scope="global",
            created_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        mock_source_store.get_by_name.return_value = source
        from unittest.mock import AsyncMock

        mock_orchestrator.refresh = AsyncMock(
            return_value=RefreshResult(
                source_id=source.id,
                refreshed=2,
                skipped=0,
                failed=3,
            )
        )

        result = await ts._refresh_source(name="flaky")

        assert result == "Refreshed flaky: 2 ingested, 0 skipped, 3 failed"
