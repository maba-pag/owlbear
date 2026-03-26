"""Bootstrap toolset assembly and wrapping."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from owlbear.core.delegation import DelegationToolset
from owlbear.paths import sandbox_path
from owlbear.tools.ask_user import AskUserToolset
from owlbear.tools.browser.toolset import BrowserToolset
from owlbear.tools.filesystem import FileToolset
from owlbear.tools.git_local import GitLocalToolset
from owlbear.tools.github_api import GitHubToolset
from owlbear.tools.hooked import HookedToolset
from owlbear.tools.kanban import KanbanToolset
from owlbear.tools.protocols import unwrap
from owlbear.tools.terminal import TerminalToolset

from ._types import ComponentStatus
from .knowledge import _build_screenshot_components

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import BrowserConfig, OwlBearSettings
    from owlbear.core.hooks import HookRegistry
    from owlbear.memory.context import ContextManager
    from owlbear.memory.knowledge.consolidation import ConsolidationService
    from owlbear.memory.knowledge.ingest import IngestPipeline
    from owlbear.memory.knowledge.query_service import KnowledgeQueryService
    from owlbear.memory.session import SessionStore
    from owlbear.memory.usage import UsageTracker
    from owlbear.projects.models import Project
    from owlbear.projects.store import ProjectStore
    from owlbear.safety.audit_log import SecurityAuditLog

logger = logging.getLogger(__name__)


def _build_security_audit_sink(
    audit_log: SecurityAuditLog | None,
) -> Callable[[object], None] | None:
    """Return an adapter sink that writes runtime events to ``SecurityAuditLog``."""
    if audit_log is None:
        return None

    def _sink(event: object) -> None:
        metadata = getattr(event, "metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        raw_tool_name = getattr(event, "tool_name", None)
        tool_name = str(raw_tool_name) if raw_tool_name is not None else None

        raw_timestamp = getattr(event, "timestamp", None)
        timestamp = str(raw_timestamp) if raw_timestamp else None

        audit_log.log(
            event_type=str(getattr(event, "event_type", "security_event")),
            severity=str(getattr(event, "severity", "medium")),
            actor=str(getattr(event, "actor", "agent")),
            session_id=str(getattr(event, "session_id", "")),
            tool_name=tool_name,
            detail=str(getattr(event, "detail", "")),
            metadata=metadata,
            timestamp=timestamp,
        )

    return _sink


def _resolve_active_project(
    config_dir: Path,
) -> tuple[Project, ProjectStore] | None:
    """Read *config_dir/active_project* and load the corresponding project."""
    from owlbear.projects.store import ProjectStore  # noqa: PLC0415

    active_path = config_dir / "active_project"
    if not active_path.is_file():
        return None
    project_id = active_path.read_text(encoding="utf-8").strip()
    if not project_id:
        return None
    store = ProjectStore(config_dir / "projects")
    try:
        project = store.get(project_id)
    except FileNotFoundError:
        logger.warning("Active project '%s' not found on disk", project_id)
        return None
    return project, store


def _wire_knowledge_toolsets(  # noqa: C901, PLR0912, PLR0913, PLR0915
    raw: list[AbstractToolset],
    settings: OwlBearSettings,
    workspace: Path,
    chat_model: str | Model | None,
    active_project_id: str | None,
    cleanup: list[Callable] | None,
    summary: list[ComponentStatus],
    _pkg: object,
    tracker: UsageTracker | None = None,
    provider: str = "copilot",
) -> tuple[KnowledgeQueryService | None, IngestPipeline | None, ConsolidationService | None]:
    """Build knowledge, bookmark, source, and web-search toolsets.

    Uses *_pkg* (the package module) to resolve ``_build_knowledge_infra``
    so that ``mock.patch("owlbear.bootstrap._build_knowledge_infra")`` works.
    """
    knowledge_service: KnowledgeQueryService | None = None
    ingest_pipeline: IngestPipeline | None = None
    consolidation_svc: ConsolidationService | None = None

    # Resolve to a Model instance so bare-string DeprecationWarnings are not raised.
    # In production build_toolsets() is always called with a Model from bootstrap(),
    # so this branch only runs in tests / edge callers that omit chat_model.
    if isinstance(chat_model, str) or chat_model is None:
        from pydantic_ai.models.openai import OpenAIChatModel  # noqa: PLC0415
        from pydantic_ai.providers.openai import OpenAIProvider  # noqa: PLC0415

        resolved_model: Model = OpenAIChatModel(
            chat_model or settings.chat_model,
            provider=OpenAIProvider(api_key="placeholder"),
        )
    else:
        resolved_model = chat_model

    try:
        infra_kwargs: dict[str, object] = {
            "chat_model": resolved_model,
        }
        if tracker is not None:
            infra_kwargs["tracker"] = tracker
            infra_kwargs["provider"] = provider

        infra = _pkg._build_knowledge_infra(  # noqa: SLF001
            workspace,
            **infra_kwargs,
        )
    except Exception as exc:  # noqa: BLE001
        infra = None
        summary.append(
            ComponentStatus(
                name="KnowledgeInfra",
                loaded=False,
                error=str(exc),
                level="ERROR",
            )
        )

    if infra is not None:
        summary.append(ComponentStatus(name="KnowledgeInfra", loaded=True))
        if cleanup is not None:
            cleanup.append(infra.conn.close)

        knowledge_kwargs: dict[str, object] = {
            "project_id": active_project_id,
            "chat_model": resolved_model,
            "max_tokens": settings.knowledge_context_tokens,
            "knowledge_graph_expansion": settings.knowledge_graph_expansion,
            "inter_doc_graph_building": settings.inter_doc_graph_building,
            "bg_concurrency": settings.ingest_bg_concurrency,
            "consolidation_enabled": settings.consolidation_enabled,
            "consolidation_interval": settings.consolidation_interval,
        }
        if cleanup is not None:
            knowledge_kwargs["cleanup"] = cleanup
        if tracker is not None:
            knowledge_kwargs["tracker"] = tracker
            knowledge_kwargs["provider"] = provider

        knowledge_result = _pkg._build_knowledge_toolset(  # noqa: SLF001
            workspace,
            infra,
            **knowledge_kwargs,
        )
        if knowledge_result is not None:
            knowledge_ts, knowledge_service, ingest_pipeline, consolidation_svc = knowledge_result
            raw.append(knowledge_ts)
            summary.append(ComponentStatus(name="KnowledgeToolset", loaded=True))
        else:
            summary.append(
                ComponentStatus(
                    name="KnowledgeToolset",
                    loaded=False,
                    error="initialization failed",
                    level="ERROR",
                )
            )

        bookmark_kwargs: dict[str, object] = {
            "chat_model": resolved_model,
        }
        if tracker is not None:
            bookmark_kwargs["tracker"] = tracker
            bookmark_kwargs["provider"] = provider

        bookmark_ts = _pkg._build_bookmark_toolset(  # noqa: SLF001
            infra,
            workspace,
            **bookmark_kwargs,
        )
        if bookmark_ts is not None:
            raw.append(bookmark_ts)
            summary.append(ComponentStatus(name="BookmarkToolset", loaded=True))
        else:
            summary.append(
                ComponentStatus(
                    name="BookmarkToolset",
                    loaded=False,
                    error="initialization failed",
                    level="WARNING",
                )
            )

        source_ts = _pkg._build_knowledge_source_toolset(  # noqa: SLF001
            infra,
            workspace,
        )
        if source_ts is not None:
            raw.append(source_ts)
            summary.append(
                ComponentStatus(name="KnowledgeSourceToolset", loaded=True),
            )
        else:
            summary.append(
                ComponentStatus(
                    name="KnowledgeSourceToolset",
                    loaded=False,
                    error="initialization failed",
                    level="WARNING",
                )
            )
    elif not any(c.name == "KnowledgeInfra" for c in summary):
        summary.append(
            ComponentStatus(
                name="KnowledgeInfra",
                loaded=False,
                error="initialization failed",
                level="ERROR",
            )
        )

    return knowledge_service, ingest_pipeline, consolidation_svc


def _wire_web_search(
    raw: list[AbstractToolset],
    summary: list[ComponentStatus],
    browser_config: BrowserConfig | None = None,
) -> None:
    """Add web search toolset if available."""
    _pkg = sys.modules[__package__]
    try:
        web_ts = _pkg._build_web_search_toolset(browser_config=browser_config)  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        web_ts = None
        summary.append(
            ComponentStatus(
                name="WebSearchToolset",
                loaded=False,
                error=str(exc),
                level="WARNING",
            )
        )
    if web_ts is not None:
        raw.append(web_ts)
        summary.append(ComponentStatus(name="WebSearchToolset", loaded=True))
    elif not any(c.name == "WebSearchToolset" for c in summary):
        summary.append(
            ComponentStatus(
                name="WebSearchToolset",
                loaded=False,
                error="optional dependency missing",
                level="WARNING",
            )
        )


def _wrap_toolsets(
    raw: list[AbstractToolset],
    settings: OwlBearSettings,
    hooks: HookRegistry,
    channel: ChannelPlugin,
    audit_sink: Callable[[object], None] | None = None,
) -> list[AbstractToolset]:
    """Wrap toolsets in HookedToolset and optionally ApprovalGateToolset."""
    wrapped: list[AbstractToolset] = [HookedToolset(wrapped=ts, hooks=hooks) for ts in raw]

    _destructive_types = (GitLocalToolset, TerminalToolset, GitHubToolset)

    if settings.approval_policy:
        from owlbear.safety.gate import ApprovalGateToolset  # noqa: PLC0415
        from owlbear.safety.policy import (  # noqa: PLC0415
            ApprovalPolicy,
            ApprovalRule,
            ApprovalSession,
        )

        policy = ApprovalPolicy(
            rules=[ApprovalRule(**r) for r in settings.approval_policy],
            default_timeout=settings.approval_timeout,
        )
        session = ApprovalSession()

        gated: list[AbstractToolset] = []
        for ts in wrapped:
            inner = unwrap(ts)
            if isinstance(inner, _destructive_types):
                gated.append(
                    ApprovalGateToolset(
                        wrapped=ts,
                        policy=policy,
                        session=session,
                        channel=channel,
                        hooks=hooks,
                        audit_sink=audit_sink,
                    )
                )
            else:
                gated.append(ts)
        wrapped = gated

    wrapped.append(DelegationToolset())
    return wrapped


def build_toolsets(  # noqa: PLR0913
    settings: OwlBearSettings,
    workspace: Path,
    hooks: HookRegistry,
    channel: ChannelPlugin,
    active_project_id: str | None = None,
    chat_model: str | Model | None = None,
    tracker: UsageTracker | None = None,
    provider: str = "copilot",
    audit_log: SecurityAuditLog | None = None,
    cleanup: list[Callable] | None = None,
    summary: list[ComponentStatus] | None = None,
) -> tuple[
    list[AbstractToolset],
    KnowledgeQueryService | None,
    IngestPipeline | None,
    ConsolidationService | None,
]:
    """Build all toolsets, wrapping non-delegation ones in :class:`HookedToolset`.

    Returns:
    -------
    tuple
        Toolset list, optional knowledge service, optional ingest pipeline,
        optional consolidation service.
    """
    # Resolve _build_knowledge_infra through the package module so that
    # ``mock.patch("owlbear.bootstrap._build_knowledge_infra", ...)`` works.
    _pkg = sys.modules[__package__]
    audit_sink = _build_security_audit_sink(audit_log)

    raw: list[AbstractToolset] = []

    raw.append(FileToolset(workspace_root=workspace))
    raw.append(TerminalToolset(workspace_root=workspace, hooks=hooks, audit_sink=audit_sink))
    raw.append(AskUserToolset(channel, hooks=hooks))
    raw.append(GitLocalToolset(workspace_root=workspace, hooks=hooks))
    profile_dir = sandbox_path(workspace, "browser_profiles")
    profile_dir.mkdir(parents=True, exist_ok=True)
    browser_toolset = BrowserToolset(config=settings.browser)
    raw.append(browser_toolset)
    raw.append(KanbanToolset(kanban_dir=workspace / "kanban", hooks=hooks))

    # Screenshot / visual-feedback wiring
    raw.append(_build_screenshot_components(settings, browser_toolset, channel, workspace, hooks))

    # Conditional toolsets
    _summary = summary if summary is not None else []

    skills_dir = workspace / ".github" / "skills"
    if skills_dir.is_dir():
        try:
            from owlbear.skills.registry import SkillRegistry  # noqa: PLC0415

            raw.append(SkillRegistry(skills_dir))
            _summary.append(ComponentStatus(name="SkillRegistry", loaded=True))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to create SkillRegistry", exc_info=True)
            _summary.append(
                ComponentStatus(name="SkillRegistry", loaded=False, error=str(exc), level="WARNING")
            )

    if settings.github_token:
        try:
            github_toolset = GitHubToolset(
                token=settings.github_token,
                owner=settings.github_owner,
                repo=settings.github_repo,
                hooks=hooks,
            )
            raw.append(github_toolset)
            if cleanup is not None:
                cleanup.append(github_toolset.aclose)
            _summary.append(ComponentStatus(name="GitHubToolset", loaded=True))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to create GitHubToolset", exc_info=True)
            _summary.append(
                ComponentStatus(name="GitHubToolset", loaded=False, error=str(exc), level="ERROR")
            )

    # Knowledge + web search toolsets
    knowledge_service, ingest_pipeline, consolidation_svc = _wire_knowledge_toolsets(
        raw,
        settings,
        workspace,
        chat_model,
        active_project_id,
        cleanup,
        _summary,
        _pkg,
        tracker=tracker,
        provider=provider,
    )
    _wire_web_search(raw, _summary, browser_config=settings.browser)

    # Wrap and gate
    wrapped = _wrap_toolsets(raw, settings, hooks, channel, audit_sink=audit_sink)
    return wrapped, knowledge_service, ingest_pipeline, consolidation_svc


def _add_project_toolset(  # noqa: PLR0913
    toolsets: list[AbstractToolset],
    project_store: ProjectStore,
    config_dir: Path,
    hooks: HookRegistry,
    *,
    session: SessionStore,
    context: ContextManager | None = None,
    agent_toolsets: list[AbstractToolset] | None = None,
    project_root: Path | None = None,
    summary: list[ComponentStatus] | None = None,
) -> None:
    """Append a :class:`ProjectToolset` to *toolsets* if import succeeds."""
    try:
        from owlbear.projects.toolset import ProjectToolset  # noqa: PLC0415

        project_toolset = ProjectToolset(
            store=project_store,
            session=session,
            config_dir=config_dir,
            context=context,
            toolsets=agent_toolsets,
            project_root=project_root,
        )
        toolsets.append(HookedToolset(wrapped=project_toolset, hooks=hooks))
        if summary is not None:
            summary.append(ComponentStatus(name="ProjectToolset", loaded=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to create ProjectToolset", exc_info=True)
        if summary is not None:
            summary.append(
                ComponentStatus(name="ProjectToolset", loaded=False, error=str(exc), level="ERROR")
            )
