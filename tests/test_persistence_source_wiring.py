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
