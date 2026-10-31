"""Durable tests for Qdrant persistence path wiring."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge import qdrant
from owlbear_knowledge.protocols.failures import KnowledgeFailureStage, KnowledgeOperationError
from owlbear_knowledge_mcp.server import _DEFAULT_QDRANT_PATH, MissingVectorStore, app_lifespan


class TestQdrantPersistencePathWiring:
    """Verify app_lifespan wires QdrantVectorStore to a filesystem path."""

    @pytest.fixture(autouse=True)
    def _qdrant_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(qdrant, "QdrantClient", object())

    @pytest.mark.asyncio
    async def test_qdrant_uses_default_path_when_env_var_is_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """QdrantVectorStore receives the default filesystem location."""
        (tmp_path / ".owlbear").mkdir()
        monkeypatch.chdir(tmp_path)

        qdrant_cls = MagicMock(name="QdrantVectorStore")
        server_mock = MagicMock()

        with patch("owlbear_knowledge_mcp.server.QdrantVectorStore", qdrant_cls):
            async with app_lifespan(server_mock):
                pass

        qdrant_cls.assert_called_once_with(location=str(tmp_path / _DEFAULT_QDRANT_PATH))
        assert (tmp_path / ".owlbear/knowledge/local.db").is_file()

    @pytest.mark.asyncio
    async def test_lifespan_closes_the_assembled_sqlite_connection(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The lifespan closes its real connection after the context exits."""
        (tmp_path / ".owlbear").mkdir()
        monkeypatch.chdir(tmp_path)

        connection: sqlite3.Connection | None = None
        with patch("owlbear_knowledge_mcp.server.QdrantVectorStore", MagicMock()):
            async with app_lifespan(MagicMock()) as context:
                connection = context.conn

        assert connection is not None
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_legacy_storage_env_vars_do_not_override_workspace_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Retired storage variables cannot redirect Knowledge state outside the workspace."""
        (tmp_path / ".owlbear").mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", ":memory:")
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path.parent / "external.db"))
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", str(tmp_path.parent / "vectors"))

        qdrant_cls = MagicMock(name="QdrantVectorStore")
        server_mock = MagicMock()

        with patch("owlbear_knowledge_mcp.server.QdrantVectorStore", qdrant_cls):
            async with app_lifespan(server_mock):
                pass

        qdrant_cls.assert_called_once_with(location=str(tmp_path / _DEFAULT_QDRANT_PATH))
        assert (tmp_path / ".owlbear/knowledge/local.db").is_file()


@pytest.mark.asyncio
async def test_lifespan_without_the_embedding_extras_fails_vector_calls_clearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Without qdrant-client the server starts and vector calls name the missing extras."""
    (tmp_path / ".owlbear").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(qdrant, "QdrantClient", None)

    async with app_lifespan(MagicMock()) as context:
        vector_store = context.content_store._vector_store  # noqa: SLF001

    assert isinstance(vector_store, MissingVectorStore)
    with pytest.raises(KnowledgeOperationError) as raised:
        vector_store.search_similar([0.0], top_k=1)
    assert raised.value.failure.stage is KnowledgeFailureStage.QUERY
    assert raised.value.failure.code == "embedding_dependency_missing"
    assert "owlbear-knowledge[embedding,qdrant]" in raised.value.failure.message
    with pytest.raises(KnowledgeOperationError) as raised:
        vector_store.store_embedding("chunk", [0.0], "document", scope="global")
    assert raised.value.failure.stage is KnowledgeFailureStage.INDEXING
