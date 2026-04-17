"""Failing tests for task #858: rename KB paths (local.db/global.db) + resolve_global_db_path.

Covers (TDD RED phase — all tests must FAIL before builder implements #858):
  - AC1: _DEFAULT_KB_PATH in server.py points to .owlbear/knowledge/local.db
  - AC2: _AUTO_DETECT_RELATIVE updated to local.db; import_scope(None) returns explicit error
  - AC4: new resolve_global_db_path(cwd) function with env var override + error handling
  - AC7: server.py reads OWLBEAR_LOCAL_KB_PATH (primary) with OWLBEAR_KB_PATH fallback
  - AC_loader: loader.py default path + env var updated matching AC7 chain
  - benchmark: run_benchmark connects to local.db not hardcoded knowledge.db

AC coverage:
  AC1  - _DEFAULT_KB_PATH in server.py → .owlbear/knowledge/local.db
  AC2  - _AUTO_DETECT_RELATIVE → local.db; import_scope(None) no longer auto-detects
  AC4  - resolve_global_db_path(cwd) function: env override, JSON read, error cases
  AC7  - OWLBEAR_LOCAL_KB_PATH primary env var in server.py + loader.py
  MISC - benchmark.py hardcoded knowledge.db reference → local.db
"""

from __future__ import annotations

