"""Bootstrap knowledge infrastructure and optional toolset builders."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear.memory.knowledge.query_service import KnowledgeQueryService
from owlbear.tools.browser.config import BrowserConfig

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.hooks import HookRegistry
    from owlbear.memory.knowledge.chunker import TextChunker
    from owlbear.memory.knowledge.consolidation import ConsolidationService
    from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider
    from owlbear.memory.knowledge.extractor import EntityExtractor
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.ingest import IngestPipeline
    from owlbear.memory.knowledge.qdrant import QdrantVectorStore
    from owlbear.tools.browser.toolset import BrowserToolset

logger = logging.getLogger(__name__)


@dataclass
class _KnowledgeInfra:
    """Shared infrastructure objects for knowledge and bookmark toolsets.

    Created once by :func:`_build_knowledge_infra` and passed to both
    :func:`_build_knowledge_toolset` and :func:`_build_bookmark_toolset`
    to avoid duplicate Qdrant clients (which would cause lock errors).
    """

    conn: sqlite3.Connection
    graph_store: GraphStore
    vector_store: QdrantVectorStore
    embedding_provider: BgeM3EmbeddingProvider
    entity_extractor: EntityExtractor
    text_chunker: TextChunker


def _build_knowledge_infra(
    workspace: Path,
    chat_model: str | Model = "gpt-4o",
) -> _KnowledgeInfra | None:
    """Create shared knowledge infrastructure objects once.

    Returns ``None`` when the knowledge subsystem cannot be initialised.
    All failures are logged at ``WARNING`` and silently swallowed.
    """
    try:
        import sqlite3  # noqa: PLC0415

        from owlbear.memory.knowledge import (  # noqa: PLC0415
            GraphStore,
            TextChunker,
            init_db,
        )
        from owlbear.memory.knowledge.embeddings import (  # noqa: PLC0415
            BgeM3EmbeddingProvider,
        )
        from owlbear.memory.knowledge.extractor import EntityExtractor  # noqa: PLC0415
        from owlbear.memory.knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

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

        return _KnowledgeInfra(
            conn=conn,
            graph_store=graph_store,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            entity_extractor=entity_extractor,
            text_chunker=text_chunker,
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create knowledge infrastructure", exc_info=True)
        return None


def _build_knowledge_toolset(  # noqa: PLR0913
    workspace: Path,
    infra: _KnowledgeInfra,
    project_id: str | None = None,
    *,
    chat_model: str | Model = "gpt-4o",
    max_tokens: int = 2000,
    knowledge_graph_expansion: bool = True,
    inter_doc_graph_building: bool = False,
    bg_concurrency: int = 5,
    consolidation_enabled: bool = False,
    consolidation_interval: int = 1800,  # noqa: ARG001
) -> (
    tuple[
        AbstractToolset,
        KnowledgeQueryService,
        IngestPipeline,
        ConsolidationService | None,
    ]
    | None
):
    """Create a :class:`KnowledgeToolset` and :class:`KnowledgeQueryService`.

    Returns ``None`` when the knowledge subsystem cannot be initialised.
    The fourth element is a :class:`ConsolidationService` when
    *consolidation_enabled* is ``True``, otherwise ``None``.
    """
    try:
        from owlbear.memory.knowledge import IngestPipeline  # noqa: PLC0415
        from owlbear.memory.knowledge.document_store import DocumentStore  # noqa: PLC0415
        from owlbear.memory.knowledge.enrichment import GraphEnricher  # noqa: PLC0415
        from owlbear.tools.knowledge import KnowledgeToolset  # noqa: PLC0415

        # Build optional inter-document graph builder.
        inter_doc_builder = None
        if inter_doc_graph_building:
            from owlbear.memory.knowledge.inter_doc_graph_builder import (  # noqa: PLC0415
                InterDocGraphBuilder,
            )

            inter_doc_builder = InterDocGraphBuilder(
                model=chat_model,
                vector_store=infra.vector_store,
                graph_store=infra.graph_store,
            )

        store = DocumentStore(
            conn=infra.conn,
            graph_store=infra.graph_store,
            vector_store=infra.vector_store,
            embedding_provider=infra.embedding_provider,
        )

        # Build enricher only when a graph builder is available.
        enricher: GraphEnricher | None = None
        if inter_doc_builder is not None:
            enricher = GraphEnricher(
                conn=infra.conn,
                graph_store=infra.graph_store,
                graph_builder=None,
                inter_doc_builder=inter_doc_builder,
                document_store=store,
                pipeline_name="ingest",
                bg_concurrency=bg_concurrency,
            )

        ingest_pipeline = IngestPipeline(
            store=store,
            entity_extractor=infra.entity_extractor,
            text_chunker=infra.text_chunker,
            enricher=enricher,
            workspace_root=workspace,
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
                vector_store=infra.vector_store,
                graph_store=infra.graph_store,
                embedding_provider=infra.embedding_provider,
            )

        service = KnowledgeQueryService(
            vector_store=infra.vector_store,
            graph_store=infra.graph_store,
            embedding_provider=infra.embedding_provider,
            scopes=scopes,
            retriever=retriever,
            consolidation_conn=infra.conn if consolidation_enabled else None,
        )
        service.default_max_tokens = max_tokens

        toolset = KnowledgeToolset(
            workspace_root=workspace,
            vector_store=infra.vector_store,
            graph_store=infra.graph_store,
            embedding_provider=infra.embedding_provider,
            ingest_pipeline=ingest_pipeline,
            project_scope=project_id,
        )
        # Build optional consolidation service.
        consolidation_svc = None
        if consolidation_enabled:
            from owlbear.memory.knowledge.consolidation import (  # noqa: PLC0415
                ConsolidationService,
            )

            consolidation_svc = ConsolidationService(
                conn=infra.conn,
                graph_store=infra.graph_store,
                model=chat_model,
            )

        return toolset, service, ingest_pipeline, consolidation_svc  # noqa: TRY300
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create KnowledgeToolset", exc_info=True)
        return None


def _build_bookmark_toolset(
    infra: _KnowledgeInfra,
    workspace: Path,
    chat_model: str | Model = "gpt-4o",
    ingest_threshold: float = 0.7,
) -> AbstractToolset | None:
    """Create a :class:`BookmarkToolset` backed by the knowledge DB.

    Returns ``None`` when the bookmark subsystem cannot be initialised.
    """
    try:
        from owlbear.memory.knowledge import (  # noqa: PLC0415
            BookmarkStore,
            IngestPipeline,
        )
        from owlbear.memory.knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415
        from owlbear.memory.knowledge.bookmark_toolset import BookmarkToolset  # noqa: PLC0415
        from owlbear.memory.knowledge.document_store import DocumentStore  # noqa: PLC0415
        from owlbear.memory.knowledge.evaluator import SourceEvaluator  # noqa: PLC0415

        bookmark_store = BookmarkStore(infra.conn)
        evaluator = SourceEvaluator(model=chat_model)

        store = DocumentStore(
            conn=infra.conn,
            graph_store=infra.graph_store,
            vector_store=infra.vector_store,
            embedding_provider=infra.embedding_provider,
        )

        # Build a lightweight ingest pipeline for bookmarks (no enricher).
        ingest_pipeline = IngestPipeline(
            store=store,
            entity_extractor=infra.entity_extractor,
            text_chunker=infra.text_chunker,
            workspace_root=workspace,
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


def _build_knowledge_source_toolset(
    infra: _KnowledgeInfra,
    workspace: Path,
) -> AbstractToolset | None:
    """Create a :class:`KnowledgeSourceToolset` backed by the knowledge DB.

    Returns ``None`` when the toolset cannot be initialised.
    """
    try:
        from owlbear.memory.knowledge import IngestPipeline  # noqa: PLC0415
        from owlbear.memory.knowledge.document_store import DocumentStore  # noqa: PLC0415
        from owlbear.memory.knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415
        from owlbear.memory.knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415
        from owlbear.tools.knowledge_source import KnowledgeSourceToolset  # noqa: PLC0415

        source_store = KnowledgeSourceStore(infra.conn)

        store = DocumentStore(
            conn=infra.conn,
            graph_store=infra.graph_store,
            vector_store=infra.vector_store,
            embedding_provider=infra.embedding_provider,
        )

        ingest_pipeline = IngestPipeline(
            store=store,
            entity_extractor=infra.entity_extractor,
            text_chunker=infra.text_chunker,
            workspace_root=workspace,
        )

        orchestrator = RefreshOrchestrator(
            store=source_store,
            pipeline=ingest_pipeline,
            workspace_root=workspace,
        )

        return KnowledgeSourceToolset(
            store=source_store,
            orchestrator=orchestrator,
            workspace_root=workspace,
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to create KnowledgeSourceToolset", exc_info=True)
        return None


def _build_web_search_toolset() -> AbstractToolset | None:
    """Create a :class:`WebSearchToolset` if duckduckgo_search is available.

    Returns ``None`` when ``duckduckgo_search`` or ``trafilatura`` cannot
    be imported.
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
