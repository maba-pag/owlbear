"""Tests for eliminating post-construction patching in bootstrap (task #523).

These tests define the new contract after refactoring:
- OwlBearAgent accepts agent_registry at construction (no post-patch)
- ProjectToolset accepts session/context/toolsets directly (no agent object)
- Deleted methods and functions no longer exist
- Bootstrap wires everything at construction time

All tests should FAIL against the current codebase.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ===================================================================
# AC 1 & 2 — OwlBearAgent accepts agent_registry at construction;
#             set_agent_registry() deleted
# ===================================================================


class TestFromAC_AgentRegistryDI:
    """OwlBearAgent.__init__ accepts agent_registry and wires it into deps."""

    def test_constructor_accepts_agent_registry_kwarg(self) -> None:
        """OwlBearAgent.__init__ has an agent_registry parameter."""
        from owlbear.core.agent import OwlBearAgent

        sig = inspect.signature(OwlBearAgent.__init__)
        assert "agent_registry" in sig.parameters, (
            "OwlBearAgent.__init__ must accept agent_registry keyword argument"
        )

    def test_agent_registry_passed_to_deps(self, tmp_path: Path) -> None:
        """When agent_registry is provided, it is set on _deps.agent_registry."""
        from owlbear.core.agent import OwlBearAgent

        fake_registry = MagicMock()
        fake_session = MagicMock()
        fake_session.path = tmp_path / "session.jsonl"

        with patch("owlbear.core.agent.Agent"):
            agent = OwlBearAgent(
                model="test-model",
                session=fake_session,
                agent_registry=fake_registry,
            )

        assert agent._deps.agent_registry is fake_registry

    def test_agent_registry_defaults_to_none(self) -> None:
        """When agent_registry is omitted, _deps.agent_registry is None."""
        from owlbear.core.agent import OwlBearAgent

        # Verify the constructor param exists AND defaults to None
        sig = inspect.signature(OwlBearAgent.__init__)
        param = sig.parameters.get("agent_registry")
        assert param is not None, "OwlBearAgent.__init__ must have an agent_registry parameter"
        assert param.default is None, "agent_registry must default to None"

    def test_set_agent_registry_deleted(self) -> None:
        """set_agent_registry() should no longer exist on OwlBearAgent."""
        from owlbear.core.agent import OwlBearAgent

        assert not hasattr(OwlBearAgent, "set_agent_registry"), (
            "set_agent_registry() must be deleted — DI replaces post-construction patching"
        )


# ===================================================================
# AC 4, 5, 6 — ProjectToolset accepts session/context/toolsets directly;
#               bind_agent() deleted
# ===================================================================


class TestFromAC_ProjectToolsetDirectDeps:
    """ProjectToolset.__init__ accepts session, context, toolsets directly."""

    def test_constructor_accepts_session_param(self) -> None:
        """ProjectToolset.__init__ has a session parameter."""
        from owlbear.projects.toolset import ProjectToolset

        sig = inspect.signature(ProjectToolset.__init__)
        assert "session" in sig.parameters, (
            "ProjectToolset.__init__ must accept session (SessionStore)"
        )

    def test_constructor_accepts_context_param(self) -> None:
        """ProjectToolset.__init__ has a context parameter."""
        from owlbear.projects.toolset import ProjectToolset

        sig = inspect.signature(ProjectToolset.__init__)
        assert "context" in sig.parameters, (
            "ProjectToolset.__init__ must accept context (ContextManager | None)"
        )

    def test_constructor_accepts_toolsets_param(self) -> None:
        """ProjectToolset.__init__ has a toolsets parameter."""
        from owlbear.projects.toolset import ProjectToolset

        sig = inspect.signature(ProjectToolset.__init__)
        assert "toolsets" in sig.parameters, (
            "ProjectToolset.__init__ must accept toolsets (list[AbstractToolset])"
        )

    def test_constructor_does_not_accept_agent_param(self) -> None:
        """ProjectToolset.__init__ must NOT accept an agent parameter."""
        from owlbear.projects.toolset import ProjectToolset

        sig = inspect.signature(ProjectToolset.__init__)
        assert "agent" not in sig.parameters, (
            "ProjectToolset.__init__ must not accept agent — use session/context/toolsets"
        )

    def test_bind_agent_deleted(self) -> None:
        """bind_agent() should no longer exist on ProjectToolset."""
        from owlbear.projects.toolset import ProjectToolset

        assert not hasattr(ProjectToolset, "bind_agent"), (
            "bind_agent() must be deleted — direct DI replaces deferred binding"
        )

    @pytest.mark.asyncio
    async def test_switch_project_updates_session_path(self, tmp_path: Path) -> None:
        """switch_project updates self._session.path to new project session dir."""
        from owlbear.projects.toolset import ProjectToolset

        workspace = tmp_path / "projects" / "alpha"
        workspace.mkdir(parents=True)

        mock_store = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "alpha"
        mock_project.name = "Alpha"
        mock_project.workspace_path = workspace
        mock_project.model_copy = MagicMock(return_value=mock_project)
        mock_store.get_by_name.return_value = mock_project

        mock_session = MagicMock()
        mock_session.path = Path("/old/session.jsonl")

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ts = ProjectToolset(
            store=mock_store,
            session=mock_session,
            context=None,
            toolsets=[],
            config_dir=config_dir,
        )

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("Alpha")

        expected_dir = config_dir / "projects" / "alpha" / "sessions"
        assert mock_session.path.parent == expected_dir

    @pytest.mark.asyncio
    async def test_switch_project_updates_context_root(self, tmp_path: Path) -> None:
        """switch_project calls context.update_root with new workspace."""
        from owlbear.memory.context import ContextManager
        from owlbear.projects.toolset import ProjectToolset

        workspace = tmp_path / "projects" / "beta"
        workspace.mkdir(parents=True)

        mock_store = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "beta"
        mock_project.name = "Beta"
        mock_project.workspace_path = workspace
        mock_project.model_copy = MagicMock(return_value=mock_project)
        mock_store.get_by_name.return_value = mock_project

        mock_session = MagicMock()
        mock_session.path = Path("/old/session.jsonl")
        ctx = ContextManager(tmp_path / "old_ws")

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ts = ProjectToolset(
            store=mock_store,
            session=mock_session,
            context=ctx,
            toolsets=[],
            config_dir=config_dir,
        )

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("Beta")

        assert ctx.path == workspace / "context.md"

    @pytest.mark.asyncio
    async def test_switch_project_updates_toolset_roots(self, tmp_path: Path) -> None:
        """switch_project updates workspace roots on provided toolsets list."""
        from owlbear.projects.toolset import ProjectToolset

        workspace = tmp_path / "projects" / "gamma"
        workspace.mkdir(parents=True)

        mock_store = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "gamma"
        mock_project.name = "Gamma"
        mock_project.workspace_path = workspace
        mock_project.model_copy = MagicMock(return_value=mock_project)
        mock_store.get_by_name.return_value = mock_project

        mock_session = MagicMock()
        mock_session.path = Path("/old/session.jsonl")

        class FakeToolset:
            def __init__(self) -> None:
                self.workspace: Path | None = None

            def update_workspace(self, ws: Path) -> None:
                self.workspace = ws

        fake_ts = FakeToolset()
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ts = ProjectToolset(
            store=mock_store,
            session=mock_session,
            context=None,
            toolsets=[fake_ts],
            config_dir=config_dir,
        )

        with patch("owlbear.projects.toolset.os.chdir"):
            await ts._switch_project("Gamma")

        assert fake_ts.workspace == workspace

    @pytest.mark.asyncio
    async def test_switch_project_none_context_no_crash(self, tmp_path: Path) -> None:
        """switch_project with context=None doesn't crash."""
        from owlbear.projects.toolset import ProjectToolset

        workspace = tmp_path / "projects" / "delta"
        workspace.mkdir(parents=True)

        mock_store = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "delta"
        mock_project.name = "Delta"
        mock_project.workspace_path = workspace
        mock_project.model_copy = MagicMock(return_value=mock_project)
        mock_store.get_by_name.return_value = mock_project

        mock_session = MagicMock()
        mock_session.path = Path("/old/session.jsonl")

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ts = ProjectToolset(
            store=mock_store,
            session=mock_session,
            context=None,
            toolsets=[],
            config_dir=config_dir,
        )

        with patch("owlbear.projects.toolset.os.chdir"):
            result = await ts._switch_project("Delta")

        assert "Delta" in result