import inspect
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dest_conn() -> sqlite3.Connection:
    """Return an in-memory destination SQLite connection with full knowledge schema."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


# ===========================================================================
# AC1 — _DEFAULT_KB_PATH renamed in server.py
# ===========================================================================


class TestFromAC_DefaultKBPath:
    """_DEFAULT_KB_PATH constant in server.py points to .owlbear/knowledge/local.db."""

    def test_server_default_kb_path_is_local_db(self) -> None:
        """_DEFAULT_KB_PATH must equal '.owlbear/knowledge/local.db'."""
        from owlbear_mcp_knowledge.server import _DEFAULT_KB_PATH  # noqa: PLC0415

        assert _DEFAULT_KB_PATH == ".owlbear/knowledge/local.db"

    def test_server_default_kb_path_not_old_store_path(self) -> None:
        """_DEFAULT_KB_PATH must not reference old store/knowledge path."""
        from owlbear_mcp_knowledge.server import _DEFAULT_KB_PATH  # noqa: PLC0415

        assert "store/knowledge" not in _DEFAULT_KB_PATH


# ===========================================================================
# AC2 — _AUTO_DETECT_RELATIVE updated + auto-detect removed from import_scope
# ===========================================================================


class TestFromAC_AutoDetectBehavior:
    """scope_transfer._AUTO_DETECT_RELATIVE uses local.db; import_scope(None) returns explicit error."""

    def test_auto_detect_relative_ends_with_local_db(self) -> None:
        """_AUTO_DETECT_RELATIVE must end with 'local.db'."""
        from owlbear_knowledge.scope_transfer import _AUTO_DETECT_RELATIVE  # noqa: PLC0415

        assert str(_AUTO_DETECT_RELATIVE).endswith("local.db")

    def test_auto_detect_relative_not_knowledge_db(self) -> None:
        """_AUTO_DETECT_RELATIVE must not reference the old knowledge.db filename."""
        from owlbear_knowledge.scope_transfer import _AUTO_DETECT_RELATIVE  # noqa: PLC0415

        assert "knowledge.db" not in str(_AUTO_DETECT_RELATIVE)

    def test_import_scope_none_no_env_no_root_returns_explicit_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """import_scope(None) with no env var and no workspace_root returns explicit error."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_LOCAL_KB_PATH", raising=False)
        dest = _make_dest_conn()
        result = import_scope(None, "testproject", dest)
        assert result.startswith("error:")
        assert "explicit source path required" in result

    def test_import_scope_none_no_env_with_root_returns_explicit_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """import_scope(None) + workspace_root but no env var returns explicit error (no auto-detect)."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_LOCAL_KB_PATH", raising=False)
        dest = _make_dest_conn()
        # workspace_root is provided but should NOT trigger auto-detect after AC2 change
        result = import_scope(None, "testproject", dest, workspace_root=tmp_path)
        assert result.startswith("error:")
        assert "explicit source path required" in result


# ===========================================================================
# AC4 — resolve_global_db_path function
# ===========================================================================


class TestFromAC_ResolveGlobalDbPath:
    """resolve_global_db_path(cwd) resolves global DB path from owlbear-project.json."""

    def test_function_is_importable(self) -> None:
        """resolve_global_db_path is importable from owlbear_knowledge.scope_transfer."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        assert callable(resolve_global_db_path)

    def test_resolve_happy_path_returns_path_object(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_global_db_path returns a Path when owlbear-project.json is valid."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        owlbear_dir = tmp_path / "owlbear-install"
        owlbear_dir.mkdir()
        (tmp_path / "owlbear-project.json").write_text(
            json.dumps({"name": "myproject", "owlbear_path": str(owlbear_dir)}),
            encoding="utf-8",
        )
        result = resolve_global_db_path(tmp_path)
        assert isinstance(result, Path)

    def test_resolve_happy_path_points_to_global_db(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_global_db_path result path must end with store/knowledge/global.db."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        owlbear_dir = tmp_path / "owlbear-install"
        owlbear_dir.mkdir()
        (tmp_path / "owlbear-project.json").write_text(
            json.dumps({"name": "myproject", "owlbear_path": str(owlbear_dir)}),
            encoding="utf-8",
        )
        result = resolve_global_db_path(tmp_path)
        # Accept both POSIX and Windows path separators
        path_str = str(result)
        assert path_str.endswith(("store/knowledge/global.db", "store\\knowledge\\global.db"))

    def test_resolve_env_var_override_returns_env_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_GLOBAL_KB_PATH env var overrides JSON resolution."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        expected = str(tmp_path / "custom" / "global.db")
        monkeypatch.setenv("OWLBEAR_GLOBAL_KB_PATH", expected)
        result = resolve_global_db_path(tmp_path)
        assert str(result) == expected

    def test_resolve_env_var_overrides_even_without_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_GLOBAL_KB_PATH is honoured even when owlbear-project.json is absent."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        custom_path = str(tmp_path / "override.db")
        monkeypatch.setenv("OWLBEAR_GLOBAL_KB_PATH", custom_path)
        # No owlbear-project.json in tmp_path — should not matter when env var is set
        result = resolve_global_db_path(tmp_path)
        assert str(result) == custom_path
        assert not str(result).startswith("error:")

    def test_resolve_missing_json_returns_error_prefix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_global_db_path returns error: string when owlbear-project.json is missing."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        result = resolve_global_db_path(tmp_path)
        assert isinstance(result, str)
        assert result.startswith("error:")

    def test_resolve_malformed_json_returns_error_prefix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_global_db_path returns error: string when owlbear-project.json is malformed."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        (tmp_path / "owlbear-project.json").write_text("not valid json }{", encoding="utf-8")
        result = resolve_global_db_path(tmp_path)
        assert isinstance(result, str)
        assert result.startswith("error:")

    def test_resolve_missing_owlbear_path_field_returns_error_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_global_db_path returns error: string when owlbear_path key is absent."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        (tmp_path / "owlbear-project.json").write_text(
            json.dumps({"name": "myproject"}),  # no owlbear_path key
            encoding="utf-8",
        )
        result = resolve_global_db_path(tmp_path)
        assert isinstance(result, str)
        assert result.startswith("error:")

    def test_resolve_nonexistent_owlbear_dir_returns_error_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_global_db_path returns error: string when the owlbear_path dir does not exist."""
        from owlbear_knowledge.scope_transfer import resolve_global_db_path  # noqa: PLC0415

        monkeypatch.delenv("OWLBEAR_GLOBAL_KB_PATH", raising=False)
        (tmp_path / "owlbear-project.json").write_text(
            json.dumps({"name": "myproject", "owlbear_path": str(tmp_path / "does_not_exist")}),
            encoding="utf-8",
        )
        result = resolve_global_db_path(tmp_path)
        assert isinstance(result, str)
        assert result.startswith("error:")


# ===========================================================================
# AC7 — env var rename in server.py (OWLBEAR_LOCAL_KB_PATH primary, OWLBEAR_KB_PATH fallback)
# ===========================================================================


class TestFromAC_EnvVarRenameServer:
    """server.py reads OWLBEAR_LOCAL_KB_PATH with fallback to OWLBEAR_KB_PATH."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_server_lifespan_reads_owlbear_local_kb_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """app_lifespan must open the DB at OWLBEAR_LOCAL_KB_PATH when set."""
        from owlbear_mcp_knowledge.server import app_lifespan  # noqa: PLC0415

        mock_conn = MagicMock()
        custom_path = "/custom/local/mydb.db"
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", custom_path)
        monkeypatch.delenv("OWLBEAR_KB_PATH", raising=False)
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "test-key")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        args, _ = mock_init.call_args
        assert custom_path in args

    @pytest.mark.asyncio(loop_scope="function")
    async def test_server_lifespan_local_kb_takes_priority_over_kb_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_LOCAL_KB_PATH takes priority over OWLBEAR_KB_PATH when both are set."""
        from owlbear_mcp_knowledge.server import app_lifespan  # noqa: PLC0415

        mock_conn = MagicMock()
        local_path = "/custom/local.db"
        old_path = "/old/kb_path.db"
        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", local_path)
        monkeypatch.setenv("OWLBEAR_KB_PATH", old_path)
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "test-key")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        args, _ = mock_init.call_args
        assert local_path in args
        assert old_path not in args

    @pytest.mark.asyncio(loop_scope="function")
    async def test_server_lifespan_no_env_uses_local_db_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """app_lifespan without env vars uses '.owlbear/knowledge/local.db' as default."""
        from owlbear_mcp_knowledge.server import app_lifespan  # noqa: PLC0415

        mock_conn = MagicMock()
        monkeypatch.delenv("OWLBEAR_LOCAL_KB_PATH", raising=False)
        monkeypatch.delenv("OWLBEAR_KB_PATH", raising=False)
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "test-key")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        args, _ = mock_init.call_args
        assert "local.db" in args[0]


