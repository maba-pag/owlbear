"""Refresh orchestrator: drive source refresh for the knowledge graph."""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field

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
_STATUS_COUNTER_KEYS = {
    "ok": "refreshed",
    "partial": "partial",
    "skipped": "skipped",
}


def _increment_status_count(status_counts: dict[str, int], status: str) -> None:
    """Increment a RefreshResult counter for a pipeline status string."""
    status_counts[_STATUS_COUNTER_KEYS.get(status, "failed")] += 1


def _configured_urls(source: KnowledgeSource) -> list[str]:
    """Return URL entries from either plural or singular source config keys."""
    urls: list[str] = []

    def append_url(value: str) -> None:
        url = value.strip()
        if url and url not in urls:
            urls.append(url)

    raw_urls = source.config.get("urls")
    if isinstance(raw_urls, list):
        for url in raw_urls:
            if isinstance(url, str):
                append_url(url)
    elif isinstance(raw_urls, str):
        for url in raw_urls.split(","):
            append_url(url)

    raw_url = source.config.get("url")
    if isinstance(raw_url, str):
        append_url(raw_url)
    return urls


def _no_file_glob_matches_result(source: KnowledgeSource, pattern: str) -> RefreshResult:
    """Return a failed refresh result for an empty file_glob match."""
    error = (
        f"no files matched source path {source.config['path']!r}"
        if isinstance(source.config.get("path"), str)
        else f"no files matched source pattern {pattern!r}"
    )
    return RefreshResult(
        source_id=source.id,
        refreshed=0,
        partial=0,
        skipped=0,
        failed=1,
        errors=[error],
    )


