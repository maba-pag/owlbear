"""Bootstrap — procedural assembly of all OwlBear components.

Wires hooks, toolsets, channels, MCP servers, agent registry, and the main
:class:`OwlBearAgent` into a :class:`BootstrapResult`.  Each ``build_*``
helper is independently testable.

Usage::

    from owlbear.bootstrap import bootstrap
    result = await bootstrap(settings, workspace_root=Path("."))
    agent = result.agent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from owlbear.channels.cli import CLIChannel
from owlbear.core.agent import OwlBearAgent
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.command_guard import CommandSafetyGuard
from owlbear.core.context_hook import ContextInjectionHook
from owlbear.core.delegation import DelegationToolset
from owlbear.core.hooks import HookRegistry
from owlbear.core.lint_hook import AutoLintHook
from owlbear.core.notification_hook import ConsoleBellBackend, NotificationHook, WinSoundBackend
from owlbear.core.observability import EventStore, ObservabilityHook
from owlbear.core.subagent_hook import SubagentVerificationHook
from owlbear.core.test_hook import TestVerificationHook
from owlbear.memory.context import ContextManager
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageTracker
from owlbear.projects.store import ProjectStore
from owlbear.providers.copilot import create_copilot_model
from owlbear.tools.ask_user import AskUserToolset
from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.toolset import BrowserToolset
from owlbear.tools.filesystem import FileToolset
from owlbear.tools.git_local import GitLocalToolset
from owlbear.tools.github_api import GitHubToolset
from owlbear.tools.hooked import HookedToolset
from owlbear.tools.kanban import KanbanToolset
from owlbear.tools.mcp_registry import MCPServerRegistry
from owlbear.tools.mcp_servers import register_default_servers
from owlbear.tools.terminal import TerminalToolset

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.progress import ProgressReporter
    from owlbear.memory.knowledge.query_service import KnowledgeQueryService
    from owlbear.projects.models import Project
    from owlbear.skills.registry import SkillRegistry

__all__ = [
    "BootstrapResult",
    "_resolve_active_project",
    "bootstrap",
    "build_agent_registry",
    "build_hooks",
    "build_mcp_registry",
    "build_toolsets",
    "create_channel",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Active project resolution
# ---------------------------------------------------------------------------


def _resolve_active_project(
    config_dir: Path,
) -> tuple[Project, ProjectStore] | None:
    """Read *config_dir/active_project* and load the corresponding :class:`Project`.

    Returns
    -------
    tuple[Project, ProjectStore] | None
        ``(project, store)`` when an active project is found, ``None`` otherwise.
        Returns ``None`` when the file is missing, empty, or the project ID
        does not correspond to a persisted project.
    """
    active_path = config_dir / "active_project"
    if not active_path.is_file():
        return None

    project_id = active_path.read_text(encoding="utf-8").strip()
    if not project_id:
        return None

    projects_dir = config_dir / "projects"
    store = ProjectStore(projects_dir)
    try:
        project = store.get(project_id)
    except FileNotFoundError:
        logger.warning("Active project '%s' not found on disk", project_id)
        return None

    return project, store


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class BootstrapResult:
    """Everything produced by :func:`bootstrap`.

    Attributes
    ----------
    progress_reporter:
        Optional :class:`~owlbear.core.progress.ProgressReporter`.  Callers
        must invoke ``await progress_reporter.start()`` at the beginning of
        each turn and ``await progress_reporter.stop()`` at the end.  A
        cleanup callable that calls ``stop()`` is also appended to
        :attr:`cleanup` so teardown always cancels the timer.
    cleanup:
        Async callables to invoke during shutdown (e.g. progress stop).
    """

    agent: OwlBearAgent
    channel: ChannelPlugin
    mcp_registry: MCPServerRegistry | None
    hooks: HookRegistry
    progress_reporter: ProgressReporter | None = None
    cleanup: list[Callable] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hook assembly
# ---------------------------------------------------------------------------


def build_hooks(
    settings: OwlBearSettings,
    *,
    workspace_root: Path | None = None,
    channel: ChannelPlugin | None = None,
) -> tuple[HookRegistry, ProgressReporter | None]:
    """Create a :class:`HookRegistry` with all standard hooks registered.

    Args:
        settings: Application settings (notification events, etc.).
        workspace_root: Workspace path for observability event storage.
        channel: Optional channel for :class:`ProgressReporter` creation.

    Returns:
        Tuple of (fully-wired :class:`HookRegistry`, optional :class:`ProgressReporter`).
    """
    hooks = HookRegistry()

    CommandSafetyGuard().register(hooks)
    AutoLintHook().register(hooks)
    SubagentVerificationHook().register(hooks)
    TestVerificationHook().register(hooks)
    ContextInjectionHook().register(hooks)

    NotificationHook(
        backends=[ConsoleBellBackend(), WinSoundBackend()],
        notification_events=settings.notification_events,
    ).register(hooks)

    if workspace_root is not None:
        event_path = workspace_root / ".owlbear" / "events.jsonl"
        ObservabilityHook(store=EventStore(event_path)).register(hooks)

    # Progress reporting — requires a channel and settings.progress_enabled
    progress_reporter: ProgressReporter | None = None
    if settings.progress_enabled and channel is not None:
        from owlbear.core.progress import ProgressReporter  # noqa: PLC0415

        progress_reporter = ProgressReporter(
            channel=channel,
            interval=settings.progress_interval,
            detail=settings.progress_detail,
        )
        progress_reporter.register(hooks)

    return hooks, progress_reporter


# ---------------------------------------------------------------------------
# Channel factory
# ---------------------------------------------------------------------------


def create_channel(settings: OwlBearSettings, channel_name: str) -> ChannelPlugin:
    """Dispatch to the correct channel adapter.

    Args:
        settings: Application settings (Slack tokens, etc.).
        channel_name: One of ``"cli"``, ``"slack"``, ``"voice"``.

    Returns:
        A :class:`ChannelPlugin` instance.

    Raises:
        ValueError: If *channel_name* is not recognized.
    """
    if channel_name == "cli":
        return CLIChannel()

    if channel_name == "slack":
        from owlbear.channels.slack import SlackChannel  # noqa: PLC0415

        has_all_slack = (
            settings.slack_app_token and settings.slack_bot_token and settings.slack_channel_id
        )
        if not has_all_slack:
            msg = "Slack channel requires slack_app_token, slack_bot_token, and slack_channel_id"
            raise ValueError(msg)
        return SlackChannel(
            app_token=settings.slack_app_token.get_secret_value(),
            bot_token=settings.slack_bot_token.get_secret_value(),
            channel_id=settings.slack_channel_id,
        )

    if channel_name == "voice":
        from owlbear.channels.voice import VoiceChannel  # noqa: PLC0415

        return VoiceChannel()

    msg = f"Unknown channel: {channel_name!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Toolset assembly
# ---------------------------------------------------------------------------


def _build_knowledge_toolset(  # noqa: PLR0913
    workspace: Path,
    project_id: str | None = None,
    *,
    chat_model: str | Model = "gpt-4o",
    max_tokens: int = 2000,
    knowledge_graph_expansion: bool = True,
    inter_doc_graph_building: bool = False,
) -> tuple[AbstractToolset, KnowledgeQueryService] | None:
    """Create a :class:`KnowledgeToolset` and :class:`KnowledgeQueryService`.

    Args:
        workspace: Root directory for knowledge DB and vector store.
        project_id: Optional active project ID.  When set, both the toolset
            and service scope queries to ``["global", "project:{id}"]``.
        chat_model: Model identifier or PydanticAI ``Model`` instance for
            agents used by :class:`EntityExtractor` and
            :class:`InterDocGraphBuilder`.
        max_tokens: Default token budget stored on the service as
            ``default_max_tokens`` for per-turn context injection.
        knowledge_graph_expansion: When ``True``, creates a
            :class:`GraphAugmentedRetriever` and passes it to the service.
        inter_doc_graph_building: When ``True``, creates an
            :class:`InterDocGraphBuilder` and passes it to the
            :class:`IngestPipeline` for cross-document relationship inference.

    Returns ``None`` when the knowledge subsystem cannot be initialised
    (e.g. missing DB, unavailable model).  All failures are logged at
    ``WARNING`` and silently swallowed.
    """
    try:
        import sqlite3  # noqa: PLC0415

        from owlbear.memory.knowledge import (  # noqa: PLC0415
            GraphStore,
            IngestPipeline,
            TextChunker,
            init_db,
        )
        from owlbear.memory.knowledge.embeddings import (  # noqa: PLC0415
            BgeM3EmbeddingProvider,
        )
        from owlbear.memory.knowledge.extractor import EntityExtractor  # noqa: PLC0415
        from owlbear.memory.knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415
        from owlbear.memory.knowledge.query_service import (  # noqa: PLC0415
            KnowledgeQueryService,
        )
        from owlbear.tools.knowledge import KnowledgeToolset  # noqa: PLC0415

        owlbear_dir = workspace / ".owlbear"
        owlbear_dir.mkdir(parents=True, exist_ok=True)
        db_path = owlbear_dir / "knowledge.db"

        conn = sqlite3.connect(str(db_path))
        init_db(conn)

        graph_store = GraphStore(conn)
        embedding_provider = BgeM3EmbeddingProvider()
        vector_store = QdrantVectorStore(location=str(owlbear_dir / "qdrant"))
        entity_extractor = EntityExtractor(model=chat_model)
        text_chunker = TextChunker()

        # Build optional inter-document graph builder.
        inter_doc_builder = None
        if inter_doc_graph_building:
            from owlbear.memory.knowledge.inter_doc_graph_builder import (  # noqa: PLC0415
                InterDocGraphBuilder,
            )

            inter_doc_builder = InterDocGraphBuilder(
                model=chat_model,
                vector_store=vector_store,
                graph_store=graph_store,
            )

        ingest_pipeline = IngestPipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            entity_extractor=entity_extractor,
            text_chunker=text_chunker,
            inter_doc_builder=inter_doc_builder,
        )

        scopes: list[str] | None = None
        if project_id:
            scopes = ["global", f"project:{project_id}"]

        # Build optional graph-augmented retriever.
        retriever = None
        if knowledge_graph_expansion:
            from owlbear.memory.knowledge.retrieval import (  # noqa: PLC0415
                GraphAugmentedRetriever,
            )

            retriever = GraphAugmentedRetriever(
                vector_store=vector_store,
                graph_store=graph_store,
                embedding_provider=embedding_provider,
            )

        service = KnowledgeQueryService(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_provider=embedding_provider,
            scopes=scopes,
            retriever=retriever,
        )
        service.default_max_tokens = max_tokens

        toolset = KnowledgeToolset(
            workspace_root=workspace,
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_provider=embedding_provider,
            ingest_pipeline=ingest_pipeline,
            project_scope=project_id,
        )
        return toolset, service  # noqa: TRY300
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create KnowledgeToolset", exc_info=True)
        return None


def _build_bookmark_toolset(
    workspace: Path,
    chat_model: str | Model = "gpt-4o",
    ingest_threshold: float = 0.7,
) -> AbstractToolset | None:
    """Create a :class:`BookmarkToolset` backed by the knowledge DB.

    Returns ``None`` when the bookmark subsystem cannot be initialised.
    All failures are logged at ``WARNING`` and silently swallowed.
    """
    try:
        import sqlite3  # noqa: PLC0415

        from owlbear.memory.knowledge import (  # noqa: PLC0415
            BookmarkStore,
            IngestPipeline,
            TextChunker,
            init_db,
        )
        from owlbear.memory.knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset  # noqa: PLC0415
        from owlbear.memory.knowledge.embeddings import (  # noqa: PLC0415
            BgeM3EmbeddingProvider,
        )
        from owlbear.memory.knowledge.evaluator import SourceEvaluator  # noqa: PLC0415
        from owlbear.memory.knowledge.extractor import EntityExtractor  # noqa: PLC0415
        from owlbear.memory.knowledge.graph import GraphStore  # noqa: PLC0415
        from owlbear.memory.knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        owlbear_dir = workspace / ".owlbear"
        owlbear_dir.mkdir(parents=True, exist_ok=True)
        db_path = owlbear_dir / "knowledge.db"

        conn = sqlite3.connect(str(db_path))
        init_db(conn)

        bookmark_store = BookmarkStore(conn)
        evaluator = SourceEvaluator(model=chat_model)

        # Build a lightweight ingest pipeline for bookmarks.
        graph_store = GraphStore(conn)
        embedding_provider = BgeM3EmbeddingProvider()
        vector_store = QdrantVectorStore(location=str(owlbear_dir / "qdrant"))
        entity_extractor = EntityExtractor(model=chat_model)
        text_chunker = TextChunker()

        ingest_pipeline = IngestPipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            entity_extractor=entity_extractor,
            text_chunker=text_chunker,
        )

        pipeline = BookmarkPipeline(
            bookmark_store=bookmark_store,
            evaluator=evaluator,
            ingest_pipeline=ingest_pipeline,
            ingest_threshold=ingest_threshold,
        )

        return BookmarkToolset(pipeline=pipeline, store=bookmark_store)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create BookmarkToolset", exc_info=True)
        return None


def _build_web_search_toolset() -> AbstractToolset | None:
    """Create a :class:`WebSearchToolset` if duckduckgo_search is available.

    Returns ``None`` when ``duckduckgo_search`` or ``trafilatura`` cannot
    be imported.  All failures are logged at ``WARNING`` and silently
    swallowed.
    """
    try:
        from owlbear.tools.web_search import WebSearchToolset  # noqa: PLC0415

        config = BrowserConfig()
        return WebSearchToolset(
            blocked_urls=config.blocked_urls,
            allowed_urls=config.allowed_urls,
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create WebSearchToolset", exc_info=True)
        return None


def _build_screenshot_components(
    settings: OwlBearSettings,
    browser_toolset: BrowserToolset,
    channel: ChannelPlugin,
    workspace: Path,
    hooks: HookRegistry,
) -> AbstractToolset:
    """Create screenshot service, visual-feedback toolset, and optional error hook.

    Registers :class:`ScreenshotOnErrorHook` on *hooks* when
    ``settings.screenshot_mode`` is not ``"manual"``.

    Returns the :class:`VisualFeedbackToolset`.
    """
    from owlbear.tools.screenshot import ScreenshotService  # noqa: PLC0415
    from owlbear.tools.visual_feedback import VisualFeedbackToolset  # noqa: PLC0415

    screenshot_service = ScreenshotService()
    toolset = VisualFeedbackToolset(
        screenshot_service=screenshot_service,
        channel=channel,
        page_getter=lambda: browser_toolset.page,
        workspace=workspace,
    )

    if settings.screenshot_mode != "manual":
        from owlbear.tools.screenshot_hook import ScreenshotOnErrorHook  # noqa: PLC0415

        ScreenshotOnErrorHook(
            screenshot_service=screenshot_service,
            browser_toolset=browser_toolset,
            workspace=workspace,
            screenshot_mode=settings.screenshot_mode,
        ).register(hooks)

    return toolset


def build_toolsets(  # noqa: PLR0913, C901
    settings: OwlBearSettings,
    workspace: Path,
    hooks: HookRegistry,
    channel: ChannelPlugin,
    active_project_id: str | None = None,
    chat_model: str | Model | None = None,
) -> tuple[list[AbstractToolset], KnowledgeQueryService | None]:
    """Build all toolsets, wrapping non-delegation ones in :class:`HookedToolset`.

    Args:
        settings: Application settings.
        workspace: Workspace root directory.
        hooks: Hook registry for HookedToolset wrapping.
        channel: Channel adapter for AskUserToolset.
        active_project_id: Optional active project ID for knowledge scoping.
        chat_model: Optional PydanticAI Model or model name for knowledge
            agents.  When ``None``, falls back to ``settings.chat_model``.

    Returns:
        Tuple of (toolset list, optional :class:`KnowledgeQueryService`).
    """
    raw: list[AbstractToolset] = []

    raw.append(FileToolset(workspace_root=workspace))
    raw.append(TerminalToolset(workspace_root=workspace, hooks=hooks))
    raw.append(AskUserToolset(channel))
    raw.append(GitLocalToolset(workspace_root=workspace, hooks=hooks))
    browser_toolset = BrowserToolset(config=BrowserConfig())
    raw.append(browser_toolset)
    raw.append(KanbanToolset(kanban_dir=workspace / "kanban", hooks=hooks))

    # Screenshot / visual-feedback wiring
    raw.append(_build_screenshot_components(settings, browser_toolset, channel, workspace, hooks))

    # Conditional toolsets
    skills_dir = workspace / ".github" / "skills"
    if skills_dir.is_dir():
        try:
            from owlbear.skills.registry import SkillRegistry  # noqa: PLC0415

            raw.append(SkillRegistry(skills_dir))
        except Exception:  # noqa: BLE001
            logger.warning("Failed to create SkillRegistry", exc_info=True)

    if settings.github_token:
        try:
            raw.append(
                GitHubToolset(
                    token=settings.github_token,
                    owner=settings.github_owner,
                    repo=settings.github_repo,
                    hooks=hooks,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to create GitHubToolset", exc_info=True)

    # Knowledge toolset — conditional on knowledge components being available
    knowledge_service: KnowledgeQueryService | None = None
    knowledge_result = _build_knowledge_toolset(
        workspace, project_id=active_project_id,
        chat_model=chat_model or settings.chat_model,
        max_tokens=settings.knowledge_context_tokens,
        knowledge_graph_expansion=settings.knowledge_graph_expansion,
        inter_doc_graph_building=settings.inter_doc_graph_building,
    )
    if knowledge_result is not None:
        knowledge_ts, knowledge_service = knowledge_result
        raw.append(knowledge_ts)

    # Bookmark toolset — conditional on knowledge components being available
    bookmark_ts = _build_bookmark_toolset(
        workspace, chat_model=chat_model or settings.chat_model,
    )
    if bookmark_ts is not None:
        raw.append(bookmark_ts)

    # Web search toolset — conditional on duckduckgo_search availability
    web_ts = _build_web_search_toolset()
    if web_ts is not None:
        raw.append(web_ts)

    # Wrap non-delegation toolsets in HookedToolset
    wrapped: list[AbstractToolset] = [HookedToolset(wrapped=ts, hooks=hooks) for ts in raw]

    # Approval gate wrapping — destructive toolsets get gated
    _destructive = {"GitLocalToolset", "TerminalToolset", "GitHubToolset"}

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
        approval_session = ApprovalSession()

        gated: list[AbstractToolset] = []
        for ts in wrapped:
            inner = ts.wrapped if isinstance(ts, HookedToolset) else ts
            if type(inner).__name__ in _destructive:
                gated.append(
                    ApprovalGateToolset(
                        wrapped=ts,
                        policy=policy,
                        session=approval_session,
                        channel=channel,
                        hooks=hooks,
                    )
                )
            else:
                gated.append(ts)
        wrapped = gated

    # DelegationToolset is NOT wrapped — it's internal dispatch
    wrapped.append(DelegationToolset())

    return wrapped, knowledge_service


# ---------------------------------------------------------------------------
# MCP registry
# ---------------------------------------------------------------------------


def build_mcp_registry(settings: OwlBearSettings) -> MCPServerRegistry | None:
    """Build the MCP server registry, or ``None`` if no servers configured.

    Args:
        settings: Application settings with ``mcp_servers`` and ``github_token``.

    Returns:
        :class:`MCPServerRegistry` or ``None``.
    """
    if not settings.mcp_servers:
        return None

    registry = MCPServerRegistry()
    try:
        register_default_servers(registry, settings)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to register MCP default servers", exc_info=True)
    return registry


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


def build_agent_registry(
    settings: OwlBearSettings,
    toolsets: list[AbstractToolset],
    mcp_registry: MCPServerRegistry | None,
    skill_registry: SkillRegistry | None = None,
) -> AgentRegistry:
    """Build and scan the :class:`AgentRegistry`.

    Args:
        settings: Application settings with ``agents_dir``.
        toolsets: Full toolset list for building the tool resolver.
        mcp_registry: Optional MCP registry for ``mcp:`` prefixed tools.
        skill_registry: Optional :class:`SkillRegistry` instance.

    Returns:
        Scanned :class:`AgentRegistry`.
    """
    # Build a name → toolset resolver from the toolsets list.
    # Agent definitions use short names (e.g. "filesystem", "kanban");
    # the alias map translates these to class names for lookup.
    _aliases: dict[str, str] = {
        "filesystem": "FileToolset",
        "terminal": "TerminalToolset",
        "ask_user": "AskUserToolset",
        "browser": "BrowserToolset",
        "delegation": "DelegationToolset",
        "git_local": "GitLocalToolset",
        "github": "GitHubToolset",
        "kanban": "KanbanToolset",
        "knowledge": "KnowledgeToolset",
        "web_search": "WebSearchToolset",
        "skills": "SkillRegistry",
    }

    tool_map: dict[str, AbstractToolset] = {}
    for ts in toolsets:
        inner = ts
        while hasattr(inner, "wrapped"):
            inner = inner.wrapped
        name = type(inner).__name__
        tool_map[name] = ts

    def _resolve(name: str) -> AbstractToolset:
        if name in tool_map:
            return tool_map[name]
        class_name = _aliases.get(name)
        if class_name and class_name in tool_map:
            return tool_map[class_name]
        msg = f"Unknown tool: {name!r}"
        raise KeyError(msg)

    registry = AgentRegistry(
        agents_dir=settings.agents_dir,
        tool_resolver=_resolve,
        skill_registry=skill_registry,
        mcp_registry=mcp_registry,
    )
    registry.scan()
    return registry


# ---------------------------------------------------------------------------
# Main bootstrap
# ---------------------------------------------------------------------------


def _add_project_toolset(
    toolsets: list[AbstractToolset],
    project_store: ProjectStore,
    config_dir: Path,
    hooks: HookRegistry,
    *,
    project_root: Path | None = None,
) -> None:
    """Append a :class:`ProjectToolset` to *toolsets* if import succeeds.

    The toolset is created with a placeholder agent reference that
    :func:`bootstrap` patches after agent construction.
    """
    try:
        from owlbear.projects.toolset import ProjectToolset  # noqa: PLC0415

        placeholder = type("_Placeholder", (), {"session": None})()
        project_toolset = ProjectToolset(
            store=project_store,
            agent=placeholder,
            config_dir=config_dir,
            project_root=project_root,
        )
        toolsets.append(HookedToolset(wrapped=project_toolset, hooks=hooks))
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create ProjectToolset", exc_info=True)


def _patch_project_toolset_agent(
    toolsets: list[AbstractToolset],
    agent: OwlBearAgent,
) -> None:
    """Replace the placeholder agent reference inside :class:`ProjectToolset`."""
    for ts in toolsets:
        inner = ts
        while hasattr(inner, "wrapped"):
            inner = inner.wrapped
        if type(inner).__name__ == "ProjectToolset":
            inner._agent = agent  # noqa: SLF001
            break


# ---------------------------------------------------------------------------
# Main bootstrap
# ---------------------------------------------------------------------------


async def bootstrap(
    settings: OwlBearSettings,
    *,
    channel_name: str = "cli",
    workspace_root: Path | None = None,
) -> BootstrapResult:
    """Wire all OwlBear components and return a :class:`BootstrapResult`.

    Args:
        settings: Application settings.
        channel_name: Channel adapter name (``"cli"``, ``"slack"``, ``"voice"``).
        workspace_root: Workspace root directory. Uses CWD when ``None``.

    Returns:
        :class:`BootstrapResult` with all assembled components.
    """
    from pathlib import Path as _Path  # noqa: PLC0415

    # 0. Project resolution — derive workspace from active project
    active_project: Project | None = None
    project_store: ProjectStore | None = None

    if workspace_root is None:
        resolved = _resolve_active_project(settings.config_dir)
        if resolved is not None:
            active_project, project_store = resolved
            workspace_root = active_project.workspace_path
            logger.info(
                "Active project '%s' → workspace %s",
                active_project.name,
                workspace_root,
            )

    workspace = workspace_root or _Path.cwd()
    cleanup: list[Callable] = []

    # 1. Channel (created first so build_hooks can wire ProgressReporter)
    channel = create_channel(settings, channel_name)

    # 2. Hooks (with channel for progress reporting)
    hooks, progress_reporter = build_hooks(
        settings, workspace_root=workspace_root, channel=channel,
    )

    # Register progress stop() in cleanup so teardown always cancels the timer
    if progress_reporter is not None:
        cleanup.append(progress_reporter.stop)

    # 3. Model (created early so knowledge agents can reuse it)
    model = await create_copilot_model(settings)

    # 4. Toolsets
    toolsets, knowledge_service = build_toolsets(
        settings, workspace, hooks, channel,
        active_project_id=active_project.id if active_project else None,
        chat_model=model,
    )

    # 4b. ProjectToolset — when an active project provides a store
    if active_project is not None and project_store is not None:
        _add_project_toolset(
            toolsets, project_store, settings.config_dir, hooks,
            project_root=settings.project_root,
        )

    # 5. MCP
    mcp_registry = build_mcp_registry(settings)

    # 6. Agent registry
    # Find SkillRegistry if present
    skill_reg = None
    for ts in toolsets:
        inner = ts
        while hasattr(inner, "wrapped"):
            inner = inner.wrapped
        if type(inner).__name__ == "SkillRegistry":
            skill_reg = inner
            break

    agent_registry = build_agent_registry(settings, toolsets, mcp_registry, skill_reg)

    # 7. Session, context, tracker
    if active_project is not None:
        session_path = (
            settings.config_dir
            / "projects"
            / active_project.id
            / "sessions"
            / "session.jsonl"
        )
    else:
        session_path = workspace / ".owlbear" / "session.jsonl"

    session = SessionStore(session_path)
    context = ContextManager(workspace)
    tracker = UsageTracker(settings.usage_path)

    # 8. Construct agent
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
    )
    agent._deps.agent_registry = agent_registry  # noqa: SLF001

    # Patch agent reference into ProjectToolset now that agent is created
    if active_project is not None:
        _patch_project_toolset_agent(toolsets, agent)

    return BootstrapResult(
        agent=agent,
        channel=channel,
        mcp_registry=mcp_registry,
        hooks=hooks,
        progress_reporter=progress_reporter,
        cleanup=cleanup,
    )