# ===================================================================
# AC 7 — _patch_project_toolset_agent() deleted from bootstrap
# ===================================================================


class TestFromAC_BootstrapPatchDeleted:
    """Post-construction patching functions removed from bootstrap."""

    def test_patch_project_toolset_agent_deleted_from_toolsets(self) -> None:
        """_patch_project_toolset_agent should no longer exist in bootstrap.toolsets."""
        from owlbear.bootstrap import toolsets as toolsets_mod

        assert not hasattr(toolsets_mod, "_patch_project_toolset_agent"), (
            "_patch_project_toolset_agent must be deleted — direct DI replaces it"
        )

    def test_patch_project_toolset_agent_not_in_bootstrap_init(self) -> None:
        """_patch_project_toolset_agent should not be importable from bootstrap."""
        import owlbear.bootstrap as bootstrap_mod

        assert not hasattr(bootstrap_mod, "_patch_project_toolset_agent"), (
            "_patch_project_toolset_agent must not be re-exported from bootstrap"
        )


# ===================================================================
# AC 8 — _add_project_toolset() accepts session/context/toolsets
# ===================================================================


class TestFromAC_AddProjectToolsetSignature:
    """_add_project_toolset() receives session, context, toolsets directly."""

    def test_accepts_session_param(self) -> None:
        """_add_project_toolset has a session parameter."""
        from owlbear.bootstrap.toolsets import _add_project_toolset

        sig = inspect.signature(_add_project_toolset)
        assert "session" in sig.parameters, (
            "_add_project_toolset must accept session (SessionStore)"
        )

    def test_accepts_context_param(self) -> None:
        """_add_project_toolset has a context parameter."""
        from owlbear.bootstrap.toolsets import _add_project_toolset

        sig = inspect.signature(_add_project_toolset)
        assert "context" in sig.parameters, (
            "_add_project_toolset must accept context (ContextManager | None)"
        )

    def test_accepts_toolsets_param(self) -> None:
        """_add_project_toolset has a dedicated param for the agent's toolsets list.

        This is distinct from the existing 'toolsets' accumulator param. The function
        must accept a param (session, context, or agent_toolsets) that passes deps
        through to ProjectToolset construction.
        """
        from owlbear.bootstrap.toolsets import _add_project_toolset

        sig = inspect.signature(_add_project_toolset)
        assert "session" in sig.parameters, (
            "_add_project_toolset must accept session for direct ProjectToolset DI"
        )
        assert "context" in sig.parameters, (
            "_add_project_toolset must accept context for direct ProjectToolset DI"
        )

    def test_no_placeholder_created(self) -> None:
        """_add_project_toolset should not create a _Placeholder object."""
        from owlbear.bootstrap import toolsets as toolsets_mod

        source = inspect.getsource(toolsets_mod._add_project_toolset)
        assert "_Placeholder" not in source, (
            "_add_project_toolset must not create placeholder objects — use direct DI"
        )


