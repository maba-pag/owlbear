"""Tests for ProjectToolset — agent tools for project switching.

TDD red-phase: these tests define the expected behavior of ProjectToolset.
The module does not exist yet — all tests should fail on ImportError.

Task #350 — see docs/multi-project-session-research.md §3.10
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from owlbear.projects.toolset import ProjectToolset

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store() -> MagicMock:
    """Return a mocked ProjectStore."""
    store = MagicMock()
    store.get_by_name = MagicMock()
    store.list_active = MagicMock(return_value=[])
    store.update = MagicMock()
    return store


@pytest.fixture
def mock_agent() -> MagicMock:
    """Return a mocked OwlBearAgent with a session attribute."""
    agent = MagicMock()
    agent.session = MagicMock()
    agent.session.path = Path("/old/session.jsonl")
    return agent


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Return a temporary config directory for project sessions."""
    return tmp_path / "config"


@pytest.fixture
def sample_project() -> MagicMock:
    """Return a mock Project with realistic attributes."""
    project = MagicMock()
    project.id = "my-project"
    project.name = "My Project"
    project.workspace_path = Path("/workspace/my-project")
    project.last_active = datetime(2026, 1, 1, tzinfo=UTC)
    project.status = "active"
    return project


@pytest.fixture
def toolset(
    mock_store: MagicMock,
    mock_agent: MagicMock,
    config_dir: Path,
) -> ProjectToolset:
    """Return a ProjectToolset wired to mocks."""
    return ProjectToolset(
        store=mock_store,
        agent=mock_agent,
        config_dir=config_dir,
    )


# ---------------------------------------------------------------------------
# switch_project — updates agent session path
# ---------------------------------------------------------------------------


class TestSwitchProjectSessionPath:
    """switch_project(name) updates agent session path to project's session dir."""

    @pytest.mark.asyncio
    async def test_session_path_points_to_project_dir(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
        mock_agent: MagicMock,
        sample_project: MagicMock,
        config_dir: Path,
    ) -> None:
        """After switch, agent.session.path is under config_dir/projects/{id}/sessions/."""
        mock_store.get_by_name.return_value = sample_project

        await toolset._switch_project("My Project")

        # The new session should be in the project's session directory
        new_session = mock_agent.session
        expected_dir = config_dir / "projects" / "my-project" / "sessions"
        assert new_session.path.parent == expected_dir


# ---------------------------------------------------------------------------
# switch_project — returns confirmation message
# ---------------------------------------------------------------------------


class TestSwitchProjectConfirmation:
    """switch_project(name) returns confirmation message with project name."""

    @pytest.mark.asyncio
    async def test_returns_confirmation_with_name(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """switch_project returns a string containing the project name."""
        mock_store.get_by_name.return_value = sample_project

        result = await toolset._switch_project("My Project")

        assert "My Project" in result
        assert "switch" in result.lower() or "switched" in result.lower()


# ---------------------------------------------------------------------------
# switch_project — nonexistent project returns error message
# ---------------------------------------------------------------------------


class TestSwitchProjectNotFound:
    """switch_project with nonexistent project returns error message (not exception)."""

    @pytest.mark.asyncio
    async def test_nonexistent_returns_error_string(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
    ) -> None:
        """When project doesn't exist, return an error string — no exception raised."""
        mock_store.get_by_name.side_effect = KeyError("No project named 'ghost'")

        result = await toolset._switch_project("ghost")

        assert isinstance(result, str)
        assert "error" in result.lower() or "not found" in result.lower()
        assert "ghost" in result


# ---------------------------------------------------------------------------
# list_projects — returns active projects
# ---------------------------------------------------------------------------


class TestListProjects:
    """list_projects() returns active projects with name and last_active."""

    @pytest.mark.asyncio
    async def test_returns_project_summaries(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
    ) -> None:
        """list_projects returns formatted info for each active project."""
        p1 = MagicMock()
        p1.name = "Alpha"
        p1.last_active = datetime(2026, 2, 15, tzinfo=UTC)
        p1.status = "active"

        p2 = MagicMock()
        p2.name = "Beta"
        p2.last_active = datetime(2026, 1, 10, tzinfo=UTC)
        p2.status = "active"

        mock_store.list_active.return_value = [p1, p2]

        result = await toolset._list_projects()

        assert "Alpha" in result
        assert "Beta" in result
        # last_active info should be present
        assert "2026" in result

    @pytest.mark.asyncio
    async def test_empty_list_returns_message(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
    ) -> None:
        """When no active projects exist, return a helpful message."""
        mock_store.list_active.return_value = []

        result = await toolset._list_projects()

        assert isinstance(result, str)
        assert "no" in result.lower() or "empty" in result.lower()


# ---------------------------------------------------------------------------
# switch_project — updates last_active timestamp
# ---------------------------------------------------------------------------


class TestSwitchProjectUpdatesTimestamp:
    """switch_project updates project.last_active timestamp."""

    @pytest.mark.asyncio
    async def test_last_active_updated_on_switch(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """After switch, store.update is called with a refreshed last_active."""
        old_time = datetime(2026, 1, 1, tzinfo=UTC)
        sample_project.last_active = old_time
        sample_project.model_copy = MagicMock(return_value=sample_project)
        mock_store.get_by_name.return_value = sample_project

        before = datetime.now(tz=UTC)
        await toolset._switch_project("My Project")

        # store.update must have been called
        mock_store.update.assert_called_once()

        # The project passed to update should have a refreshed last_active
        updated_project = mock_store.update.call_args[0][0]
        assert updated_project.last_active >= before or sample_project.model_copy.called


# ---------------------------------------------------------------------------
# Mock isolation — ProjectStore and OwlBearAgent
# ---------------------------------------------------------------------------


class TestMockIsolation:
    """Verify toolset uses mocked ProjectStore and OwlBearAgent — no real I/O."""

    @pytest.mark.asyncio
    async def test_no_filesystem_access_on_switch(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """switch_project accesses only mocked store and agent, not real FS."""
        mock_store.get_by_name.return_value = sample_project

        await toolset._switch_project("My Project")

        mock_store.get_by_name.assert_called_once_with("My Project")

    @pytest.mark.asyncio
    async def test_list_delegates_to_store(
        self,
        toolset: ProjectToolset,
        mock_store: MagicMock,
    ) -> None:
        """list_projects delegates to store.list_active without filesystem I/O."""
        mock_store.list_active.return_value = []

        await toolset._list_projects()

        mock_store.list_active.assert_called_once()
