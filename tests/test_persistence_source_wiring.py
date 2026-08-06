"""Durable tests for Qdrant persistence path wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge_mcp.server import _DEFAULT_QDRANT_PATH, app_lifespan


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

        with patch("owlbear_knowledge_mcp.server.QdrantVectorStore", qdrant_cls):
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

        with patch("owlbear_knowledge_mcp.server.QdrantVectorStore", qdrant_cls):
            async with app_lifespan(server_mock):
                pass

        qdrant_cls.assert_called_once_with(location=custom_path)
