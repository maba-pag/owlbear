"""Bootstrap — procedural assembly of all OwlBear components."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from owlbear.core.agent import OwlBearAgent
from owlbear.core.condenser import SummarizingCondenser
from owlbear.memory.context import ContextManager
from owlbear.memory.error_journal import ErrorJournal
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageTracker
from owlbear.providers.copilot import create_copilot_model
from owlbear.tools.mcp_servers import register_default_servers  # noqa: F401
from owlbear.tools.protocols import find_toolset

from ._types import BootstrapResult, ComponentStatus, StartupSummary
from .channel import create_channel
from .hooks import build_hooks
from .knowledge import (
    _build_bookmark_toolset,  # noqa: F401
    _build_knowledge_infra,  # noqa: F401
    _build_knowledge_source_toolset,  # noqa: F401
    _build_knowledge_toolset,  # noqa: F401
    _build_screenshot_components,  # noqa: F401
    _build_web_search_toolset,  # noqa: F401
    _KnowledgeInfra,  # noqa: F401
)
from .registry import build_agent_registry, build_mcp_registry
from .toolsets import (
    _add_project_toolset,
    _patch_project_toolset_agent,
    _resolve_active_project,
    build_toolsets,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear.config import OwlBearSettings
    from owlbear.projects.models import Project
    from owlbear.projects.store import ProjectStore

logger = logging.getLogger(__name__)


async def bootstrap(
    settings: OwlBearSettings,
    *,
    channel_name: str = "cli",
    workspace_root: Path | None = None,
) -> BootstrapResult:
    """Wire all OwlBear components and return a :class:`BootstrapResult`."""
    from pathlib import Path as _Path  # noqa: PLC0415

    active_project: Project | None = None
    project_store: ProjectStore | None = None
    if workspace_root is None:
        resolved = _resolve_active_project(settings.config_dir)
        if resolved is not None:
            active_project, project_store = resolved
            workspace_root = active_project.workspace_path
            logger.info(
                "Active project '%s' \u2192 workspace %s",
                active_project.name,
                workspace_root,
            )

    workspace = workspace_root or _Path.cwd()
    cleanup: list[Callable] = []

    error_journal = ErrorJournal(workspace)
    channel = create_channel(settings, channel_name)
    hooks, progress_reporter = build_hooks(
        settings,
        workspace_root=workspace_root,
        channel=channel,
    )
    if progress_reporter is not None:
        cleanup.append(progress_reporter.stop)

    # 3. Model (created early so knowledge agents can reuse it)
    model = await create_copilot_model(settings)

    component_statuses: list[ComponentStatus] = []
    toolsets, knowledge_service, ingest_pipeline = build_toolsets(
        settings,
        workspace,
        hooks,
        channel,
        active_project_id=active_project.id if active_project else None,
        chat_model=model,
        cleanup=cleanup,
        summary=component_statuses,
    )

    if ingest_pipeline is not None:
        from owlbear.core.retrospective_hook import RetrospectiveHook  # noqa: PLC0415

        RetrospectiveHook(
            model=model,
            ingest_pipeline=ingest_pipeline,
            kanban_root=workspace / "kanban",
        ).register(hooks)

    if active_project is not None and project_store is not None:
        _add_project_toolset(
            toolsets,
            project_store,
            settings.config_dir,
            hooks,
            project_root=settings.project_root,
            summary=component_statuses,
        )

    mcp_registry = build_mcp_registry(settings, summary=component_statuses)

    from owlbear.skills.registry import SkillRegistry  # noqa: PLC0415

    skill_reg = find_toolset(toolsets, SkillRegistry)
    agent_registry = build_agent_registry(
        settings,
        toolsets,
        mcp_registry,
        skill_reg,
        model=model,
    )

    session_path = (
        settings.config_dir / "projects" / active_project.id / "sessions" / "session.jsonl"
        if active_project is not None
        else workspace / ".owlbear" / "session.jsonl"
    )

    session = SessionStore(session_path)
    context = ContextManager(workspace)
    tracker = UsageTracker(settings.usage_path)

    history_processors = None
    if settings.condenser_enabled:
        condenser = SummarizingCondenser(
            max_events=settings.condenser_max_events,
            model=model,
        )
        history_processors = [condenser]

    agent = OwlBearAgent(
        model=model,
        session=session,
        context=context,
        hooks=hooks,
        channel=channel,
        tracker=tracker,
        provider=settings.provider,
        toolsets=toolsets,
        knowledge_service=knowledge_service,
        history_processors=history_processors,
        rigor_profile=settings.rigor_profiles[settings.default_rigor],
    )
    agent.set_agent_registry(agent_registry)

    if active_project is not None:
        _patch_project_toolset_agent(toolsets, agent)

    startup_summary = StartupSummary(
        components=component_statuses,
        workspace=workspace,
        project=active_project.name if active_project else None,
        channel_name=channel_name,
    )
    summary_text = startup_summary.format()
    logger.info("Bootstrap complete:\n%s", summary_text)

    if settings.log_startup_summary:
        await channel.send(summary_text)

    return BootstrapResult(
        agent=agent,
        channel=channel,
        mcp_registry=mcp_registry,
        hooks=hooks,
        error_journal=error_journal,
        startup_summary=startup_summary,
        progress_reporter=progress_reporter,
        cleanup=cleanup,
    )
