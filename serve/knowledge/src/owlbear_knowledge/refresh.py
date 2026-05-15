"""Refresh orchestrator: drive source refresh for the knowledge graph."""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

import owlbear_knowledge.intake as _intake
from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.models import KnowledgeSource, SourceType

if TYPE_CHECKING:
    from owlbear_knowledge.cancellation import CancelSignal
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.ingest import IngestPipeline, IngestResult
    from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
    from owlbear_knowledge.source_store import KnowledgeSourceStore

logger = logging.getLogger(__name__)

_MIN_SCOPE_DOCS = 2  # guard: skip inter-doc build when scope has fewer than 2 documents

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RefreshResult(BaseModel):
    """Result of refreshing a single knowledge source."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    refreshed: int
    skipped: int
    failed: int
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class RefreshOrchestrator:
    """Orchestrates refresh operations across registered knowledge sources.

    Args:
        store: KnowledgeSourceStore (or compatible) for CRUD operations.
        pipeline: IngestPipeline for ingesting intake results.
        workspace_root: Root directory for file sandbox; defaults to Path.cwd().
        content_fetcher: Optional protocol object with an async ``fetch(url)``
            method used to retrieve content for ``AUTHENTICATED_WEB`` sources.
            When ``None``, authenticated web refresh is a no-op.
        inter_doc_builder: Optional ``InterDocGraphBuilder`` used to build
            cross-document edges after each successful ingest. When ``None``
            (the default), inter-doc graph building is disabled.
        graph_store: Optional ``GraphStore`` used to retrieve per-document
            entities and persist cross-document edges produced by
            ``inter_doc_builder``. When ``None``, inter-doc graph building is
            disabled regardless of ``inter_doc_builder``.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        store: KnowledgeSourceStore | object,
        pipeline: IngestPipeline | object,
        workspace_root: Path | None = None,
        content_fetcher: object | None = None,
        inter_doc_builder: InterDocGraphBuilder | None = None,
        graph_store: GraphStore | None = None,
    ) -> None:
        self._store = store
        self._pipeline = pipeline
        self._workspace_root = (
            workspace_root if workspace_root is not None else Path.cwd()
        )
        self._content_fetcher = content_fetcher
        self._inter_doc_builder = inter_doc_builder
        self._graph_store = graph_store

    async def refresh(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Refresh a single source and persist timing metadata.

        Args:
            source: The knowledge source to refresh.
            cancel: Optional CancelSignal; checked between items.

        Returns:
            RefreshResult with per-status counters.

        Raises:
            ValueError: If the source is disabled.
        """
        if not source.enabled:
            msg = f"Source {source.id!r} is disabled"
            raise ValueError(msg)

        if source.source_type == SourceType.URL_LIST:
            result = await self._handle_url_list(source, cancel=cancel)
        elif source.source_type == SourceType.FILE_GLOB:
            result = await self._handle_file_glob(source, cancel=cancel)
        elif source.source_type == SourceType.AUTHENTICATED_WEB:
            result = await self._handle_authenticated_web(source, cancel=cancel)
        else:
            msg = f"Unsupported source type: {source.source_type}"
            raise ValueError(msg)

        self._update_source_record(source, result)
        return result

    async def refresh_all(
        self,
        scope: str | None = None,
        cancel: CancelSignal | None = None,
    ) -> list[RefreshResult]:
        """Refresh all enabled sources sorted by priority descending.

        Args:
            scope: Optional scope filter forwarded to store.list_all.
            cancel: Optional CancelSignal; checked between sources.

        Returns:
            List of RefreshResult, one per processed source.
        """
        sources: list[KnowledgeSource] = self._store.list_all(scope)
        enabled = [s for s in sources if s.enabled]
        ordered = sorted(enabled, key=lambda s: s.priority, reverse=True)

        results: list[RefreshResult] = []
        for source in ordered:
            if cancel is not None and cancel.is_set():
                break
            try:
                result = await self.refresh(source, cancel=cancel)
                results.append(result)
            except Exception:
                logger.exception("Error refreshing source %r", source.id)
        return results

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    async def _handle_url_list(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        urls: list[str] = source.config.get("urls", [])
        refreshed = skipped = failed = 0
        errors: list[str] = []

        for url in urls:
            if cancel is not None and cancel.is_set():
                break
            try:
                intake_result = await _intake.read_url(url)
                ingest_result: IngestResult = await self._pipeline.ingest(
                    intake_result,
                    scope=source.scope,
                    source_id=source.id,
                )
                if ingest_result.status == "ok":
                    refreshed += 1
                    self._schedule_inter_doc_build(source, ingest_result.document_id)
                elif ingest_result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(str(exc))

        return RefreshResult(
            source_id=source.id,
            refreshed=refreshed,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    async def _handle_file_glob(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        pattern: str = source.config.get("pattern", "*")
        base_dir_raw: str | None = source.config.get("base_dir")
        base_dir_path = Path(base_dir_raw) if base_dir_raw else self._workspace_root

        try:
            safe_base = sandbox_path(self._workspace_root, base_dir_path)
        except PermissionError as exc:
            return RefreshResult(
                source_id=source.id,
                refreshed=0,
                skipped=0,
                failed=1,
                errors=[str(exc)],
            )

        matching_files = sorted(safe_base.glob(pattern))
        refreshed = skipped = failed = 0
        errors: list[str] = []

        for file_path in matching_files:
            if cancel is not None and cancel.is_set():
                break
            try:
                safe_path = sandbox_path(self._workspace_root, file_path)
                intake_result = await _intake.read_file(
                    safe_path, workspace_root=self._workspace_root
                )
                ingest_result: IngestResult = await self._pipeline.ingest(
                    intake_result,
                    scope=source.scope,
                    source_id=source.id,
                )
                if ingest_result.status == "ok":
                    refreshed += 1
                    self._schedule_inter_doc_build(source, ingest_result.document_id)
                elif ingest_result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(str(exc))

        return RefreshResult(
            source_id=source.id,
            refreshed=refreshed,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    async def _handle_authenticated_web(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Refresh an AUTHENTICATED_WEB source via the injected content_fetcher.

        For each URL in ``source.config["urls"]``, calls
        ``self._content_fetcher.fetch(url)`` to retrieve page content and
        ingests it through the pipeline.

        Args:
            source: The knowledge source to refresh.
            cancel: Optional CancelSignal; checked between URLs.

        Returns:
            RefreshResult with per-status counters.
        """
        if self._content_fetcher is None:
            return RefreshResult(
                source_id=str(source.id),
                refreshed=0,
                skipped=0,
                failed=0,
                errors=[],
            )

        urls: list[str] = source.config.get("urls", [])
        refreshed = skipped = failed = 0
        errors: list[str] = []

        for url in urls:
            if cancel is not None and cancel.is_set():
                break
            try:
                content: str = await self._content_fetcher.fetch(url)  # type: ignore[union-attr]
                intake_result = _intake.IntakeResult(
                    content=content,
                    source=url,
                    metadata={"source_type": "authenticated_web"},
                )
                ingest_call = self._pipeline.ingest(
                    intake_result,
                    scope=source.scope,
                    source_id=source.id,
                )
                if inspect.isawaitable(ingest_call):
                    ingest_result: IngestResult = await ingest_call
                else:
                    ingest_result = ingest_call

                status = getattr(ingest_result, "status", "ok")
                if status not in {"ok", "skipped", "failed"}:
                    status = "ok"

                if status == "ok":
                    refreshed += 1
                    document_id = str(getattr(ingest_result, "document_id", ""))
                    self._schedule_inter_doc_build(source, document_id)
                elif status == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(str(exc))

        return RefreshResult(
            source_id=str(source.id),
            refreshed=refreshed,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    def _schedule_inter_doc_build(
        self, source: KnowledgeSource, document_id: str
    ) -> None:
        """Schedule an inter-doc graph build as a non-blocking background task."""
        if self._inter_doc_builder is None or self._graph_store is None:
            return

        builder = self._inter_doc_builder
        graph_store = self._graph_store

        async def _run() -> None:
            try:
                if (
                    len(graph_store.list_documents(scopes=[source.scope]))
                    < _MIN_SCOPE_DOCS
                ):
                    return
                entities = graph_store.list_entities_for_document(document_id)
                result = await builder.build(entities, scope=source.scope)
                for edge in result.edges:
                    graph_store.insert_edge(edge)
            except Exception as exc:  # noqa: BLE001
                logger.error(  # noqa: TRY400
                    "Inter-doc build failed for source %r: %s", source.id, exc
                )

        asyncio.create_task(_run())  # noqa: RUF006

    def _update_source_record(
        self,
        source: KnowledgeSource,
        result: RefreshResult,
    ) -> None:
        """Persist last_refreshed_at and last_error to the store."""
        now = datetime.now(tz=UTC).isoformat()
        last_error = "; ".join(result.errors) if result.errors else None
        updated = source.model_copy(
            update={
                "last_refreshed_at": now,
                "last_error": last_error,
                "updated_at": now,
            }
        )
        self._store.update(updated)
