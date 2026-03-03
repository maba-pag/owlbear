"""Tests for ProjectToolset — agent tools for project switching.

TDD red-phase: these tests define the expected behavior of ProjectToolset.
The module does not exist yet — all tests should fail on ImportError.

Task #350 — see docs/multi-project-session-research.md §3.10
Task #369 — workspace switching improvements (CWD + context reload)
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from owlbear.memory.context import ContextManager
from owlbear.projects.models import Project
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
def sample_project(tmp_path: Path) -> MagicMock:
    """Return a mock Project with realistic attributes."""
    workspace = tmp_path / "workspace" / "my-project"
    workspace.mkdir(parents=True)
    project = MagicMock()
    project.id = "my-project"
    project.name = "My Project"
    project.workspace_path = workspace
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


# ===================================================================
# Task #369 — ContextManager.update_root
# ===================================================================


class TestContextManagerUpdateRoot:
    """ContextManager.update_root changes the workspace root pointer."""

    def test_update_root_changes_root_and_path(self, tmp_path: Path) -> None:
        ctx = ContextManager(tmp_path / "old_workspace")
        new_root = tmp_path / "new_workspace"

        ctx.update_root(new_root)

        assert ctx.path == new_root / "context.md"

    def test_update_root_preserves_custom_filename(self, tmp_path: Path) -> None:
        ctx = ContextManager(tmp_path / "old", filename="INSTRUCTIONS.md")
        new_root = tmp_path / "new"

        ctx.update_root(new_root)

        assert ctx.path == new_root / "INSTRUCTIONS.md"

    def test_load_uses_new_root_after_update(self, tmp_path: Path) -> None:
        old_root = tmp_path / "old"
        new_root = tmp_path / "new"
        new_root.mkdir(parents=True)
        (new_root / "context.md").write_text("new context", encoding="utf-8")

        ctx = ContextManager(old_root)
        assert ctx.load() is None  # old doesn't exist

        ctx.update_root(new_root)
        assert ctx.load() == "new context"


# ===================================================================
# Task #369 — switch_project CWD change
# ===================================================================


def _real_project(name: str, workspace: Path) -> Project:
    """Create a real Project model for testing."""
    return Project(
        name=name,
        workspace_path=workspace,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        last_active=datetime(2025, 1, 1, tzinfo=UTC),
    )


def _real_store(project: Project) -> MagicMock:
    """Mock store that resolves *project* by name."""
    store = MagicMock()
    store.get_by_name.return_value = project
    store.update = MagicMock()
    return store


def _agent_ns(
    *,
    context: ContextManager | None = None,
    toolsets: list | None = None,
) -> SimpleNamespace:
    """Minimal agent-like namespace with context + toolsets."""
    return SimpleNamespace(
        session=SimpleNamespace(path=Path("/old/session.jsonl")),
        context=context,
        toolsets=toolsets or [],
    )


class TestSwitchProjectCWD:
    """switch_project calls os.chdir to the new workspace."""

    @pytest.mark.asyncio
    async def test_chdir_called_with_workspace_path(self, tmp_path: Path) -> None:
        workspace = tmp_path / "projects" / "alpha"
        workspace.mkdir(parents=True)
        project = _real_project("alpha", workspace)
        store = _real_store(project)
        agent = _agent_ns()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir") as mock_chdir:
            result = await ts._switch_project("alpha")

        mock_chdir.assert_called_once_with(workspace)
        assert "alpha" in result

    @pytest.mark.asyncio
    async def test_chdir_not_called_on_missing_project(self, tmp_path: Path) -> None:
        store = MagicMock()
        store.get_by_name.side_effect = KeyError("nope")
        agent = _agent_ns()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir") as mock_chdir:
            result = await ts._switch_project("nonexistent")

        mock_chdir.assert_not_called()
        assert "not found" in result.lower()


# ===================================================================
# Task #369 — switch_project ContextManager update
# ===================================================================


class TestSwitchProjectContextUpdate:
    """switch_project updates the agent's ContextManager workspace root."""

    @pytest.mark.asyncio
    async def test_context_manager_root_updated(self, tmp_path: Path) -> None:
        old_root = tmp_path / "old_ws"
        new_ws = tmp_path / "projects" / "beta"
        new_ws.mkdir(parents=True)

        ctx = ContextManager(old_root)
        project = _real_project("beta", new_ws)
        store = _real_store(project)
        agent = _agent_ns(context=ctx)

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("beta")

        assert ctx.path == new_ws / "context.md"

    @pytest.mark.asyncio
    async def test_no_error_when_agent_has_no_context(self, tmp_path: Path) -> None:
        workspace = tmp_path / "projects" / "gamma"
        workspace.mkdir(parents=True)
        project = _real_project("gamma", workspace)
        store = _real_store(project)
        agent = _agent_ns(context=None)

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            result = await ts._switch_project("gamma")

        assert "gamma" in result

    @pytest.mark.asyncio
    async def test_no_error_when_agent_lacks_context_attr(
        self, tmp_path: Path
    ) -> None:
        """Agent without a context attribute (e.g. placeholder) doesn't crash."""
        workspace = tmp_path / "projects" / "kappa"
        workspace.mkdir(parents=True)
        project = _real_project("kappa", workspace)
        store = _real_store(project)
        agent = SimpleNamespace(
            session=SimpleNamespace(path=Path("/x")),
        )  # no context attr

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            result = await ts._switch_project("kappa")

        assert "kappa" in result


