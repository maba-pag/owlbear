"""Refresh orchestrator — dispatch by source type.

Reads :class:`~owlbear.memory.knowledge.models.KnowledgeSource` configs and
dispatches refresh operations to the appropriate handler (url_list, crawl,
file_glob).  Collects per-item results into a :class:`RefreshResult` summary.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.models import SourceType
from owlbear.tools.browser.crawl_config import CrawlConfig
from owlbear.tools.browser.integration import crawl_and_ingest

if TYPE_CHECKING:
    from owlbear.memory.knowledge.ingest import IngestPipeline, IngestResult
    from owlbear.memory.knowledge.models import KnowledgeSource
    from owlbear.memory.knowledge.source_store import KnowledgeSourceStore
    from owlbear.tools.browser.crawler import WebCrawler

logger = logging.getLogger(__name__)


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

    Parameters
    ----------
    store:
        CRUD store for knowledge source records.
    pipeline:
        Async ingestion pipeline (handles delta detection internally).
    crawler:
        Optional web crawler for ``crawl`` source types.
    workspace_root:
        Root path used as default ``base_dir`` for ``file_glob`` sources.
    """

    def __init__(
        self,
        store: KnowledgeSourceStore,
        pipeline: IngestPipeline,
        crawler: WebCrawler | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._store = store
        self._pipeline = pipeline
        self._crawler = crawler
        self._workspace_root = workspace_root or Path.cwd()

    # -- public API ----------------------------------------------------------

    async def refresh(self, source: KnowledgeSource) -> RefreshResult:
        """Refresh a single knowledge source.

        Dispatches to the appropriate handler based on
        :attr:`source.source_type`.

        Raises
        ------
        ValueError
            If *source* is disabled.
        """
        if not source.enabled:
            msg = f"Source {source.id!r} is disabled"
            raise ValueError(msg)

        handler = {
            SourceType.URL_LIST: self._handle_url_list,
            SourceType.CRAWL: self._handle_crawl,
            SourceType.FILE_GLOB: self._handle_file_glob,
        }[source.source_type]

        result = await handler(source)
        self._update_source_record(source, result)
        return result

    async def refresh_all(
        self, scope: str | None = None
    ) -> list[RefreshResult]:
        """Refresh all enabled sources, ordered by priority descending.

        Parameters
        ----------
        scope:
            Optional scope filter passed to
            :meth:`KnowledgeSourceStore.list_enabled`.
        """
        sources = self._store.list_enabled(scope)
        results: list[RefreshResult] = []
        for src in sources:
            result = await self.refresh(src)
            results.append(result)
        return results

    # -- handlers ------------------------------------------------------------

    async def _handle_url_list(
        self, source: KnowledgeSource
    ) -> RefreshResult:
        """Ingest each URL in ``config['urls']``."""
        urls: list[str] = source.config.get("urls", [])
        return await self._ingest_items(source.id, urls)

    async def _handle_crawl(self, source: KnowledgeSource) -> RefreshResult:
        """Build CrawlConfig and delegate to crawl_and_ingest."""
        if self._crawler is None:
            msg = "Cannot refresh crawl source: crawler is not configured"
            raise ValueError(msg)

        config = self._build_crawl_config(source.config)
        ingest_results = await crawl_and_ingest(
            self._crawler, self._pipeline, config
        )

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
        self, source: KnowledgeSource
    ) -> RefreshResult:
        """Resolve file glob pattern and ingest each matching file."""
        pattern: str = source.config.get("pattern", "")
        base_dir_str: str | None = source.config.get("base_dir")

        base = Path(base_dir_str) if base_dir_str else self._workspace_root
        paths = sorted(base.glob(pattern))

        items = [str(p) for p in paths]
        return await self._ingest_items(source.id, items)

    # -- helpers -------------------------------------------------------------

    async def _ingest_items(
        self, source_id: str, items: list[str]
    ) -> RefreshResult:
        """Ingest a list of URLs or file paths, collecting per-item results."""
        refreshed = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for item in items:
            try:
                result: IngestResult = await self._pipeline.ingest(item)
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

    @staticmethod
    def _build_crawl_config(config: dict[str, object]) -> CrawlConfig:
        """Build a :class:`CrawlConfig` from a source config dict."""
        fields = {
            k: v
            for k, v in config.items()
            if k in CrawlConfig.model_fields
        }
        return CrawlConfig(**fields)

    def _update_source_record(
        self, source: KnowledgeSource, result: RefreshResult
    ) -> None:
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
