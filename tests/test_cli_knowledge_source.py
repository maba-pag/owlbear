"""Tests for bearclaw knowledge-source CLI subcommands.

TDD red-phase: tests define expected behavior of the knowledge-source subcommand
group (add, list, show, refresh, remove) using CliRunner and mocked
KnowledgeSourceStore / RefreshOrchestrator.

See kanban tasks #431 (tests) and #385 (implementation) for acceptance criteria.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(  # noqa: PLR0913
    *,
    name: str = "my-source",
    source_type: str = "url_list",
    scope: str = "global",
    enabled: bool = True,
    priority: int = 0,
    config: dict | None = None,
    last_refreshed_at: str | None = None,
    last_error: str | None = None,
) -> MagicMock:
    """Build a mock KnowledgeSource with the given attributes."""
    src = MagicMock()
    src.id = "abc123"
    src.name = name
    src.source_type = source_type
    src.scope = scope
    src.enabled = enabled
    src.priority = priority
    src.config = config or {}
    src.last_refreshed_at = last_refreshed_at
    src.last_error = last_error
    src.created_at = "2026-01-01T00:00:00+00:00"
    src.updated_at = "2026-01-01T00:00:00+00:00"
    return src


def _mock_store(sources: list | None = None) -> MagicMock:
    """Build a mock KnowledgeSourceStore."""
    store = MagicMock()
    store.list_all.return_value = sources or []
    store.get_by_name.return_value = None
    store.create.return_value = None
    store.delete.return_value = True
    return store


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestKnowledgeSourceHelp:
    """The 'knowledge-source' subcommand group appears in CLI help."""

    def test_knowledge_source_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "knowledge-source" in result.output

    def test_knowledge_source_help_lists_subcommands(self) -> None:
        result = runner.invoke(app, ["knowledge-source", "--help"])
        assert result.exit_code == 0
        for cmd in ("add", "list", "show", "refresh", "remove"):
            assert cmd in result.output


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestKnowledgeSourceAdd:
    """bearclaw knowledge-source add — creates a new source."""

    @patch("bearclaw.cli._get_source_store")
    def test_add_url_list(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        result = runner.invoke(
            app,
            [
                "knowledge-source",
                "add",
                "--name",
                "docs",
                "--type",
                "url_list",
                "--urls",
                "https://example.com,https://other.com",
            ],
        )
        assert result.exit_code == 0
        assert "docs" in result.output
        store.create.assert_called_once()

        # Verify the KnowledgeSource passed to create
        created = store.create.call_args[0][0]
        assert created.name == "docs"
        assert str(created.source_type) == "url_list"
        assert created.config["urls"] == [
            "https://example.com",
            "https://other.com",
        ]

    @patch("bearclaw.cli._get_source_store")
    def test_add_crawl(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        result = runner.invoke(
            app,
            [
                "knowledge-source",
                "add",
                "--name",
                "site",
                "--type",
                "crawl",
                "--seeds",
                "https://docs.example.com",
                "--max-depth",
                "2",
                "--max-pages",
                "100",
            ],
        )
        assert result.exit_code == 0
        store.create.assert_called_once()

        created = store.create.call_args[0][0]
        assert str(created.source_type) == "crawl"
        assert created.config["seeds"] == ["https://docs.example.com"]
        assert created.config["max_depth"] == 2
        assert created.config["max_pages"] == 100

    @patch("bearclaw.cli._get_source_store")
    def test_add_file_glob(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        result = runner.invoke(
            app,
            [
                "knowledge-source",
                "add",
                "--name",
                "code",
                "--type",
                "file_glob",
                "--pattern",
                "src/**/*.py",
            ],
        )
        assert result.exit_code == 0
        store.create.assert_called_once()

        created = store.create.call_args[0][0]
        assert str(created.source_type) == "file_glob"
        assert created.config["pattern"] == "src/**/*.py"

    @patch("bearclaw.cli._get_source_store")
    def test_add_with_scope(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        result = runner.invoke(
            app,
            [
                "knowledge-source",
                "add",
                "--name",
                "local",
                "--type",
                "url_list",
                "--urls",
                "https://example.com",
                "--scope",
                "my-project",
            ],
        )
        assert result.exit_code == 0
        created = store.create.call_args[0][0]
        assert created.scope == "my-project"

    def test_add_url_list_requires_urls(self) -> None:
        """url_list type without --urls should fail."""
        with patch("bearclaw.cli._get_source_store") as mock_get_store:
            mock_get_store.return_value = _mock_store()
            result = runner.invoke(
                app,
                [
                    "knowledge-source",
                    "add",
                    "--name",
                    "bad",
                    "--type",
                    "url_list",
                ],
            )
            assert result.exit_code == 1
            assert "urls" in result.output.lower()

    def test_add_crawl_requires_seeds(self) -> None:
        """crawl type without --seeds should fail."""
        with patch("bearclaw.cli._get_source_store") as mock_get_store:
            mock_get_store.return_value = _mock_store()
            result = runner.invoke(
                app,
                [
                    "knowledge-source",
                    "add",
                    "--name",
                    "bad",
                    "--type",
                    "crawl",
                ],
            )
            assert result.exit_code == 1
            assert "seeds" in result.output.lower()

    def test_add_file_glob_requires_pattern(self) -> None:
        """file_glob type without --pattern should fail."""
        with patch("bearclaw.cli._get_source_store") as mock_get_store:
            mock_get_store.return_value = _mock_store()
            result = runner.invoke(
                app,
                [
                    "knowledge-source",
                    "add",
                    "--name",
                    "bad",
                    "--type",
                    "file_glob",
                ],
            )
            assert result.exit_code == 1
            assert "pattern" in result.output.lower()

    def test_add_invalid_type_errors(self) -> None:
        """An invalid --type value should fail."""
        result = runner.invoke(
            app,
            [
                "knowledge-source",
                "add",
                "--name",
                "bad",
                "--type",
                "invalid",
                "--urls",
                "http://x.com",
            ],
        )
        # Typer should reject the invalid choice or the code should error
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestKnowledgeSourceList:
    """bearclaw knowledge-source list — table output."""

    @patch("bearclaw.cli._get_source_store")
    def test_list_empty(self, mock_get_store: MagicMock) -> None:
        store = _mock_store(sources=[])
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "list"])
        assert result.exit_code == 0
        assert "No knowledge sources" in result.output

    @patch("bearclaw.cli._get_source_store")
    def test_list_shows_sources(self, mock_get_store: MagicMock) -> None:
        src = _make_source(name="docs", source_type="url_list")
        store = _mock_store(sources=[src])
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "list"])
        assert result.exit_code == 0
        assert "docs" in result.output
        assert "url_list" in result.output

    @patch("bearclaw.cli._get_source_store")
    def test_list_with_scope_filter(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        runner.invoke(
            app, ["knowledge-source", "list", "--scope", "my-project"]
        )
        store.list_all.assert_called_once_with(scope="my-project")

    @patch("bearclaw.cli._get_source_store")
    def test_list_table_has_headers(self, mock_get_store: MagicMock) -> None:
        src = _make_source()
        store = _mock_store(sources=[src])
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "list"])
        assert result.exit_code == 0
        assert "Name" in result.output
        assert "Type" in result.output
        assert "Scope" in result.output
        assert "Enabled" in result.output


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


class TestKnowledgeSourceShow:
    """bearclaw knowledge-source show NAME — full source details."""

    @patch("bearclaw.cli._get_source_store")
    def test_show_existing_source(self, mock_get_store: MagicMock) -> None:
        src = _make_source(
            name="docs",
            config={"urls": ["https://example.com"]},
            last_refreshed_at="2026-01-15T10:00:00+00:00",
        )
        store = _mock_store()
        store.get_by_name.return_value = src
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "show", "docs"])
        assert result.exit_code == 0
        assert "docs" in result.output
        assert "url_list" in result.output
        assert "example.com" in result.output

    @patch("bearclaw.cli._get_source_store")
    def test_show_nonexistent_source(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        store.get_by_name.return_value = None
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "show", "ghost"])
        assert result.exit_code == 1
        assert "ghost" in result.output.lower()

    @patch("bearclaw.cli._get_source_store")
    def test_show_displays_config_json(self, mock_get_store: MagicMock) -> None:
        src = _make_source(
            config={"urls": ["https://a.com", "https://b.com"]},
        )
        store = _mock_store()
        store.get_by_name.return_value = src
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "show", "my-source"])
        assert result.exit_code == 0
        # Config should be shown as JSON
        assert "https://a.com" in result.output


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


class TestKnowledgeSourceRefresh:
    """bearclaw knowledge-source refresh — invoke RefreshOrchestrator."""

    @patch("bearclaw.cli._make_refresh_orchestrator")
    @patch("bearclaw.cli._get_source_store")
    def test_refresh_single_source(
        self,
        mock_get_store: MagicMock,
        mock_make_orch: MagicMock,
    ) -> None:
        src = _make_source(name="docs")
        store = _mock_store()
        store.get_by_name.return_value = src
        mock_get_store.return_value = store

        orch = MagicMock()
        refresh_result = MagicMock()
        refresh_result.refreshed = 3
        refresh_result.skipped = 1
        refresh_result.failed = 0
        refresh_result.errors = []
        orch.refresh = AsyncMock(return_value=refresh_result)
        mock_make_orch.return_value = orch

        result = runner.invoke(
            app, ["knowledge-source", "refresh", "--name", "docs"]
        )
        assert result.exit_code == 0
        assert "3" in result.output  # refreshed count
        orch.refresh.assert_awaited_once()

    @patch("bearclaw.cli._make_refresh_orchestrator")
    @patch("bearclaw.cli._get_source_store")
    def test_refresh_all_sources(
        self,
        mock_get_store: MagicMock,
        mock_make_orch: MagicMock,
    ) -> None:
        store = _mock_store()
        mock_get_store.return_value = store

        orch = MagicMock()
        r1 = MagicMock(refreshed=2, skipped=0, failed=0, errors=[])
        r2 = MagicMock(refreshed=1, skipped=1, failed=0, errors=[])
        orch.refresh_all = AsyncMock(return_value=[r1, r2])
        mock_make_orch.return_value = orch

        result = runner.invoke(
            app, ["knowledge-source", "refresh", "--all"]
        )
        assert result.exit_code == 0
        orch.refresh_all.assert_awaited_once()

    @patch("bearclaw.cli._get_source_store")
    def test_refresh_nonexistent_source(
        self, mock_get_store: MagicMock
    ) -> None:
        store = _mock_store()
        store.get_by_name.return_value = None
        mock_get_store.return_value = store

        result = runner.invoke(
            app, ["knowledge-source", "refresh", "--name", "ghost"]
        )
        assert result.exit_code == 1
        assert "ghost" in result.output.lower()

    def test_refresh_requires_name_or_all(self) -> None:
        """Must provide --name or --all, not neither."""
        with patch("bearclaw.cli._get_source_store") as mock_get_store:
            mock_get_store.return_value = _mock_store()
            result = runner.invoke(app, ["knowledge-source", "refresh"])
            assert result.exit_code == 1


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestKnowledgeSourceRemove:
    """bearclaw knowledge-source remove NAME — delete source."""

    @patch("bearclaw.cli._get_source_store")
    def test_remove_existing(self, mock_get_store: MagicMock) -> None:
        src = _make_source(name="old-source")
        store = _mock_store()
        store.get_by_name.return_value = src
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "remove", "old-source"])
        assert result.exit_code == 0
        assert "old-source" in result.output
        store.delete.assert_called_once_with(src.id)

    @patch("bearclaw.cli._get_source_store")
    def test_remove_nonexistent(self, mock_get_store: MagicMock) -> None:
        store = _mock_store()
        store.get_by_name.return_value = None
        mock_get_store.return_value = store

        result = runner.invoke(app, ["knowledge-source", "remove", "ghost"])
        assert result.exit_code == 1
        assert "ghost" in result.output.lower()