# ===========================================================================
# AC7 — env var rename in loader.py
# ===========================================================================


class TestFromAC_LoaderEnvVarChain:
    """loader.main() reads OWLBEAR_LOCAL_KB_PATH (primary) with .owlbear/knowledge/local.db default."""

    def test_loader_main_source_references_owlbear_local_kb_path(self) -> None:
        """loader.main() source must reference OWLBEAR_LOCAL_KB_PATH env var."""
        from owlbear_knowledge import loader as loader_mod  # noqa: PLC0415

        src = inspect.getsource(loader_mod.main)
        assert "OWLBEAR_LOCAL_KB_PATH" in src

    def test_loader_main_default_path_is_local_db(self) -> None:
        """loader.main() must not use store/knowledge/knowledge.db; must use .owlbear/knowledge/local.db."""
        from owlbear_knowledge import loader as loader_mod  # noqa: PLC0415

        src = inspect.getsource(loader_mod.main)
        assert "store/knowledge/knowledge.db" not in src
        assert ".owlbear/knowledge/local.db" in src


# ===========================================================================
# benchmark.py — run_benchmark connects to local.db not hardcoded knowledge.db
# ===========================================================================


class TestFromAC_BenchmarkLocalDb:
    """benchmark.run_benchmark() must connect to local.db, not hardcoded knowledge.db."""

    def test_benchmark_uses_local_db_not_knowledge_db(self) -> None:
        """run_benchmark source must not reference the old hardcoded 'knowledge.db' filename."""
        from owlbear_knowledge import benchmark as bench_mod  # noqa: PLC0415

        src = inspect.getsource(bench_mod.run_benchmark)
        assert '"knowledge.db"' not in src
        assert "local.db" in src
