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
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.projects.store import ProjectStore

__all__ = ["ProjectToolset"]

logger = logging.getLogger(__name__)


class ProjectToolset(FunctionToolset):
    """FunctionToolset exposing project switching and listing tools.

    Args:
        store: :class:`ProjectStore` for project CRUD operations.
        agent: Agent instance whose ``session.path`` is updated on switch.
        config_dir: Root config directory; sessions stored under
            ``config_dir/projects/{id}/sessions/``.
    """

    def __init__(self, store: ProjectStore, agent: object, config_dir: Path) -> None:
        super().__init__()
        self._store = store
        self._agent = agent
        self._config_dir = config_dir
        self._register_tools()

    def _register_tools(self) -> None:
        """Register project tools on this toolset."""
        self.add_function(self._switch_project, name="switch_project")
        self.add_function(self._list_projects, name="list_projects")

    async def _switch_project(self, project_name: str) -> str:
        """Switch the active project, updating session path and timestamp."""
        try:
            project = self._store.get_by_name(project_name)
        except (KeyError, FileNotFoundError):
            return f"Error: project '{project_name}' not found."

        # Rebuild session path under project directory
        session_dir = self._config_dir / "projects" / project.id / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "session.jsonl"
        self._agent.session.path = session_file

        # Update last_active timestamp
        updated = project.model_copy(update={"last_active": datetime.now(tz=UTC)})
        self._store.update(updated)

        logger.info("Switched to project '%s'", project.name)
        name = project.name
        return f"Switched to project '{name}'. You are now working on project: {name}"

    async def _list_projects(self) -> str:
        """Return a formatted list of active projects."""
        projects = self._store.list_active()
        if not projects:
            return "No active projects found."
        lines = [f"- {p.name} (last active: {p.last_active:%Y-%m-%d %H:%M})" for p in projects]
        return "\n".join(lines)
