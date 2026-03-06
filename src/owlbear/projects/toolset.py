"""ProjectToolset — FunctionToolset for project switching and listing.

Exposes ``switch_project`` and ``list_projects`` tools for agents to manage
multi-project workspaces.  Switching updates the agent session path and
refreshes the project's ``last_active`` timestamp.

Usage::

    from owlbear.projects.toolset import ProjectToolset

    toolset = ProjectToolset(store=store, agent=agent, config_dir=config_dir)
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.projects.store import ProjectStore

__all__ = ["ProjectToolset"]

logger = logging.getLogger(__name__)


class ProjectToolset(FunctionToolset):
    """FunctionToolset exposing project switching, listing, and creation tools.

    Args:
        store: :class:`ProjectStore` for project CRUD operations.
        agent: Agent instance whose ``session.path`` is updated on switch.
        config_dir: Root config directory; sessions stored under
            ``config_dir/projects/{id}/sessions/``.
        project_root: Base directory for new projects.  When supplied,
            ``workspace_create_project`` can scaffold new workspaces.
    """

    def __init__(
        self,
        store: ProjectStore,
        agent: object,
        config_dir: Path,
        *,
        project_root: Path | None = None,
    ) -> None:
        super().__init__()
        self._store = store
        self._agent = agent
        self._config_dir = config_dir
        self._project_root = project_root
        self._register_tools()

    def bind_agent(self, agent: object) -> None:
        """Replace the agent reference (used after deferred construction)."""
        self._agent = agent

    def _register_tools(self) -> None:
        """Register project tools on this toolset."""
        self.add_function(self._switch_project, name="switch_project")
        self.add_function(self._list_projects, name="list_projects")
        self.add_function(self._workspace_create_project, name="workspace_create_project")

    async def _switch_project(self, project_name: str) -> str:
        """Switch the active project, updating session path and timestamp.

        After updating the session path and timestamp this also:

        1. Changes the process CWD to the project workspace (so
           subprocess-based tools operate in the new workspace).
        2. Updates the agent's :class:`ContextManager` root (if present)
           so instructions are loaded from the new workspace.
        3. Walks the agent's toolsets and updates any
           ``_workspace_root`` / ``_root`` attributes to the new
           workspace path.
        """
        try:
            project = self._store.get_by_name(project_name)
        except (KeyError, FileNotFoundError):
            return f"Error: project '{project_name}' not found."

        workspace = project.workspace_path

        # Rebuild session path under project directory
        session_dir = self._config_dir / "projects" / project.id / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "session.jsonl"
        self._agent.session.path = session_file

        # Update last_active timestamp
        updated = project.model_copy(update={"last_active": datetime.now(tz=UTC)})
        self._store.update(updated)

        # --- workspace switching (task #369) ---
        os.chdir(workspace)

        # Update ContextManager workspace root
        ctx = getattr(self._agent, "context", None)
        if ctx is not None and hasattr(ctx, "update_root"):
            ctx.update_root(workspace)

        # Update toolset workspace_root references
        _update_toolset_roots(getattr(self._agent, "toolsets", []), workspace)

        logger.info("Switched to project '%s' (cwd=%s)", project.name, workspace)
        name = project.name
        return f"Switched to project '{name}'. You are now working on project: {name}"

    async def _list_projects(self) -> str:
        """Return a formatted list of active projects."""
        projects = self._store.list_active()
        if not projects:
            return "No active projects found."
        lines = [f"- {p.name} (last active: {p.last_active:%Y-%m-%d %H:%M})" for p in projects]
        return "\n".join(lines)

    async def _workspace_create_project(self, name: str, template: str) -> str:
        """Create a new project from a template using ProjectWorkspace."""
        from owlbear.projects.workspace import ProjectWorkspace  # noqa: PLC0415

        if self._project_root is None:
            return "Error: project_root is not configured. Cannot create workspace."

        ws = ProjectWorkspace(project_root=self._project_root, store=self._store)
        try:
            path = ws.create_project(name, template)
        except (ValueError, FileExistsError) as exc:
            return f"Error: {exc}"
        return f"Created project '{name}' at {path}"


def _update_toolset_roots(toolsets: list[object], workspace: Path) -> None:
    """Walk *toolsets* and update workspace root attributes in-place.

    Handles toolsets wrapped via ``wrapped`` attribute (e.g.
    :class:`~owlbear.tools.hooked.HookedToolset`).

    Uses the :class:`~owlbear.tools.protocols.WorkspaceAware` protocol
    to detect toolsets that support workspace updates.
    """
    from owlbear.tools.protocols import WorkspaceAware  # noqa: PLC0415

    for ts in toolsets:
        inner = ts
        while hasattr(inner, "wrapped"):
            inner = inner.wrapped  # type: ignore[union-attr]
        if isinstance(inner, WorkspaceAware):
            inner.update_workspace(workspace)
