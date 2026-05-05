"""Tests for task #1326: inter_doc_builder=None kwargs assertion.

AC coverage:
  AC3 (refined): inter_doc_builder=None passed to RefreshOrchestrator in both
       app_lifespan and refresh_source; asserted via constructor kwargs check
       (same pattern as AC1 content_fetcher kwarg assertion in
       test_browser_fetcher_wiring_1325.py:174-176) — must fail if
       inter_doc_builder is changed to non-None regardless of API key env vars
       (td:1)

These tests are discriminating: they inspect RefreshOrchestrator constructor
kwargs directly and do NOT rely on env var clearing to prove the behaviour.
If inter_doc_builder is changed to non-None in either wiring site, both tests
fail regardless of which API keys are present in the environment.
"""

from __future__ import annotations

from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_mcp_knowledge.server import app_lifespan, refresh_source


# ---------------------------------------------------------------------------
# Helpers (mirrors test_browser_fetcher_wiring_1325 for self-contained clarity)
# ---------------------------------------------------------------------------

_NOW = "2026-05-04T00:00:00+00:00"


def _make_source(
    *,
    source_type: SourceType = SourceType.AUTHENTICATED_WEB,
    fetch_method: str = "http",
) -> KnowledgeSource:
    """Factory for KnowledgeSource test fixtures."""
    return KnowledgeSource(
        name="test-source",
        source_type=source_type,
        fetch_method=fetch_method,
        config={"urls": ["https://example.com/page"]},
        enabled=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _lifespan_heavy_patches() -> list[Any]:
    """Return patch objects for all heavy lifespan dependencies."""
    return [
        patch("owlbear_mcp_knowledge.server.init_db"),
        patch("owlbear_mcp_knowledge.server.GraphStore"),
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
        patch("owlbear_mcp_knowledge.server.EntityExtractor"),
        patch("owlbear_mcp_knowledge.server.IntraDocGraphBuilder"),
        patch("owlbear_mcp_knowledge.server.InterDocGraphBuilder"),
        patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
        patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        patch("owlbear_mcp_knowledge.server.DocumentStore"),
        patch("owlbear_mcp_knowledge.server.TextChunker"),
        patch("owlbear_mcp_knowledge.server.KnowledgeSourceStore"),
        patch("owlbear_mcp_knowledge.server.ContentInjectionGuard"),
        patch("owlbear_mcp_knowledge.server.IngestPipeline"),
        patch("owlbear_mcp_knowledge.server.BookmarkStore"),
        patch("owlbear_mcp_knowledge.server.SourceEvaluator"),
        patch("owlbear_mcp_knowledge.server.BookmarkPipeline"),
        patch("owlbear_mcp_knowledge.server.ConsolidationService"),
        patch(
            "owlbear_mcp_knowledge.server.make_evaluate_fn",
            return_value=AsyncMock(),
        ),
    ]


class _PatchStack:
    """Enter a list of context managers and exit them all on __exit__."""

    def __init__(self, managers: list[Any]) -> None:
        self._managers = managers
        self._active: list[Any] = []

    def __enter__(self) -> Self:
        for mgr in self._managers:
            self._active.append(mgr.__enter__())
        return self

    def __exit__(self, *exc_info: object) -> None:
        for mgr in reversed(self._managers):
            mgr.__exit__(*exc_info)


# ---------------------------------------------------------------------------
# TestFromAC_InterDocBuilderNoneWiring
# AC3 (refined): kwargs-assertion — independent of env var state
# ---------------------------------------------------------------------------


class TestFromAC_InterDocBuilderNoneWiring:
    """AC3 (refined): RefreshOrchestrator must receive inter_doc_builder=None in both
    app_lifespan and refresh_source wiring sites.

    Discriminating pattern (same as AC1 in test_browser_fetcher_wiring_1325.py):
    - Patch RefreshOrchestrator with a MagicMock
    - Run the code under test
    - Inspect constructor kwargs directly
    - Assert inter_doc_builder kwarg is present and equals None

    These tests do NOT clear API key env vars (no monkeypatch.delenv), so they
    remain discriminating regardless of which keys are set.  If inter_doc_builder
    is changed to non-None in either site the test fails — the env-var escape
    hatch used by the old test is closed.
    """

    @pytest.fixture(autouse=True)
    def _patch_home(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Redirect home to avoid touching real user data; no env var clearing.
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    @pytest.mark.asyncio
    async def test_app_lifespan_inter_doc_builder_kwarg_is_none(self) -> None:
        """app_lifespan passes inter_doc_builder=None to RefreshOrchestrator.

        Patches RefreshOrchestrator to capture constructor kwargs, then asserts
        the inter_doc_builder kwarg is present and None.  Does not rely on API
        key env vars — the assertion is on the kwarg value itself.

        Fails if inter_doc_builder is changed to a non-None value in app_lifespan.
        """
        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        patches = _lifespan_heavy_patches()
        with (
            patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls),
            _PatchStack(patches),
        ):
            async with app_lifespan(MagicMock()):
                pass

        orchestrator_cls.assert_called_once()
        _, kwargs = orchestrator_cls.call_args
        assert "inter_doc_builder" in kwargs, (
            "RefreshOrchestrator must receive inter_doc_builder= kwarg from app_lifespan; "
            "kwarg was absent"
        )
        assert kwargs["inter_doc_builder"] is None, (
            f"inter_doc_builder kwarg must be None in app_lifespan wiring, "
            f"got {kwargs['inter_doc_builder']!r}; "
            "enrichment must not be enabled in the lifespan orchestrator"
        )

    @pytest.mark.asyncio
    async def test_refresh_source_inter_doc_builder_kwarg_is_none(self) -> None:
        """refresh_source passes inter_doc_builder=None to its per-run RefreshOrchestrator.

        Patches RefreshOrchestrator to capture constructor kwargs, then asserts
        the inter_doc_builder kwarg is present and None.  Does not rely on API
        key env vars.

        Fails if inter_doc_builder is changed to a non-None value in refresh_source.
        """
        source = _make_source(fetch_method="http")

        refresh_result = MagicMock()
        refresh_result.refreshed = 1
        refresh_result.skipped = 0
        refresh_result.failed = 0
        refresh_result.source_id = source.id

        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        orchestrator_instance = MagicMock()
        orchestrator_instance.refresh = AsyncMock(return_value=refresh_result)
        orchestrator_cls.return_value = orchestrator_instance

        app_ctx = MagicMock()
        app_ctx.source_store = MagicMock()
        app_ctx.source_store.get.return_value = source
        app_ctx.refresh_orchestrator = MagicMock()  # non-None → guard passes
        app_ctx.ingest_pipeline = MagicMock()  # non-None → guard passes
        app_ctx.graph_store = MagicMock()

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context = app_ctx

        with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls):
            await refresh_source(mcp_ctx, source_id=source.id)

        orchestrator_cls.assert_called_once()
        _, kwargs = orchestrator_cls.call_args
        assert "inter_doc_builder" in kwargs, (
            "RefreshOrchestrator must receive inter_doc_builder= kwarg from refresh_source; "
            "kwarg was absent"
        )
        assert kwargs["inter_doc_builder"] is None, (
            f"inter_doc_builder kwarg must be None in refresh_source wiring, "
            f"got {kwargs['inter_doc_builder']!r}; "
            "enrichment must not be enabled in per-run refresh orchestrator"
        )
