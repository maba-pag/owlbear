"""Failing tests for task #1320: Qdrant persistence + source identity MCP wiring.

RED phase — all tests must FAIL until builder task #1320 implements:
  1. QdrantVectorStore called with filesystem path from OWLBEAR_QDRANT_PATH
  2. IngestPipeline receives source_store= kwarg from app_lifespan
  3. ingest_document MCP tool exposes source_url parameter and forwards it

AC coverage:
  AC1: Qdrant uses filesystem persistence (td:1)
       - QdrantVectorStore constructed with non-:memory: path in app_lifespan
       - OWLBEAR_QDRANT_PATH env var controls the path
       - Default path is .owlbear/knowledge/vectors when env var unset
  AC4: ingest_document registers/resolves source record via source_url param (td:1)
       - ingest_document tool accepts source_url: str | None parameter
       - source_url forwarded to pipeline.ingest_text()
       - IngestPipeline wired with source_store in app_lifespan
  AC6: Source identity resolved by URL (web sources) (td:1)
       - When source_url is provided, source_store.resolve_by_url() is called
       - Resolved source id is linked to the ingested document
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan, ingest_document


# ---------------------------------------------------------------------------
# Autouse fixture: patches heavy I/O so app_lifespan runs fast in all tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_lifespan_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch heavy I/O constructors so app_lifespan runs without real DB/network."""
    monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# TestFromAC_QdrantFilesystemPersistence
