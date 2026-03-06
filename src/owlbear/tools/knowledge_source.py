"""KnowledgeSourceToolset — FunctionToolset exposing source management to agents.

Provides ``add_source``, ``list_sources``, and ``refresh_source`` —
allowing agents to register, browse, and refresh knowledge sources.

Usage::

    from owlbear.tools.knowledge_source import KnowledgeSourceToolset

    toolset = KnowledgeSourceToolset(
        store=source_store,
        orchestrator=refresh_orch,
        workspace_root=workspace,
    )
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from owlbear.memory.knowledge.models import KnowledgeSource, SourceType

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.memory.knowledge.refresh import RefreshOrchestrator
    from owlbear.memory.knowledge.source_store import KnowledgeSourceStore

__all__ = ["KnowledgeSourceToolset"]

logger = logging.getLogger(__name__)


class KnowledgeSourceToolset(FunctionToolset):
    """FunctionToolset subclass exposing 3 source-management tools.

    Args:
        store: :class:`KnowledgeSourceStore` CRUD façade.
        orchestrator: :class:`RefreshOrchestrator` for triggering refreshes.
        workspace_root: Optional root directory (reserved for future use).
    """

    def __init__(
        self,
        store: KnowledgeSourceStore,
        orchestrator: RefreshOrchestrator,
        workspace_root: Path | None = None,
    ) -> None:
        super().__init__()
        self._store = store
        self._orchestrator = orchestrator
        self._workspace_root = workspace_root
        self._register_tools()

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace*."""
        self._workspace_root = workspace

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all 3 source-management tools on this toolset."""
        self.add_function(
            self._add_source,
            name="add_source",
            description=(
                "Register a new knowledge source. "
                "Provide a name, source type (url_list, crawl, file_glob), "
                "configuration as a JSON string, and an optional scope."
            ),
        )
        self.add_function(
            self._list_sources,
            name="list_sources",
            description=("List all registered knowledge sources, optionally filtered by scope."),
        )
        self.add_function(
            self._refresh_source,
            name="refresh_source",
            description=(
                "Trigger a refresh for a named knowledge source. "
                "Fetches new content and ingests it into the knowledge base."
            ),
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _add_source(
        self,
        name: str,
        source_type: str,
        config_json: str,
        scope: str = "global",
    ) -> str:
        """Register a new knowledge source.

        Args:
            name: Human-readable name for the source.
            source_type: One of ``'url_list'``, ``'crawl'``, or ``'file_glob'``.
            config_json: JSON string with source-specific configuration.
            scope: Scope tag (default ``'global'``).

        Returns:
            Confirmation message or error description.
        """
        # Validate source_type
        try:
            st = SourceType(source_type)
        except ValueError:
            valid = ", ".join(t.value for t in SourceType)
            return f"Error: Invalid source_type '{source_type}'. Must be one of: {valid}"

        # Parse config JSON
        try:
            config = json.loads(config_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error: Invalid config_json — {exc}"

        now = datetime.now(tz=UTC).isoformat()
        source = KnowledgeSource(
            name=name,
            source_type=st,
            config=config,
            scope=scope,
            created_at=now,
            updated_at=now,
        )
        self._store.create(source)
        return f"Source {name} ({source_type}) created."

    def _list_sources(self, scope: str | None = None) -> str:
        """List registered knowledge sources.

        Args:
            scope: Optional scope filter. When ``None``, lists all sources.

        Returns:
            Formatted list or ``'No sources registered.'`` when empty.
        """
        sources = self._store.list_all(scope)

        if not sources:
            return "No sources registered."

        lines: list[str] = []
        for src in sources:
            enabled = "yes" if src.enabled else "no"
            last_refresh = src.last_refreshed_at or "never"
            lines.append(
                f"- {src.name} [{src.source_type}] "
                f"(scope: {src.scope}, enabled: {enabled}, "
                f"last refresh: {last_refresh})"
            )
        return "\n".join(lines)

    async def _refresh_source(self, name: str) -> str:
        """Trigger a refresh for a named knowledge source.

        Args:
            name: Name of the source to refresh.

        Returns:
            Summary string with ingested/skipped/failed counts,
            or an error message if the source is not found.
        """
        source = self._store.get_by_name(name)
        if source is None:
            return f"Source {name} not found."

        result = await self._orchestrator.refresh(source)
        return (
            f"Refreshed {name}: "
            f"{result.refreshed} ingested, "
            f"{result.skipped} skipped, "
            f"{result.failed} failed"
        )