def _local_path_from_url(url: str) -> Path | None:
    """Return a local path for file:// and plain path source identifiers."""
    if url.startswith("file://"):
        raw_path = url.removeprefix("file://")
        if raw_path.startswith("localhost/"):
            raw_path = raw_path.removeprefix("localhost")
        return Path(unquote(raw_path))
    if "://" not in url:
        return Path(url)
    return None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RefreshResult(BaseModel):
    """Result of refreshing a single knowledge source."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    refreshed: int
    partial: int = 0
    skipped: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
        self._workspace_root = workspace_root if workspace_root is not None else Path.cwd()
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

    @staticmethod
    def _ingest_warnings(ingest_result: object) -> list[str]:
        warnings = getattr(ingest_result, "warnings", [])
        return [warning for warning in warnings if isinstance(warning, str)] if isinstance(warnings, list) else []

    def _record_ingest_outcome(self, source: KnowledgeSource, ingest_result: object) -> tuple[str, list[str]]:
        status = getattr(ingest_result, "status", "ok")
        if status not in {"ok", "partial", "skipped", "failed"}:
            status = "ok"

        if status in {"ok", "partial"}:
            document_id = str(getattr(ingest_result, "document_id", ""))
            if document_id:
                self._schedule_inter_doc_build(source, document_id)

        return str(status), self._ingest_warnings(ingest_result)

    async def _handle_url_list(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        urls = _configured_urls(source)
        status_counts = {"refreshed": 0, "partial": 0, "skipped": 0, "failed": 0}
        errors: list[str] = []
        warnings: list[str] = []

        if not urls:
            return RefreshResult(
                source_id=source.id,
                refreshed=0,
                partial=0,
                skipped=0,
                failed=1,
                errors=["source has no URL configured"],
            )

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
                status, ingest_warnings = self._record_ingest_outcome(source, ingest_result)
                warnings.extend(ingest_warnings)
                _increment_status_count(status_counts, status)
            except Exception as exc:  # noqa: BLE001
                status_counts["failed"] += 1
                errors.append(str(exc))

        return RefreshResult(
            source_id=source.id,
            refreshed=status_counts["refreshed"],
            partial=status_counts["partial"],
            skipped=status_counts["skipped"],
            failed=status_counts["failed"],
            errors=errors,
            warnings=warnings,
        )

    async def _handle_file_glob(
        self,
        source: KnowledgeSource,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        pattern = str(source.config.get("pattern") or source.config.get("glob") or "").strip()
        if not pattern:
            return RefreshResult(
                source_id=source.id,
                refreshed=0,
                partial=0,
                skipped=0,
                failed=1,
                errors=["source has no glob pattern configured"],
            )

        base_dir_raw: str | None = source.config.get("base_dir")
        base_dir_path = Path(base_dir_raw) if base_dir_raw else self._workspace_root
        single_source_identity = source.config.get("url") if isinstance(source.config.get("path"), str) else None

        try:
            safe_base = sandbox_path(self._workspace_root, base_dir_path)
        except PermissionError as exc:
            return RefreshResult(
                source_id=source.id,
                refreshed=0,
                partial=0,
                skipped=0,
                failed=1,
                errors=[str(exc)],
            )

        matching_files = sorted(safe_base.glob(pattern))
        status_counts = {"refreshed": 0, "partial": 0, "skipped": 0, "failed": 0}
        errors: list[str] = []
        warnings: list[str] = []

        if not matching_files:
            return _no_file_glob_matches_result(source, pattern)

        for file_path in matching_files:
            if cancel is not None and cancel.is_set():
                break
            try:
                safe_path = sandbox_path(self._workspace_root, file_path)
                intake_result = await _intake.read_file(safe_path, workspace_root=self._workspace_root)
                if isinstance(single_source_identity, str) and single_source_identity:
                    intake_result = intake_result.model_copy(update={"source": single_source_identity})
                ingest_result: IngestResult = await self._pipeline.ingest(
                    intake_result,
                    scope=source.scope,
                    source_id=source.id,
                )
                status, ingest_warnings = self._record_ingest_outcome(source, ingest_result)
                warnings.extend(ingest_warnings)
                _increment_status_count(status_counts, status)
            except Exception as exc:  # noqa: BLE001
                status_counts["failed"] += 1
                errors.append(str(exc))

        return RefreshResult(
            source_id=source.id,
            refreshed=status_counts["refreshed"],
            partial=status_counts["partial"],
            skipped=status_counts["skipped"],
            failed=status_counts["failed"],
            errors=errors,
            warnings=warnings,
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
        urls = _configured_urls(source)
        refreshed = partial = skipped = failed = 0
        errors: list[str] = []
        warnings: list[str] = []

        if not urls:
            return RefreshResult(
                source_id=str(source.id),
                refreshed=0,
                partial=0,
                skipped=0,
                failed=1,
                errors=["source has no URL configured"],
            )

        for url in urls:
            if cancel is not None and cancel.is_set():
                break
            try:
                intake_result = await self._read_authenticated_url(url)
                ingest_call = self._pipeline.ingest(
                    intake_result,
                    scope=source.scope,
                    source_id=source.id,
                )
                if inspect.isawaitable(ingest_call):
                    ingest_result: IngestResult = await ingest_call
                else:
                    ingest_result = ingest_call

                status, ingest_warnings = self._record_ingest_outcome(source, ingest_result)
                warnings.extend(ingest_warnings)
                if status == "ok":
                    refreshed += 1
                elif status == "partial":
                    partial += 1
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
            partial=partial,
            skipped=skipped,
            failed=failed,
            errors=errors,
            warnings=warnings,
        )

    async def _read_authenticated_url(self, url: str) -> _intake.IntakeResult:
        """Read a configured authenticated-web URL or legacy local file URL."""
        local_path = _local_path_from_url(url)
        if local_path is not None:
            safe_path = sandbox_path(self._workspace_root, local_path)
            intake_result = await _intake.read_file(safe_path, workspace_root=self._workspace_root)
            return intake_result.model_copy(update={"source": url})

        if self._content_fetcher is None:
            msg = "content fetcher not available"
            raise RuntimeError(msg)

        content: str = await self._content_fetcher.fetch(url)  # type: ignore[union-attr]
        return _intake.IntakeResult(
            content=content,
            source=url,
            metadata={"source_type": "authenticated_web"},
        )

    def _schedule_inter_doc_build(self, source: KnowledgeSource, document_id: str) -> None:
        """Schedule an inter-doc graph build as a non-blocking background task."""
        if self._inter_doc_builder is None or self._graph_store is None:
            return

        builder = self._inter_doc_builder
        graph_store = self._graph_store

        async def _run() -> None:
            try:
                if len(graph_store.list_documents(scopes=[source.scope])) < _MIN_SCOPE_DOCS:
                    return
                entities = graph_store.list_entities(scopes=[source.scope])
                result = await builder.build(entities, scope=source.scope)
                for edge in result.edges:
                    edge_document_id = edge.metadata.get("document_id")
                    if not isinstance(edge_document_id, str) or not edge_document_id:
                        edge_document_id = document_id
                    scoped_edge = edge.model_copy(update={"scope": source.scope})
                    graph_store.insert_edge(scoped_edge, document_id=edge_document_id)
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
        """Persist source refresh check state to the store."""
        if result.refreshed == 0 and result.partial == 0 and result.skipped == 0 and result.failed == 0:
            return

        now = datetime.now(tz=UTC).isoformat()
        update: dict[str, str | None] = {
            "last_checked_at": now,
            "updated_at": now,
        }

        if result.refreshed > 0 or result.partial > 0:
            messages = [*result.errors, *result.warnings]
            update["last_refreshed_at"] = now
            update["last_error"] = "; ".join(messages) if messages else None
        elif result.failed > 0:
            update["last_error"] = "; ".join(result.errors) if result.errors else None
        else:
            update["last_error"] = None

        updated = source.model_copy(update=update)
        self._store.update(updated)