# ===================================================================
# Task #369 — switch_project toolset workspace_root update
# ===================================================================


class TestSwitchProjectToolsetRootUpdate:
    """switch_project updates _workspace_root / _root on agent toolsets."""

    @pytest.mark.asyncio
    async def test_toolset_workspace_root_updated(self, tmp_path: Path) -> None:
        workspace = tmp_path / "projects" / "delta"
        workspace.mkdir(parents=True)
        project = _real_project("delta", workspace)
        store = _real_store(project)

        fake_ts = SimpleNamespace(_workspace_root=Path("/old"))
        agent = _agent_ns(toolsets=[fake_ts])

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("delta")

        assert fake_ts._workspace_root == workspace

    @pytest.mark.asyncio
    async def test_toolset_root_updated(self, tmp_path: Path) -> None:
        """Toolsets using _root (e.g. FileToolset, KnowledgeToolset) get updated."""
        workspace = tmp_path / "projects" / "epsilon"
        workspace.mkdir(parents=True)
        project = _real_project("epsilon", workspace)
        store = _real_store(project)

        fake_ts = SimpleNamespace(_root=Path("/old"))
        agent = _agent_ns(toolsets=[fake_ts])

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("epsilon")

        assert fake_ts._root == workspace.resolve()

    @pytest.mark.asyncio
    async def test_wrapped_toolset_unwrapped_and_updated(
        self, tmp_path: Path
    ) -> None:
        """Toolsets wrapped (e.g. HookedToolset) are unwrapped for update."""
        workspace = tmp_path / "projects" / "zeta"
        workspace.mkdir(parents=True)
        project = _real_project("zeta", workspace)
        store = _real_store(project)

        inner_ts = SimpleNamespace(_workspace_root=Path("/old"))
        wrapper = SimpleNamespace(wrapped=inner_ts)
        agent = _agent_ns(toolsets=[wrapper])

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("zeta")

        assert inner_ts._workspace_root == workspace

    @pytest.mark.asyncio
    async def test_no_error_when_agent_has_no_toolsets_attr(
        self, tmp_path: Path
    ) -> None:
        """Graceful when agent has no toolsets attribute."""
        workspace = tmp_path / "projects" / "theta"
        workspace.mkdir(parents=True)
        project = _real_project("theta", workspace)
        store = _real_store(project)
        agent = SimpleNamespace(
            session=SimpleNamespace(path=Path("/x")),
        )  # no toolsets attr

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ts = ProjectToolset(store=store, agent=agent, config_dir=config_dir)

        with patch("owlbear.projects.toolset.os.chdir"):
            result = await ts._switch_project("theta")

        assert "theta" in result


# ---------------------------------------------------------------------------
# workspace_create_project — delegates to ProjectWorkspace
# ---------------------------------------------------------------------------


class TestWorkspaceCreateProject:
    """workspace_create_project(name, template) creates via ProjectWorkspace."""

    @pytest.mark.asyncio
    async def test_returns_confirmation_with_path(
        self,
        mock_store: MagicMock,
        mock_agent: MagicMock,
        config_dir: Path,
        tmp_path: Path,
    ) -> None:
        project_root = tmp_path / "project-root"
        ts = ProjectToolset(
            store=mock_store, agent=mock_agent,
            config_dir=config_dir, project_root=project_root,
        )
        expected_path = project_root / "my-app"
        with patch("owlbear.projects.workspace.ProjectWorkspace") as mock_ws_cls:
            mock_ws_cls.return_value.create_project.return_value = expected_path
            result = await ts._workspace_create_project("My App", "bare")
        assert "My App" in result
        assert str(expected_path) in result

    @pytest.mark.asyncio
    async def test_delegates_to_workspace(
        self,
        mock_store: MagicMock,
        mock_agent: MagicMock,
        config_dir: Path,
        tmp_path: Path,
    ) -> None:
        project_root = tmp_path / "project-root"
        ts = ProjectToolset(
            store=mock_store, agent=mock_agent,
            config_dir=config_dir, project_root=project_root,
        )
        with patch("owlbear.projects.workspace.ProjectWorkspace") as mock_ws_cls:
            mock_ws_cls.return_value.create_project.return_value = tmp_path / "my-app"
            await ts._workspace_create_project("My App", "python-uv")
        mock_ws_cls.return_value.create_project.assert_called_once_with(
            "My App", "python-uv"
        )

    @pytest.mark.asyncio
    async def test_invalid_template_returns_error(
        self,
        mock_store: MagicMock,
        mock_agent: MagicMock,
        config_dir: Path,
        tmp_path: Path,
    ) -> None:
        project_root = tmp_path / "project-root"
        ts = ProjectToolset(
            store=mock_store, agent=mock_agent,
            config_dir=config_dir, project_root=project_root,
        )
        with patch("owlbear.projects.workspace.ProjectWorkspace") as mock_ws_cls:
            mock_ws_cls.return_value.create_project.side_effect = ValueError(
                "Unknown template 'bad'"
            )
            result = await ts._workspace_create_project("My App", "bad")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_no_project_root_returns_error(
        self,
        mock_store: MagicMock,
        mock_agent: MagicMock,
        config_dir: Path,
    ) -> None:
        """Without project_root, tool returns an error message."""
        ts = ProjectToolset(
            store=mock_store, agent=mock_agent, config_dir=config_dir,
        )
        result = await ts._workspace_create_project("My App", "bare")
        assert "error" in result.lower()
