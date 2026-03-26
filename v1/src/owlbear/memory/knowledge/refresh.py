"""Refresh orchestrator — dispatch by source type.

Reads :class:`~owlbear.memory.knowledge.models.KnowledgeSource` configs and
dispatches refresh operations to the appropriate handler (url_list, crawl,
file_glob).  Collects per-item results into a :class:`RefreshResult` summary.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.models import SourceType
from owlbear.paths import sandbox_path

if TYPE_CHECKING:
    from owlbear.memory.knowledge.cancellation import CancelSignal
    from owlbear.memory.knowledge.ingest import IngestPipeline, IngestResult
    from owlbear.memory.knowledge.models import KnowledgeSource
    from owlbear.memory.knowledge.source_store import KnowledgeSourceStore

logger = logging.getLogger(__name__)

CrawlHandler = Callable[..., Awaitable[list["IngestResult"]]]
"""Callback that receives a raw source config dict and returns ingest results.

The bootstrap layer is responsible for constructing the appropriate CrawlConfig
and wiring crawler + pipeline into the closure that implements this signature.
"""


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class RefreshResult(BaseModel):
    """Summary of a single source refresh operation."""

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
    """Dispatches refresh operations by source type.

    Args:
        store (KnowledgeSourceStore): CRUD store for knowledge source records.
        pipeline (IngestPipeline): Async ingestion pipeline (handles delta detection internally).
        crawl_handler (CrawlHandler | None): Optional callback for ``crawl``
            source types. Receives the raw
            source config dict and returns a list of :class:`IngestResult`.
        workspace_root (Path | None): Root path used as default ``base_dir``
            for ``file_glob`` sources.
    """

    def __init__(
        self,
        store: KnowledgeSourceStore,
        pipeline: IngestPipeline,
        crawl_handler: CrawlHandler | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._store = store
        self._pipeline = pipeline
        self._crawl_handler = crawl_handler
        self._workspace_root = workspace_root or Path.cwd()

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace*."""
        self._workspace_root = workspace

    # -- public API ----------------------------------------------------------

    async def refresh(
        self,
        source: KnowledgeSource,
        *,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Refresh a single knowledge source.

        Dispatches to the appropriate handler based on
        :attr:`source.source_type`.

        Raises:
            ValueError: If *source* is disabled.
        """
        if not source.enabled:
            msg = f"Source {source.id!r} is disabled"
            raise ValueError(msg)

        handler = {
            SourceType.URL_LIST: self._handle_url_list,
            SourceType.CRAWL: self._handle_crawl,
            SourceType.FILE_GLOB: self._handle_file_glob,
        }[source.source_type]

        result = await handler(source, cancel=cancel)
        self._update_source_record(source, result)
        return result

    async def refresh_all(
        self,
        scope: str | None = None,
        *,
        cancel: CancelSignal | None = None,
    ) -> list[RefreshResult]:
        """Refresh all enabled sources, ordered by priority descending.

        Args:
            scope (str | None): Optional scope filter passed to
                :meth:`KnowledgeSourceStore.list_enabled`.
            cancel (CancelSignal | None): Optional cooperative cancellation
                signal. When set, the loop stops before starting the next
                source. Any object satisfying :class:`CancelSignal` (e.g.
                :class:`asyncio.Event`) is accepted.
        """
        sources = self._store.list_enabled(scope)
        results: list[RefreshResult] = []
        for src in sources:
            if cancel is not None and cancel.is_set():
                break
            result = await self.refresh(src, cancel=cancel)
            results.append(result)
        return results

    # -- handlers ------------------------------------------------------------

    async def _handle_url_list(
        self,
        source: KnowledgeSource,
        *,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Ingest each URL in ``config['urls']``."""
        urls: list[str] = source.config.get("urls", [])
        return await self._ingest_items(source.id, urls, cancel=cancel)

    async def _handle_crawl(
        self,
        source: KnowledgeSource,
        *,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Delegate to the injected crawl handler callback."""
        if self._crawl_handler is None:
            msg = "Cannot refresh crawl source: crawl handler is not configured"
            raise ValueError(msg)

        ingest_results = await self._run_crawl_handler(source.config, cancel=cancel)

        refreshed = sum(1 for r in ingest_results if not r.skipped)
        skipped = sum(1 for r in ingest_results if r.skipped)

        return RefreshResult(
            source_id=source.id,
            refreshed=refreshed,
            skipped=skipped,
            failed=0,
            errors=[],
        )

    async def _handle_file_glob(
        self,
        source: KnowledgeSource,
        *,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Resolve file glob pattern and ingest matching files.

        Both ``base_dir`` (when provided) and each resolved glob path are
        validated with :func:`~owlbear.paths.sandbox_path` to prevent
        path-traversal escapes outside the workspace root.
        """
        pattern: str = source.config.get("pattern", "")
        base_dir_str: str | None = source.config.get("base_dir")

        if base_dir_str is not None:
            base = sandbox_path(self._workspace_root, base_dir_str)
        else:
            base = self._workspace_root

        paths = sorted(base.glob(pattern))

        # Validate each glob result against the workspace sandbox
        items: list[str] = []
        errors: list[str] = []
        for p in paths:
            try:
                sandboxed = sandbox_path(self._workspace_root, p)
                items.append(str(sandboxed))
            except PermissionError as exc:
                errors.append(f"{p}: {exc}")
                logger.warning("Skipping path outside workspace: %s", p)

        result = await self._ingest_items(source.id, items, cancel=cancel)
        # Merge sandbox errors into the ingest result
        if errors:
            return RefreshResult(
                source_id=result.source_id,
                refreshed=result.refreshed,
                skipped=result.skipped,
                failed=result.failed + len(errors),
                errors=[*result.errors, *errors],
            )
        return result

    # -- helpers -------------------------------------------------------------

    async def _ingest_items(
        self,
        source_id: str,
        items: list[str],
        *,
        cancel: CancelSignal | None = None,
    ) -> RefreshResult:
        """Ingest a list of URLs or file paths, collecting per-item results."""
        refreshed = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for item in items:
            if cancel is not None and cancel.is_set():
                break
            try:
                result: IngestResult = await self._ingest_item(item, cancel=cancel)
                if result.skipped:
                    skipped += 1
                else:
                    refreshed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"{item}: {exc}")
                logger.warning("Ingest failed for %s: %s", item, exc)

        return RefreshResult(
            source_id=source_id,
            refreshed=refreshed,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    async def _run_crawl_handler(
        self,
        config: dict[str, object],
        *,
        cancel: CancelSignal | None = None,
    ) -> list[IngestResult]:
        """Call crawl handler and pass cancel= when supported."""
        assert self._crawl_handler is not None  # narrowed by caller

        if cancel is None or not self._supports_cancel_kwarg(self._crawl_handler):
            return await self._crawl_handler(config)
        return await self._crawl_handler(config, cancel=cancel)

    async def _ingest_item(
        self,
        item: str,
        *,
        cancel: CancelSignal | None = None,
    ) -> IngestResult:
        """Call ingest pipeline and pass cancel= when supported."""
        if cancel is None or not self._supports_cancel_kwarg(self._pipeline.ingest):
            return await self._pipeline.ingest(item)

        return await self._pipeline.ingest(item, cancel=cancel)

    @staticmethod
    def _supports_cancel_kwarg(callable_obj: object) -> bool:
        """Return True when *callable_obj* supports ``cancel=``.

        AsyncMock instances commonly hold the real callable in ``side_effect``;
        check that first to avoid double invocation from fallback retries.
        """
        side_effect = getattr(callable_obj, "side_effect", None)
        target = side_effect if callable(side_effect) else callable_obj

        try:
            signature = inspect.signature(target)
        except (TypeError, ValueError):
            return True

        for param in signature.parameters.values():
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                return True
            if param.name == "cancel":
                return True
        return False

    def _update_source_record(self, source: KnowledgeSource, result: RefreshResult) -> None:
        """Persist refresh outcome on the source record."""
        now = datetime.now(tz=UTC).isoformat()

        if result.failed > 0 and result.refreshed == 0 and result.skipped == 0:
            # All items failed
            error_summary = "; ".join(result.errors[:5])
            updated = source.model_copy(
                update={
                    "last_refreshed_at": now,
                    "last_error": error_summary,
                    "updated_at": now,
                }
            )
        else:
            updated = source.model_copy(
                update={
                    "last_refreshed_at": now,
                    "last_error": None,
                    "updated_at": now,
                }
            )
        self._store.update(updated)
