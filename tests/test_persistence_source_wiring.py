"""Durable tests for Qdrant persistence path and source identity wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.protocols.ingest import IngestRequest
from owlbear_knowledge.protocols.sources import SourceKind, SourceState
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
    """Verify source identity is resolved from v2 source-store wiring."""

    @pytest.mark.asyncio
    async def test_ingest_request_source_id_comes_from_existing_inline_source(self) -> None:
        """knowledge_ingest forwards resolved inline source id into IngestRequest."""
        existing_source = SimpleNamespace(id="resolved-src-1907", name="mcp-inline-global", kind=SourceKind.INLINE)
        source_store = MagicMock()
        source_store.list_sources.return_value = (existing_source,)

        ingest_result = SimpleNamespace(documents_processed=1, chunks_created=1, chunks_enqueued=1)
        coordinator = MagicMock()
        coordinator.ingest = AsyncMock(return_value=ingest_result)

        ctx = MagicMock()
        ctx.request_context.lifespan_context = SimpleNamespace(
            source_store_v2=source_store,
            ingest_coordinator=coordinator,
        )

        response = await knowledge_ingest(ctx, text="hello world", scope="global")

        assert response.startswith("Ingested:"), f"unexpected response: {response!r}"
        source_store.list_sources.assert_called_once_with(scope="global", state=SourceState.ACTIVE)
        coordinator.ingest.assert_called_once()

        request = coordinator.ingest.call_args.args[0]
        assert isinstance(request, IngestRequest), (
            f"knowledge_ingest must call coordinator.ingest with IngestRequest, got: {type(request)}"
        )
        assert request.source_id == "resolved-src-1907", (
            f"request.source_id must match resolved source id, got: {request.source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_request_source_id_comes_from_newly_registered_source(self) -> None:
        """knowledge_ingest uses register_source return id when no inline source exists."""
        registered_source = SimpleNamespace(id="registered-src-1907", name="mcp-inline-global", kind=SourceKind.INLINE)
        source_store = MagicMock()
        source_store.list_sources.return_value = ()
        source_store.register_source.return_value = registered_source

        ingest_result = SimpleNamespace(documents_processed=1, chunks_created=2, chunks_enqueued=2)
        coordinator = MagicMock()
        coordinator.ingest = AsyncMock(return_value=ingest_result)

        ctx = MagicMock()
        ctx.request_context.lifespan_context = SimpleNamespace(
            source_store_v2=source_store,
            ingest_coordinator=coordinator,
        )

        response = await knowledge_ingest(ctx, text="hello world", scope="global")

        assert response.startswith("Ingested:"), f"unexpected response: {response!r}"
        source_store.register_source.assert_called_once()
        coordinator.ingest.assert_called_once()

        request = coordinator.ingest.call_args.args[0]
        assert isinstance(request, IngestRequest), (
            f"knowledge_ingest must call coordinator.ingest with IngestRequest, got: {type(request)}"
        )
        assert request.source_id == "registered-src-1907", (
            f"request.source_id must match registered source id, got: {request.source_id!r}"
        )
