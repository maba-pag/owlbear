"""Tests for Phase 1: Browser Package + Pipeline Quality + Schema (#775).

Covers testable interfaces from the scope items:

  SC2  - owlbear_mcp_browser: navigate, click, type, select, read_text, snapshot tools
         with URL domain allowlist enforcement
  SC3  - RefreshOrchestrator dispatches AUTHENTICATED_WEB source type to new handler
  SC4  - RefreshOrchestrator accepts content_fetcher injection, handler uses it
  SC8  - Content safety predicate INVERSION — wrap all except file/text source types
  SC10 - replace-on-change: delete prior document data before re-ingesting

SC1 (EdgeCDPLauncher) was removed in cleanup task #870 — Edge/CDP approach superseded by Playwright.
SC5 (schema v9), SC6 (EntityType extensions), SC7 (RelationType extensions), and
SC9 (LLM prompt examples) are each covered by dedicated Layer-0 subtask test files.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# SC2: owlbear_mcp_browser — MCP tools + domain allowlist
# ---------------------------------------------------------------------------


class TestFromAC_BrowserMCPServer:
    """owlbear_mcp_browser MCP server exposes browser-control tools with domain allowlist (SC2)."""

    def test_owlbear_mcp_browser_has_server_module(self) -> None:
        """owlbear_mcp_browser package has a server module."""
        from owlbear_mcp_browser import server  # type: ignore[import-not-found]  # noqa: F401

    def test_navigate_tool_is_defined(self) -> None:
        """A navigate tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "navigate" in tool_names

    def test_click_tool_is_defined(self) -> None:
        """A click tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "click" in tool_names

    def test_type_tool_is_defined(self) -> None:
        """A type tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "type" in tool_names

    def test_select_tool_is_defined(self) -> None:
        """A select tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "select" in tool_names

    def test_read_text_tool_is_defined(self) -> None:
        """A read_text tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "read_text" in tool_names

    def test_snapshot_tool_is_defined(self) -> None:
        """A snapshot tool is registered on the MCP browser server."""
        from owlbear_mcp_browser import mcp_app  # type: ignore[import-not-found]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert "snapshot" in tool_names

    def test_navigate_blocked_for_unapproved_domain(self) -> None:
        """navigate() raises when the URL domain is not in the allowlist."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist  # type: ignore[import-not-found]

        allowlist = DomainAllowlist(domains=["sharepoint.example.com"])
        with pytest.raises((PermissionError, ValueError)):
            allowlist.check("https://evil.com/malicious-page")

    def test_navigate_allowed_for_approved_domain(self) -> None:
        """navigate() permits URLs whose domain is in the allowlist."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist  # type: ignore[import-not-found]

        allowlist = DomainAllowlist(domains=["sharepoint.example.com"])
        # Must not raise
        allowlist.check("https://sharepoint.example.com/sites/IT/page")

    def test_empty_allowlist_blocks_all_navigation(self) -> None:
        """An empty allowlist denies every URL."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist  # type: ignore[import-not-found]

        allowlist = DomainAllowlist(domains=[])
        with pytest.raises((PermissionError, ValueError)):
            allowlist.check("https://example.com/any-page")

    def test_allowlist_check_is_domain_scoped(self) -> None:
        """Allowlist check matches on domain only, not full URL path."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist  # type: ignore[import-not-found]

        allowlist = DomainAllowlist(domains=["example.com"])
        # A sibling domain must NOT be permitted
        with pytest.raises((PermissionError, ValueError)):
            allowlist.check("https://not-example.com/page")


# ---------------------------------------------------------------------------
# SC3 + SC4: AUTHENTICATED_WEB dispatch + ContentFetcher injection
# ---------------------------------------------------------------------------