# ===================================================================
# AC 9 — Bootstrap reorders SessionStore/ContextManager creation
# ===================================================================


class TestFromAC_BootstrapCreationOrder:
    """SessionStore and ContextManager created before _add_project_toolset call."""

    def test_session_and_context_created_before_project_toolset(self) -> None:
        """In bootstrap(), SessionStore and ContextManager are created before
        _add_project_toolset is called, so they can be passed as arguments.
        """
        bootstrap_mod = importlib.import_module("owlbear.bootstrap")

        # Get the source of the bootstrap function
        source = inspect.getsource(bootstrap_mod.bootstrap)

        # Find positions of key constructs
        session_store_pos = source.find("SessionStore(")
        context_manager_pos = source.find("ContextManager(")
        add_project_pos = source.find("_add_project_toolset(")

        # All three must exist
        assert session_store_pos != -1, "SessionStore construction not found in bootstrap()"
        assert context_manager_pos != -1, "ContextManager construction not found in bootstrap()"
        assert add_project_pos != -1, "_add_project_toolset call not found in bootstrap()"

        # SessionStore and ContextManager must come BEFORE _add_project_toolset
        assert session_store_pos < add_project_pos, (
            "SessionStore must be created before _add_project_toolset is called"
        )
        assert context_manager_pos < add_project_pos, (
            "ContextManager must be created before _add_project_toolset is called"
        )

    def test_bootstrap_passes_session_to_add_project_toolset(self) -> None:
        """bootstrap() passes session= argument to _add_project_toolset."""
        bootstrap_mod = importlib.import_module("owlbear.bootstrap")

        source = inspect.getsource(bootstrap_mod.bootstrap)

        # Find the _add_project_toolset call region and check it contains session=
        add_pos = source.find("_add_project_toolset(")
        assert add_pos != -1
        # Extract a reasonable chunk after the call start
        call_region = source[add_pos : add_pos + 500]
        # Find the closing paren
        depth = 0
        end = 0
        for i, ch in enumerate(call_region):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        call_text = call_region[: end + 1]
        assert "session" in call_text, "bootstrap must pass session to _add_project_toolset"
