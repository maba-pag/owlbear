"""Durable tests for Qdrant persistence path and source identity wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.protocols.ingest import IngestRequest
from owlbear_knowledge.protocols.sources import (
    FetchTransport,
    InlineConfig,
    SourceKind,
    SourceRegistration,
    SourceState,
)
from owlbear_knowledge.stores.sources import SqliteSourceStore
from owlbear_mcp_knowledge.server import _DEFAULT_QDRANT_PATH, app_lifespan, knowledge_ingest


class TestQdrantPersistencePathWiring:
    """Verify app_lifespan wires QdrantVectorStore to a filesystem path."""

    @pytest.mark.asyncio
    async def test_qdrant_uses_default_path_when_env_var_is_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """QdrantVectorStore receives the default filesystem location."""
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", ":memory:")
        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)

        qdrant_cls = MagicMock(name="QdrantVectorStore")
        server_mock = MagicMock()

        with patch("owlbear_mcp_knowledge.server.QdrantVectorStore", qdrant_cls):
            async with app_lifespan(server_mock):
                pass

        qdrant_cls.assert_called_once_with(location=_DEFAULT_QDRANT_PATH)

    @pytest.mark.asyncio
    async def test_qdrant_uses_env_path_when_owlbear_qdrant_path_is_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """OWLBEAR_QDRANT_PATH overrides the default vector-store location."""
        custom_path = str(tmp_path / "vectors")
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", ":memory:")
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", custom_path)

        qdrant_cls = MagicMock(name="QdrantVectorStore")
        server_mock = MagicMock()

        with patch("owlbear_mcp_knowledge.server.QdrantVectorStore", qdrant_cls):
            async with app_lifespan(server_mock):
                pass

        qdrant_cls.assert_called_once_with(location=custom_path)


class TestKnowledgeIngestSourceIdentityWiring:
    """Verify source identity flows correctly through real v2 lifespan (app_lifespan + SqliteSourceStore)."""

    @pytest.mark.asyncio
    async def test_ingest_source_id_comes_from_existing_inline_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """knowledge_ingest uses existing source.id when mcp-inline-{scope} is already registered."""
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", ":memory:")
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", str(tmp_path / "vectors"))
        server_mock = MagicMock()

        with patch("owlbear_mcp_knowledge.server.QdrantVectorStore"):
            async with app_lifespan(server_mock) as app_ctx:
                assert isinstance(app_ctx.source_store_v2, SqliteSourceStore)

                pre_registered = app_ctx.source_store_v2.register_source(
                    SourceRegistration(
                        name="mcp-inline-global",
                        kind=SourceKind.INLINE,
                        fetch_method=FetchTransport.NONE,
                        config=InlineConfig(),
                        scope="global",
                        enrich=True,
                        refreshable=False,
                    )
                )

                fake_result = MagicMock()
                fake_result.documents_processed = 1
                fake_result.chunks_created = 1
                fake_result.chunks_enqueued = 1
                app_ctx.ingest_coordinator.ingest = AsyncMock(return_value=fake_result)

                mcp_ctx = MagicMock()
                mcp_ctx.request_context.lifespan_context = app_ctx

                response = await knowledge_ingest(mcp_ctx, text="hello world", scope="global")

        assert response.startswith("Ingested:"), f"unexpected response: {response!r}"
        app_ctx.ingest_coordinator.ingest.assert_called_once()
        request = app_ctx.ingest_coordinator.ingest.call_args.args[0]
        assert isinstance(request, IngestRequest), (
            f"knowledge_ingest must call coordinator.ingest with IngestRequest, got: {type(request)}"
        )
        assert request.source_id == pre_registered.id, (
            f"request.source_id must match existing source id, got: {request.source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_source_id_comes_from_newly_registered_inline_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """knowledge_ingest creates and uses a new source.id when mcp-inline-{scope} is absent."""
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", ":memory:")
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", str(tmp_path / "vectors"))
        server_mock = MagicMock()

        with patch("owlbear_mcp_knowledge.server.QdrantVectorStore"):
            async with app_lifespan(server_mock) as app_ctx:
                assert isinstance(app_ctx.source_store_v2, SqliteSourceStore)

                fake_result = MagicMock()
                fake_result.documents_processed = 1
                fake_result.chunks_created = 2
                fake_result.chunks_enqueued = 2
                app_ctx.ingest_coordinator.ingest = AsyncMock(return_value=fake_result)

                mcp_ctx = MagicMock()
                mcp_ctx.request_context.lifespan_context = app_ctx

                response = await knowledge_ingest(mcp_ctx, text="hello world", scope="global")

                sources = list(
                    app_ctx.source_store_v2.list_sources(scope="global", state=SourceState.ACTIVE)
                )
                inline = [s for s in sources if s.name == "mcp-inline-global"]

        assert response.startswith("Ingested:"), f"unexpected response: {response!r}"
        assert len(inline) == 1, (
            f"expected exactly one inline source after ingest, found {len(inline)}"
        )
        app_ctx.ingest_coordinator.ingest.assert_called_once()
        request = app_ctx.ingest_coordinator.ingest.call_args.args[0]
        assert isinstance(request, IngestRequest), (
            f"knowledge_ingest must call coordinator.ingest with IngestRequest, got: {type(request)}"
        )
        assert request.source_id == inline[0].id, (
            f"request.source_id must match newly registered source id, got: {request.source_id!r}"
        )