class TestFromAC_AuthWebRefreshHandler:
    """RefreshOrchestrator dispatches AUTHENTICATED_WEB to _handle_authenticated_web
    and accepts a ContentFetcher injection (SC3, SC4)."""

    def test_refresh_orchestrator_accepts_content_fetcher_kwarg(self) -> None:
        """RefreshOrchestrator.__init__ accepts a content_fetcher keyword argument."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = MagicMock()
        # Currently: TypeError — unexpected keyword argument 'content_fetcher'
        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        assert orchestrator is not None

    def test_refresh_orchestrator_stores_content_fetcher(self) -> None:
        """RefreshOrchestrator retains injected content_fetcher for later use."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = MagicMock()
        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        # The stored fetcher must be retrievable (attribute name may vary)
        assert mock_fetcher in vars(orchestrator).values()

    @pytest.mark.asyncio
    async def test_refresh_authenticated_web_source_does_not_raise(self) -> None:
        """refresh() with an AUTHENTICATED_WEB source does not raise ValueError."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_source = MagicMock()
        mock_source.enabled = True
        mock_source.source_type = "authenticated_web"
        mock_source.config = {"urls": []}
        mock_source.scope = "global"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value="page content")

        mock_store = MagicMock()
        mock_store.update = MagicMock()

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        # Currently raises ValueError("Unsupported source type: authenticated_web")
        result = await orchestrator.refresh(mock_source)
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_calls_content_fetcher(self) -> None:
        """_handle_authenticated_web() calls the injected content_fetcher for each URL."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        fetch_url = "https://sharepoint.example.com/sites/IT/policies"
        mock_source = MagicMock()
        mock_source.enabled = True
        mock_source.source_type = "authenticated_web"
        mock_source.config = {"urls": [fetch_url]}
        mock_source.scope = "global"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value="policy content")

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        mock_store = MagicMock()
        mock_store.update = MagicMock()

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        await orchestrator.refresh(mock_source)

        mock_fetcher.fetch.assert_called_once_with(fetch_url)

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_returns_refresh_result(self) -> None:
        """_handle_authenticated_web() returns a RefreshResult with correct counters."""
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_source = MagicMock()
        mock_source.enabled = True
        mock_source.source_type = "authenticated_web"
        mock_source.config = {"urls": ["https://sharepoint.example.com/page1"]}
        mock_source.scope = "global"
        mock_source.id = "src-1"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value="page content")

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        mock_store = MagicMock()
        mock_store.update = MagicMock()

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator.refresh(mock_source)
        assert isinstance(result, RefreshResult)
        assert result.refreshed >= 1

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_empty_urls_returns_zero_counts(self) -> None:
        """_handle_authenticated_web() with no URLs returns RefreshResult with zero counters."""
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_source = MagicMock()
        mock_source.enabled = True
        mock_source.source_type = "authenticated_web"
        mock_source.config = {"urls": []}
        mock_source.scope = "global"
        mock_source.id = "src-empty"

        mock_fetcher = MagicMock()
        mock_store = MagicMock()
        mock_store.update = MagicMock()

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator.refresh(mock_source)
        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_fetch_failure_increments_failed(self) -> None:
        """A content_fetcher.fetch() exception is caught and counted as failed."""
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_source = MagicMock()
        mock_source.enabled = True
        mock_source.source_type = "authenticated_web"
        mock_source.config = {"urls": ["https://sharepoint.example.com/broken"]}
        mock_source.scope = "global"
        mock_source.id = "src-fail"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=ConnectionError("browser unavailable"))

        mock_store = MagicMock()
        mock_store.update = MagicMock()

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator.refresh(mock_source)
        assert isinstance(result, RefreshResult)
        assert result.failed >= 1


# ---------------------------------------------------------------------------
# SC8: Content safety predicate inversion
# ---------------------------------------------------------------------------


