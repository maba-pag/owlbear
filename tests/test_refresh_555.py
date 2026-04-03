"""RED-phase tests for RefreshOrchestrator contract gaps (#555).

Tests AC items from #555 that are not covered by the #554 test suite
(tests/test_refresh_orchestrator.py):

- url_list handler must forward scope=source.scope to pipeline.ingest
- crawl handler must call crawl_handler with source.config dict, not the full
  KnowledgeSource object

Both tests FAIL against the current implementation because:
- url_list: pipeline.ingest is called without a scope argument (lines 159-164 of
  refresh.py), defaulting to 'global' regardless of source.scope.
- crawl: crawl_handler is called with the full KnowledgeSource (line 196), not
  source.config as the AC requires.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import KnowledgeSource, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_source(
    *,
    source_type: SourceType = SourceType.URL_LIST,
    config: dict[str, Any] | None = None,
    scope: str = "global",
) -> KnowledgeSource:
    return KnowledgeSource(
        name="src",
        source_type=source_type,
        enabled=True,
        priority=0,
        config=config or {},
        scope=scope,
        created_at=_now(),
        updated_at=_now(),
    )


def _ok_ingest_result() -> IngestResult:
    return IngestResult(
        document_id="doc-1",
        chunk_count=1,
        entity_count=0,
        edge_count=0,
        status="ok",
    )


def _make_intake_result(source: str = "https://example.com") -> IntakeResult:
    return IntakeResult(
        content="hello",
        source=source,
        metadata={"source_type": "url", "fetched_at": _now()},
    )


# ===========================================================================
# AC: url_list handler calls pipeline.ingest(intake_result, scope=source.scope)
# ===========================================================================


class TestFromAC_UrlListScopeForwarding:  # noqa: N801
    """url_list AC: "calls pipeline.ingest(intake_result, scope=source.scope)"."""

    @pytest.mark.asyncio
    async def test_url_list_passes_source_scope_to_pipeline_ingest(self) -> None:
        """pipeline.ingest must receive scope=source.scope, not the default 'global'."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://example.com"]},
                scope="my-project",
            )
            await orch.refresh(source)

        # AC requires scope=source.scope forwarded to pipeline.ingest
        pipeline_mock.ingest.assert_called_once_with(ANY, scope="my-project")


# ===========================================================================
# AC: crawl handler calls crawl_handler(config) — config dict, not full source
# ===========================================================================


class TestFromAC_CrawlHandlerReceivesConfig:  # noqa: N801
    """crawl AC: "delegates to crawl_handler(config)" — config = source.config dict."""

    @pytest.mark.asyncio
    async def test_crawl_handler_called_with_config_dict_not_source(self) -> None:
        """crawl_handler must receive source.config, not the full KnowledgeSource."""
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        crawl_handler = AsyncMock(return_value=[_ok_ingest_result()])
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        source_config: dict[str, Any] = {"seed": "https://example.com", "depth": 2}
        orch = RefreshOrchestrator(
            store=store_mock,
            pipeline=MagicMock(),
            crawl_handler=crawl_handler,
        )
        source = _make_source(
            source_type=SourceType.CRAWL,
            config=source_config,
        )
        await orch.refresh(source)

        # AC: crawl_handler(config) where config = source.config dict
        crawl_handler.assert_called_once_with(source_config)