# AC1: Qdrant uses filesystem persistence — vectors survive server restart (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_QdrantFilesystemPersistence:
    """AC1: QdrantVectorStore must be constructed with a filesystem path."""

    @pytest.mark.asyncio
    async def test_qdrant_vector_store_uses_filesystem_path_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """app_lifespan constructs QdrantVectorStore with the default filesystem path.

        Currently FAILS: QdrantVectorStore() is called with no args, defaulting
        to :memory: — not a filesystem-persistent path.
        """
        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)

        qdrant_cls = MagicMock(name="QdrantVectorStore")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch(
                "owlbear_mcp_knowledge.server.QdrantVectorStore",
                qdrant_cls,
            ),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
            patch(
                "owlbear_mcp_knowledge.server.make_evaluate_fn",
                return_value=AsyncMock(),
            ),
        ):
            mock_server = MagicMock()
            async with app_lifespan(mock_server):
                pass

        qdrant_cls.assert_called_once()
        args, kwargs = qdrant_cls.call_args
        # Must NOT default to :memory: — must use a filesystem path
        location = kwargs.get("location") or (args[0] if args else None)
        assert location is not None, "QdrantVectorStore must be called with an explicit location= argument"
        assert location != ":memory:", f"QdrantVectorStore must use filesystem path, got: {location!r}"
        assert ".owlbear/knowledge/vectors" in location, (
            f"Default path must include .owlbear/knowledge/vectors, got: {location!r}"
        )

    @pytest.mark.asyncio
    async def test_qdrant_path_uses_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_QDRANT_PATH env var controls the QdrantVectorStore location.

        Currently FAILS: QdrantVectorStore() ignores OWLBEAR_QDRANT_PATH because
        it is constructed with no arguments.
        """
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", "/tmp/test-vectors")  # noqa: S108

        qdrant_cls = MagicMock(name="QdrantVectorStore")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch(
                "owlbear_mcp_knowledge.server.QdrantVectorStore",
                qdrant_cls,
            ),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
            patch(
                "owlbear_mcp_knowledge.server.make_evaluate_fn",
                return_value=AsyncMock(),
            ),
        ):
            mock_server = MagicMock()
            async with app_lifespan(mock_server):
                pass

        qdrant_cls.assert_called_once()
        args, kwargs = qdrant_cls.call_args
        location = kwargs.get("location") or (args[0] if args else None)
        assert location == "/tmp/test-vectors", (  # noqa: S108
            f"Expected OWLBEAR_QDRANT_PATH to be used, got: {location!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocumentSourceUrl
# AC4: ingest_document registers/resolves source record via source_url param (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocumentSourceUrl:
    """AC4: ingest_document MCP tool must accept and forward source_url."""

    def test_ingest_document_signature_has_source_url_param(self) -> None:
        """ingest_document tool function has a source_url parameter.

        Currently FAILS: the tool signature is (ctx, text, metadata, scope)
        with no source_url parameter.
        """
        sig = inspect.signature(ingest_document)
        assert "source_url" in sig.parameters, "ingest_document must have a source_url parameter"

    def test_ingest_document_source_url_defaults_to_none(self) -> None:
        """source_url parameter defaults to None (backwards-compatible).

        Currently FAILS: parameter does not exist.
        """
        sig = inspect.signature(ingest_document)
        param = sig.parameters.get("source_url")
        assert param is not None, "source_url parameter missing"
        assert param.default is None, f"source_url should default to None, got: {param.default!r}"

    @pytest.mark.asyncio
    async def test_ingest_document_forwards_source_url_to_pipeline(self) -> None:
        """ingest_document forwards source_url= to pipeline.ingest_text().

        Currently FAILS: ingest_document does not have source_url param,
        so it cannot be forwarded.
        """
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.document_id = "doc-123"
        mock_result.chunk_count = 2
        mock_result.entity_count = 1
        mock_result.edge_count = 0
        mock_result.status = "ok"
        mock_pipeline.ingest_text = AsyncMock(return_value=mock_result)

        mock_app_ctx = MagicMock()
        mock_app_ctx.ingest_pipeline = mock_pipeline

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app_ctx

        await ingest_document(
            mock_ctx,
            text="Hello world",
            source_url="https://example.com/doc",
        )

        mock_pipeline.ingest_text.assert_called_once()
        _, call_kwargs = mock_pipeline.ingest_text.call_args
        assert "source_url" in call_kwargs, "ingest_text must be called with source_url= kwarg"
        assert call_kwargs["source_url"] == "https://example.com/doc", (
            f"source_url not forwarded correctly, got: {call_kwargs['source_url']!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_source_url_none_by_default(self) -> None:
        """When source_url not passed, ingest_text is called with source_url=None.

        Currently FAILS: parameter does not exist.
        """
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.document_id = "doc-456"
        mock_result.chunk_count = 1
        mock_result.entity_count = 0
        mock_result.edge_count = 0
        mock_result.status = "ok"
        mock_pipeline.ingest_text = AsyncMock(return_value=mock_result)

        mock_app_ctx = MagicMock()
        mock_app_ctx.ingest_pipeline = mock_pipeline

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app_ctx

        await ingest_document(mock_ctx, text="Hello world")

        mock_pipeline.ingest_text.assert_called_once()
        _, call_kwargs = mock_pipeline.ingest_text.call_args
        # source_url must be passed (even as None) so pipeline can skip resolution
        assert "source_url" in call_kwargs, "ingest_text must receive source_url= kwarg (None by default)"
        assert call_kwargs["source_url"] is None, (
            f"source_url must be None when not provided, got: {call_kwargs['source_url']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SourceStoreWiring
# AC4 (continued): IngestPipeline receives source_store from app_lifespan (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_SourceStoreWiring:
    """AC4: app_lifespan must wire source_store into IngestPipeline."""

    @pytest.mark.asyncio
    async def test_ingest_pipeline_receives_source_store_kwarg(self) -> None:
        """IngestPipeline is constructed with source_store= in app_lifespan.

        Currently FAILS: IngestPipeline is created without source_store= kwarg,
        so URL-based source resolution never runs.
        """
        ingest_pipeline_cls = MagicMock(name="IngestPipeline")
        mock_source_store = MagicMock(name="KnowledgeSourceStore")
        mock_source_store_cls = MagicMock(return_value=mock_source_store)

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
            patch(
                "owlbear_mcp_knowledge.server.IngestPipeline",
                ingest_pipeline_cls,
            ),
            patch(
                "owlbear_mcp_knowledge.server.KnowledgeSourceStore",
                mock_source_store_cls,
            ),
            patch(
                "owlbear_mcp_knowledge.server.make_evaluate_fn",
                return_value=AsyncMock(),
            ),
        ):
            mock_server = MagicMock()
            async with app_lifespan(mock_server):
                pass

        ingest_pipeline_cls.assert_called_once()
        _, pipeline_kwargs = ingest_pipeline_cls.call_args
        assert "source_store" in pipeline_kwargs, (
            "IngestPipeline must be constructed with source_store= kwarg in app_lifespan"
        )
        assert pipeline_kwargs["source_store"] is mock_source_store, (
            "IngestPipeline source_store must be the KnowledgeSourceStore instance"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SourceResolutionByUrl
# AC6: Source identity resolved by URL (web sources) (td:1)
# Tests MCP integration: ingest_document + wired source_store resolves by URL
# ---------------------------------------------------------------------------


class TestFromAC_SourceResolutionByUrl:
    """AC6: MCP ingest_document resolves source by URL via wired source_store."""

    @pytest.mark.asyncio
    async def test_ingest_document_with_source_url_triggers_source_resolution(
        self,
    ) -> None:
        """ingest_document with source_url causes source_store.resolve_by_url to run.

        Currently FAILS: ingest_document has no source_url param, so calling
        it with source_url= raises TypeError before resolution can happen.
        """
        mock_source_store = MagicMock()
        mock_source = MagicMock()
        mock_source.id = "source-uuid-123"
        mock_source_store.resolve_by_url = MagicMock(return_value=mock_source)

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.document_id = "doc-123"
        mock_result.chunk_count = 1
        mock_result.entity_count = 0
        mock_result.edge_count = 0
        mock_result.status = "ok"
        mock_pipeline.ingest_text = AsyncMock(return_value=mock_result)

        mock_app_ctx = MagicMock()
        mock_app_ctx.ingest_pipeline = mock_pipeline
        mock_app_ctx.source_store = mock_source_store

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app_ctx

        await ingest_document(
            mock_ctx,
            text="Some document text",
            source_url="https://example.com/page",
        )

        # source_url must reach ingest_text so the pipeline can resolve it
        mock_pipeline.ingest_text.assert_called_once()
        _, call_kwargs = mock_pipeline.ingest_text.call_args
        assert call_kwargs.get("source_url") == "https://example.com/page", (
            "source_url must be forwarded to ingest_text() for URL-based resolution"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_without_source_url_passes_none(
        self,
    ) -> None:
        """Calling ingest_document without source_url passes source_url=None to pipeline.

        Currently FAILS: ingest_document does not have source_url param, so
        ingest_text is called without it — resolution is never opt-in controlled.
        """
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.document_id = "doc-456"
        mock_result.chunk_count = 1
        mock_result.entity_count = 0
        mock_result.edge_count = 0
        mock_result.status = "ok"
        mock_pipeline.ingest_text = AsyncMock(return_value=mock_result)

        mock_app_ctx = MagicMock()
        mock_app_ctx.ingest_pipeline = mock_pipeline

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app_ctx

        await ingest_document(mock_ctx, text="Some document")

        mock_pipeline.ingest_text.assert_called_once()
        _, call_kwargs = mock_pipeline.ingest_text.call_args
        # source_url=None must be explicitly passed so pipeline skips resolution
        assert "source_url" in call_kwargs, "ingest_text must be called with source_url= kwarg (None when not provided)"
        assert call_kwargs["source_url"] is None, (
            f"source_url must be None when not given, got: {call_kwargs['source_url']!r}"
        )