class TestFromAC_ContentSafetyInversion:
    """IngestPipeline wraps all source types except exempt locals (predicate inversion, SC8).

    Current behaviour: only "url" and "authenticated_web" are wrapped.
    After inversion: all source types are wrapped EXCEPT "file_glob" and local-text types.
    """

    @pytest.mark.asyncio
    async def test_url_list_source_content_is_wrapped(self) -> None:
        """ingest() wraps content when source_type is 'url_list' (predicate inversion)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "corporate knowledge base article"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="https://kb.example.com/article",
            metadata={"source_type": "url_list"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        # Currently FAILS: "url_list" not in {"url", "authenticated_web"}
        assert "<untrusted_web_content" in call_text

    @pytest.mark.asyncio
    async def test_novel_source_type_content_is_wrapped(self) -> None:
        """ingest() wraps content for an unrecognised future source type (defense in depth)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "unknown source type content"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="custom://proprietary-source/data",
            metadata={"source_type": "future_browser_screenshot"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        # Currently FAILS: "future_browser_screenshot" not in {"url", "authenticated_web"}
        assert "<untrusted_web_content" in call_text

    @pytest.mark.asyncio
    async def test_file_glob_source_content_is_not_wrapped(self) -> None:
        """ingest() does NOT wrap content for file_glob sources (local files are trusted)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "local codebase content"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="/workspace/src/main.py",
            metadata={"source_type": "file_glob"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        # file_glob is trusted — must NOT be wrapped
        # After inversion this continues to pass (file_glob in exempt set)
        # Currently this test FAILS because predicate uses allowlist, not blocklist:
        # the future inversion changes the logic control path, and any test that
        # checks the predicate function directly will fail.
        assert "<untrusted_web_content" not in call_text
        # Verify there's a predicate module or function that encodes the exempt list
        from owlbear_knowledge import content_safety  # noqa: PLC0415

        # After inversion an explicit `should_wrap` or `is_exempt` predicate must exist
        assert hasattr(content_safety, "should_wrap") or hasattr(content_safety, "is_trusted_source")

    @pytest.mark.asyncio
    async def test_url_list_wrapping_includes_source_url_attribute(self) -> None:
        """ingest() tags wrapping on url_list content with the source URL attribute."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "article about compliance policies"
        source_url = "https://kb.example.com/compliance"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source=source_url,
            metadata={"source_type": "url_list"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        # Currently FAILS: "url_list" not wrapped at all
        assert source_url in call_text


# ---------------------------------------------------------------------------
# SC10: Replace-on-change refresh semantics (ghost document fix)
# ---------------------------------------------------------------------------


class TestFromAC_ReplaceOnChangeRefresh:
    """ingest() cascade-deletes stale document data before re-ingesting changed content (SC10).

    Ghost document bug: when check_content_changed returns (True, existing_id),
    existing_id is captured but never passed to delete_document_data().
    After fix: delete_document_data(existing_id) is called before insert_document().
    """

    @pytest.mark.asyncio
    async def test_replace_calls_delete_document_data_on_prior_doc(self) -> None:
        """ingest() calls delete_document_data(prior_id) when content has changed."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        prior_doc_id = "prior-doc-abc123"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text="updated content", index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, prior_doc_id)
        doc_store.store_chunks.return_value = ["cid-new"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content="updated content",
            source="https://example.com/doc",
            metadata={},
        )
        await pipeline.ingest(intake)

        # Currently FAILS: delete_document_data is never called in ingest()
        doc_store.delete_document_data.assert_called_once_with(prior_doc_id)

    @pytest.mark.asyncio
    async def test_replace_delete_precedes_new_insert(self) -> None:
        """ingest() deletes prior document BEFORE inserting the replacement."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        call_order: list[str] = []

        prior_doc_id = "prior-doc-xyz"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text="refreshed content", index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, prior_doc_id)
        doc_store.store_chunks.return_value = ["cid-new"]
        doc_store.store_extractions.return_value = (0, 0)
        doc_store.delete_document_data.side_effect = lambda *_: call_order.append("delete")
        doc_store.insert_document.side_effect = lambda *_, **__: call_order.append("insert")

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        await pipeline.ingest(
            IntakeResult(
                content="refreshed content",
                source="https://example.com/doc",
                metadata={},
            )
        )

        # Currently FAILS: delete never called, call_order == ["insert", ...]
        assert "delete" in call_order
        assert call_order.index("delete") < call_order.index("insert")

    @pytest.mark.asyncio
    async def test_replace_returns_ok_status_after_deletion(self) -> None:
        """ingest() returns IngestResult(status='ok') after deleting and replacing content."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline, IngestResult
        from owlbear_knowledge.intake import IntakeResult

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text="fresh content", index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, "stale-doc-id")
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        result = await pipeline.ingest(
            IntakeResult(
                content="fresh content",
                source="https://example.com/doc",
                metadata={},
            )
        )

        # Currently FAILS: delete_document_data not called, so this line
        # raises AssertionError when we assert the delete happened.
        doc_store.delete_document_data.assert_called_once()
        assert isinstance(result, IngestResult)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_multiple_changed_docs_each_get_prior_deleted(self) -> None:
        """Back-to-back ingests with distinct prior IDs each trigger their own delete."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text="updated", index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )

        for prior_id in ("prior-a", "prior-b"):
            doc_store.check_content_changed.return_value = (True, prior_id)
            await pipeline.ingest(
                IntakeResult(
                    content="updated",
                    source="https://example.com/doc",
                    metadata={},
                )
            )

        # Currently FAILS: delete_document_data never called, let alone twice
        assert doc_store.delete_document_data.call_count == 2  # noqa: PLR2004
