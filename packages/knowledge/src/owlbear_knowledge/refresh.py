"""Refresh orchestrator: drive source refresh for the knowledge graph."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

import owlbear_knowledge.intake as _intake
from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.models import KnowledgeSource, SourceType

if TYPE_CHECKING:
    from owlbear_knowledge.cancellation import CancelSignal
    from owlbear_knowledge.ingest import IngestPipeline
    from owlbear_knowledge.source_store import KnowledgeSourceStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

CrawlHandler = Callable[..., Awaitable[list[IngestResult]]]


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
        crawl_handler: Optional async callable for CRAWL-type sources.
        workspace_root: Root directory for file sandbox; defaults to Path.cwd().
    """

    def __init__(
        self,
        *,
        store: KnowledgeSourceStore | object,
        pipeline: IngestPipeline | object,
        crawl_handler: CrawlHandler | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._store = store
        self._pipeline = pipeline
        self._crawl_handler = crawl_handler
        self._workspace_root = workspace_root if workspace_root is not None else Path.cwd()

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
            ValueError: If the source is disabled or (for CRAWL) no handler is set.
        """
        if not source.enabled:
            msg = f"Source {source.id!r} is disabled"
            raise ValueError(msg)

        if source.source_type == SourceType.URL_LIST:
            result = await self._handle_url_list(source, cancel=cancel)
        elif source.source_type == SourceType.CRAWL:
            result = await self._handle_crawl(source)
        elif source.source_type == SourceType.FILE_GLOB:
            result = await self._handle_file_glob(source, cancel=cancel)
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
                ingest_result: IngestResult = await self._pipeline.ingest(intake_result)
                if ingest_result.status == "ok":
                    refreshed += 1
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

    async def _handle_crawl(self, source: KnowledgeSource) -> RefreshResult:
        if self._crawl_handler is None:
            msg = "crawl_handler is required for CRAWL sources but was not provided"
            raise ValueError(msg)

        ingest_results: list[IngestResult] = await self._crawl_handler(source)
        refreshed = skipped = failed = 0
        errors: list[str] = []

        for result in ingest_results:
            if result.status == "ok":
                refreshed += 1
            elif result.status == "skipped":
                skipped += 1
            else:
                failed += 1

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
                intake_result = await _intake.read_file(
                    file_path, workspace_root=self._workspace_root
                )
                ingest_result: IngestResult = await self._pipeline.ingest(intake_result)
                if ingest_result.status == "ok":
                    refreshed += 1
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
