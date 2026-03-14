"""Bootstrap shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin
    from owlbear.core.agent import OwlBearAgent
    from owlbear.core.hooks import HookRegistry
    from owlbear.core.progress import ProgressReporter
    from owlbear.memory.error_journal import ErrorJournal
    from owlbear.tools.mcp_registry import MCPServerRegistry


@dataclass(frozen=True)
class ComponentStatus:
    """Status of a single bootstrap component.

    Attributes
    ----------
    name:
        Human-readable component name (e.g. ``"KnowledgeToolset"``).
    loaded:
        ``True`` when the component initialised successfully.
    error:
        Exception message when ``loaded`` is ``False``, else ``None``.
    level:
        Severity: ``"INFO"`` (loaded OK), ``"WARNING"`` (optional dep missing),
        or ``"ERROR"`` (user-configured component failed).
    """

    name: str
    loaded: bool
    error: str | None = None
    level: str = "INFO"


@dataclass(frozen=True)
class StartupSummary:
    """Aggregated bootstrap startup summary.

    Attributes
    ----------
    components:
        Status entries for each bootstrap component.
    workspace:
        Resolved workspace path.
    project:
        Active project name, or ``None``.
    channel_name:
        Channel adapter name (e.g. ``"cli"``).
    """

    components: list[ComponentStatus]
    workspace: Path
    project: str | None
    channel_name: str

    def format(self) -> str:
        """Format the summary as a human-readable multi-line string."""
        lines = ["OwlBear startup summary"]
        lines.append(f"  Workspace: {self.workspace}")
        if self.project:
            lines.append(f"  Project:   {self.project}")
        lines.append(f"  Channel:   {self.channel_name}")
        lines.append("")

        loaded = 0
        failed = 0
        skipped = 0
        for c in self.components:
            if c.loaded:
                lines.append(f"  OK    {c.name}")
                loaded += 1
            elif c.level == "ERROR":
                lines.append(f"  FAIL  {c.name} \u2014 {c.error}")
                failed += 1
            else:
                lines.append(f"  SKIP  {c.name} \u2014 {c.error}")
                skipped += 1

        lines.append("")
        lines.append(f"  {loaded} loaded, {failed} failed, {skipped} skipped")
        return "\n".join(lines)


@dataclass
class BootstrapResult:
    """Everything produced by :func:`bootstrap`.

    Attributes
    ----------
    startup_summary:
        :class:`StartupSummary` collected during bootstrap, or ``None``
        if summary collection was skipped.
    progress_reporter:
        Optional :class:`~owlbear.core.progress.ProgressReporter`.
    cleanup:
        Sync or async callables to invoke during shutdown (e.g.
        ``progress_reporter.stop``, ``openai_client.close``).
    """

    agent: OwlBearAgent
    channel: ChannelPlugin
    mcp_registry: MCPServerRegistry | None
    hooks: HookRegistry
    error_journal: ErrorJournal
    startup_summary: StartupSummary | None = None
    progress_reporter: ProgressReporter | None = None
    hydrator: Callable | None = None
    consolidation_svc: object | None = None
    cleanup: list[Callable] = field(default_factory=list)
