"""Tests for task #524: Scaffold mcp-memory package.

Contract-level verification that the mcp-memory package scaffold is correct
per the AC acceptance criteria.

AC coverage:
  - AC1: Package structure — packages/mcp-memory/ with pyproject.toml, __init__.py,
         __main__.py, server.py, models.py
  - AC2: models.py — MemoryEntry Pydantic model with 11 fields, correct types/literals
  - AC3: server.py — AppContext dataclass, lifespan (a)-(h), mcp FastMCP, __all__
  - AC4: SQLite DDL — memory_entries table schema with correct columns/constraints
  - AC5: scripts/setup.py — owlbearMemory entry in create_mcp_config(), docstring updated
  - AC6: tests/test_package_boundary.py — ALLOWED_IMPORTS has owlbear_mcp_memory: set()
  - AC7: Root pyproject.toml — packages/mcp-memory/src in tool.ruff.src
"""

from __future__ import annotations

import ast
import json
import sqlite3
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_PACKAGE_DIR = _REPO_ROOT / "serve" / "mcp-memory"
_SRC_DIR = _PACKAGE_DIR / "src" / "owlbear_mcp_memory"

# setup/ is a namespace package; insert repo root so setup.init is importable
sys.path.insert(0, str(_REPO_ROOT))


# ===========================================================================
# AC1: Package structure — required files exist
# ===========================================================================


class TestFromAC_PackageStructure:
    """Package directory and all required files exist."""

    def test_package_directory_exists(self) -> None:
        assert _PACKAGE_DIR.is_dir(), f"packages/mcp-memory/ not found at {_PACKAGE_DIR}"

    def test_pyproject_toml_exists(self) -> None:
        assert (_PACKAGE_DIR / "pyproject.toml").is_file()

    def test_init_py_exists(self) -> None:
        assert (_SRC_DIR / "__init__.py").is_file()

    def test_main_py_exists(self) -> None:
        assert (_SRC_DIR / "__main__.py").is_file()

    def test_server_py_exists(self) -> None:
        assert (_SRC_DIR / "server.py").is_file()

    def test_models_py_exists(self) -> None:
        assert (_SRC_DIR / "models.py").is_file()


# ===========================================================================
# AC1: pyproject.toml content
# ===========================================================================


class TestFromAC_Pyproject:
    """pyproject.toml has correct name, dependencies, and hatch build config."""

    def _load(self) -> dict:
        path = _PACKAGE_DIR / "pyproject.toml"
        assert path.is_file(), "pyproject.toml missing — package not yet scaffolded"
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def test_project_name_is_owlbear_mcp_memory(self) -> None:
        data = self._load()
        assert data["project"]["name"] == "owlbear-mcp-memory"

    def test_mcp_cli_dep_present_with_minimum_version(self) -> None:
        data = self._load()
        deps = data["project"]["dependencies"]
        assert any("mcp[cli]" in dep and "1.26" in dep for dep in deps), (
            f"Expected 'mcp[cli]>=1.26' in dependencies, got: {deps}"
        )

    def test_hatch_wheel_packages_points_to_src_namespace(self) -> None:
        data = self._load()
        packages = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        assert "src/owlbear_mcp_memory" in packages


# ===========================================================================
# AC1: __main__.py follows the mcp-kanban pattern
# ===========================================================================


class TestFromAC_MainModule:
    """__main__.py imports mcp from server and calls mcp.run()."""

    def _source(self) -> str:
        path = _SRC_DIR / "__main__.py"
        assert path.is_file(), "__main__.py missing"
        return path.read_text(encoding="utf-8")

    def test_main_imports_mcp_from_server(self) -> None:
        tree = ast.parse(self._source())
        found = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "owlbear_mcp_memory.server"
            and any(alias.name == "mcp" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert found, "Expected 'from owlbear_mcp_memory.server import mcp' in __main__.py"

    def test_main_calls_mcp_run(self) -> None:
        assert "mcp.run()" in self._source(), "__main__.py must call mcp.run()"


# ===========================================================================
# AC2: MemoryEntry Pydantic model
# ===========================================================================


class TestFromAC_MemoryEntry:
    """MemoryEntry model: importable, BaseModel subclass, 11 correct fields."""

    def test_memory_entry_importable(self) -> None:
        from owlbear_mcp_memory.models import MemoryEntry

        assert MemoryEntry is not None

    def test_memory_entry_is_pydantic_base_model(self) -> None:
        from pydantic import BaseModel

        from owlbear_mcp_memory.models import MemoryEntry

        assert issubclass(MemoryEntry, BaseModel)

    def test_memory_entry_has_exactly_11_fields(self) -> None:
        from owlbear_mcp_memory.models import MemoryEntry

        expected = {
            "id",
            "content",
            "category",
            "confidence",
            "created_at",
            "updated_at",
            "source",
            "scope_agent",
            "scope_project",
            "approval_state",
            "deleted_at",
        }
        actual = set(MemoryEntry.model_fields)
        assert actual == expected, f"Field mismatch — extra: {actual - expected}, missing: {expected - actual}"

    def test_memory_entry_category_literal_values(self) -> None:
        import typing

        from owlbear_mcp_memory.models import MemoryEntry

        annotation = MemoryEntry.model_fields["category"].annotation
        args = set(typing.get_args(annotation))
        expected = {"preference", "knowledge", "context", "behavior", "goal"}
        assert args == expected, f"Expected category Literal{sorted(expected)}, got args={sorted(args)}"

    def test_memory_entry_approval_state_literal_values(self) -> None:
        import typing

        from owlbear_mcp_memory.models import MemoryEntry

        annotation = MemoryEntry.model_fields["approval_state"].annotation
        args = set(typing.get_args(annotation))
        expected = {"pending", "approved", "deleted"}
        assert args == expected, f"Expected approval_state Literal{sorted(expected)}, got args={sorted(args)}"

    def test_memory_entry_confidence_is_float(self) -> None:
        from owlbear_mcp_memory.models import MemoryEntry

        annotation = MemoryEntry.model_fields["confidence"].annotation
        assert annotation is float, f"Expected confidence: float, got {annotation}"

    def test_memory_entry_nullable_optional_fields(self) -> None:
        import typing

        from owlbear_mcp_memory.models import MemoryEntry

        for field_name in ("scope_agent", "scope_project", "deleted_at"):
            annotation = MemoryEntry.model_fields[field_name].annotation
            args = typing.get_args(annotation)
            assert type(None) in args, f"Expected {field_name} to be str | None, got {annotation}"

    def test_memory_entry_valid_instance_accepted(self) -> None:
        from owlbear_mcp_memory.models import MemoryEntry

        entry = MemoryEntry(
            id="550e8400-e29b-41d4-a716-446655440000",
            content="prefer pytest over unittest",
            category="preference",
            confidence=0.9,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
            source="user:test",
            approval_state="pending",
        )
        assert entry.scope_agent is None
        assert entry.scope_project is None
        assert entry.deleted_at is None

    def test_memory_entry_invalid_category_rejected(self) -> None:
        from pydantic import ValidationError

        from owlbear_mcp_memory.models import MemoryEntry

        with pytest.raises(ValidationError):
            MemoryEntry(
                id="550e8400-e29b-41d4-a716-446655440000",
                content="test",
                category="invalid_category",
                confidence=0.5,
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
                source="test",
                approval_state="pending",
            )

    def test_memory_entry_invalid_approval_state_rejected(self) -> None:
        from pydantic import ValidationError

        from owlbear_mcp_memory.models import MemoryEntry

        with pytest.raises(ValidationError):
            MemoryEntry(
                id="550e8400-e29b-41d4-a716-446655440000",
                content="test",
                category="preference",
                confidence=0.5,
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
                source="test",
                approval_state="unknown",
            )


# ===========================================================================
# AC3: AppContext dataclass
# ===========================================================================


class TestFromAC_AppContext:
    """AppContext is a dataclass with conn: sqlite3.Connection and project_name: str | None."""

    def test_app_context_importable(self) -> None:
        from owlbear_mcp_memory.server import AppContext

        assert AppContext is not None

    def test_app_context_is_dataclass(self) -> None:
        import dataclasses

        from owlbear_mcp_memory.server import AppContext

        assert dataclasses.is_dataclass(AppContext)

    def test_app_context_has_conn_field(self) -> None:
        import dataclasses

        from owlbear_mcp_memory.server import AppContext

        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "conn" in field_names

    def test_app_context_has_project_name_field(self) -> None:
        import dataclasses

        from owlbear_mcp_memory.server import AppContext

        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "project_name" in field_names

    def test_app_context_conn_type_is_sqlite_connection(self) -> None:
        import typing

        from owlbear_mcp_memory.server import AppContext

        hints = typing.get_type_hints(AppContext)
        assert hints.get("conn") is sqlite3.Connection, f"Expected conn: sqlite3.Connection, got {hints.get('conn')}"

    def test_app_context_project_name_allows_none(self) -> None:
        import typing

        from owlbear_mcp_memory.server import AppContext

        hints = typing.get_type_hints(AppContext)
        annotation = hints.get("project_name")
        args = typing.get_args(annotation)
        assert type(None) in args, f"Expected project_name: str | None, got {annotation}"


# ===========================================================================
# AC3: server.py — mcp FastMCP instance and __all__
# ===========================================================================


class TestFromAC_McpInstance:
    """mcp is a FastMCP instance named 'owlbear-memory'; __all__ exports public symbols."""

    def test_mcp_importable_from_server(self) -> None:
        from owlbear_mcp_memory.server import mcp

        assert mcp is not None

    def test_mcp_is_fastmcp_instance(self) -> None:
        from mcp.server.fastmcp import FastMCP

        from owlbear_mcp_memory.server import mcp

        assert isinstance(mcp, FastMCP)

    def test_mcp_name_is_owlbear_memory(self) -> None:
        from owlbear_mcp_memory.server import mcp

        assert mcp.name == "owlbear-memory", f"Expected mcp.name == 'owlbear-memory', got {mcp.name!r}"

    def test_server_all_defined(self) -> None:
        from owlbear_mcp_memory import server

        assert hasattr(server, "__all__"), "server.py must define __all__"
        assert isinstance(server.__all__, (list, tuple))

    def test_server_all_contains_app_context(self) -> None:
        from owlbear_mcp_memory import server

        assert "AppContext" in server.__all__

    def test_server_all_contains_mcp(self) -> None:
        from owlbear_mcp_memory import server

        assert "mcp" in server.__all__

    def test_server_all_contains_app_lifespan(self) -> None:
        from owlbear_mcp_memory import server

        assert "app_lifespan" in server.__all__

    def test_server_has_no_tool_implementations(self) -> None:
        """server.py scaffold must not define any @mcp.tool-decorated functions."""
        path = _SRC_DIR / "server.py"
        assert path.is_file(), "server.py missing"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tool_defs = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    dec_str = ast.unparse(decorator)
                    if "tool" in dec_str.lower() and "mcp" in dec_str.lower():
                        tool_defs.append(node.name)
        assert not tool_defs, f"server.py must not have tool implementations, found: {tool_defs}"

    def test_no_cross_package_imports_in_server(self) -> None:
        """server.py must use stdlib json for project identity — no owlbear_* imports."""
        path = _SRC_DIR / "server.py"
        assert path.is_file(), "server.py missing"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        disallowed_roots = {"owlbear_mcp_kanban", "owlbear_mcp_project", "owlbear_mcp_knowledge"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in disallowed_roots, (
                    f"server.py imports {root!r} — cross-package import forbidden. "
                    "Use stdlib json to read owlbear-project.json."
                )


# ===========================================================================
# AC3: Lifespan contract — all 8 steps
# ===========================================================================


class TestFromAC_Lifespan:
    """app_lifespan implements all 8 steps: env var, mkdir, connect, PRAGMAs,
    project.json, DDL, yield AppContext, close connection."""

    @pytest.mark.asyncio
    async def test_lifespan_uses_env_var_for_db_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (a): DB path read from OWLBEAR_MEMORY_DB_PATH env var."""
        db_path = tmp_path / "custom" / "test.db"
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(db_path))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.conn is not None

    @pytest.mark.asyncio
    async def test_lifespan_default_db_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (a): Default DB path is store/memory/memory.db relative to CWD."""
        monkeypatch.delenv("OWLBEAR_MEMORY_DB_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()):
            pass
        assert (tmp_path / "store" / "memory" / "memory.db").exists(), (
            "Default DB must be created at store/memory/memory.db relative to CWD"
        )

    @pytest.mark.asyncio
    async def test_lifespan_creates_parent_directories(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (b): Parent directories created if absent."""
        db_path = tmp_path / "nested" / "dirs" / "memory.db"
        assert not db_path.parent.exists()
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(db_path))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()):
            pass
        assert db_path.parent.exists(), "Parent directories must be created if absent"

    @pytest.mark.asyncio
    async def test_lifespan_sets_wal_journal_mode(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (d): PRAGMA journal_mode=WAL is set on the connection."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "wal.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            row = ctx.conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal", f"Expected journal_mode=wal, got {row[0]!r}"

    @pytest.mark.asyncio
    async def test_lifespan_sets_busy_timeout_5000(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (d): PRAGMA busy_timeout=5000 is set on the connection."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "bt.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            row = ctx.conn.execute("PRAGMA busy_timeout").fetchone()
        assert row[0] == 5000, f"Expected busy_timeout=5000, got {row[0]}"

    @pytest.mark.asyncio
    async def test_lifespan_reads_project_name_from_json(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (e): project_name read from owlbear-project.json in CWD via stdlib json."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "proj.db"))
        (tmp_path / "owlbear-project.json").write_text(json.dumps({"name": "my-test-project"}), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_name == "my-test-project"

    @pytest.mark.asyncio
    async def test_lifespan_project_name_none_when_json_absent(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (e): project_name is None when owlbear-project.json absent."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "noproj.db"))
        monkeypatch.chdir(tmp_path)
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_name is None

    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context_instance(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (g): lifespan yields an AppContext instance."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "yield.db"))
        from owlbear_mcp_memory.server import AppContext, app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            assert isinstance(ctx, AppContext)

    @pytest.mark.asyncio
    async def test_lifespan_closes_connection_on_normal_exit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (h): connection is closed in finally on normal exit."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "close.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            conn = ctx.conn
        # Closed connection raises ProgrammingError on use
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_lifespan_closes_connection_on_exception(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step (h): connection is closed in finally even when exception raised in body."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "exc.db"))
        from owlbear_mcp_memory.server import app_lifespan

        conn_ref: list[sqlite3.Connection] = []

        async def _body_with_error() -> None:
            async with app_lifespan(MagicMock()) as ctx:
                conn_ref.append(ctx.conn)
                msg = "simulated body error"
                raise RuntimeError(msg)

        with pytest.raises(RuntimeError):
            await _body_with_error()
        with pytest.raises(sqlite3.ProgrammingError):
            conn_ref[0].execute("SELECT 1")


# ===========================================================================
# AC4: SQLite DDL — memory_entries table schema
# ===========================================================================


class TestFromAC_SqliteDdl:
    """memory_entries table created with correct columns, types, and constraints."""

    @pytest.mark.asyncio
    async def test_memory_entries_table_created(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "ddl.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            row = ctx.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_entries'"
            ).fetchone()
        assert row is not None, "memory_entries table was not created"

    @pytest.mark.asyncio
    async def test_memory_entries_columns_and_types(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "ddl2.db"))
        expected = {
            "id": "TEXT",
            "content": "TEXT",
            "category": "TEXT",
            "confidence": "REAL",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "source": "TEXT",
            "scope_agent": "TEXT",
            "scope_project": "TEXT",
            "approval_state": "TEXT",
            "deleted_at": "TEXT",
        }
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            pragma = ctx.conn.execute("PRAGMA table_info(memory_entries)").fetchall()
        # pragma rows: (cid, name, type, notnull, dflt_value, pk)
        col_map = {row[1]: row[2] for row in pragma}
        assert set(col_map) == set(expected), (
            f"Column mismatch — extra: {set(col_map) - set(expected)}, missing: {set(expected) - set(col_map)}"
        )
        for col, col_type in expected.items():
            assert col_map[col] == col_type, f"Column {col!r}: expected type {col_type!r}, got {col_map[col]!r}"

    @pytest.mark.asyncio
    async def test_id_is_primary_key(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "pk.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            pragma = ctx.conn.execute("PRAGMA table_info(memory_entries)").fetchall()
        pk_cols = [row[1] for row in pragma if row[5] == 1]
        assert pk_cols == ["id"], f"Expected 'id' as PRIMARY KEY, got {pk_cols}"

    @pytest.mark.asyncio
    async def test_approval_state_default_is_pending(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "default.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            pragma = ctx.conn.execute("PRAGMA table_info(memory_entries)").fetchall()
        defaults = {row[1]: row[4] for row in pragma}
        raw = defaults.get("approval_state", "")
        # SQLite returns default with quotes: "'pending'"
        assert raw in ("'pending'", "pending"), f"Expected approval_state DEFAULT 'pending', got {raw!r}"

    @pytest.mark.asyncio
    async def test_nullable_columns_allow_null(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "null.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()) as ctx:
            pragma = ctx.conn.execute("PRAGMA table_info(memory_entries)").fetchall()
        # notnull=0 means nullable
        notnull = {row[1]: row[3] for row in pragma}
        for col in ("scope_agent", "scope_project", "deleted_at"):
            assert notnull.get(col) == 0, f"Expected {col!r} to be nullable (notnull=0), got {notnull.get(col)}"

    @pytest.mark.asyncio
    async def test_required_columns_are_not_null(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "notnull.db"))
        from owlbear_mcp_memory.server import app_lifespan

        required = {"content", "category", "confidence", "created_at", "updated_at", "source"}
        async with app_lifespan(MagicMock()) as ctx:
            pragma = ctx.conn.execute("PRAGMA table_info(memory_entries)").fetchall()
        notnull = {row[1]: row[3] for row in pragma}
        for col in required:
            assert notnull.get(col) == 1, f"Expected {col!r} NOT NULL (notnull=1), got {notnull.get(col)}"

    @pytest.mark.asyncio
    async def test_create_table_is_idempotent(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CREATE TABLE IF NOT EXISTS: running lifespan twice on same DB must not error."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "idem.db"))
        from owlbear_mcp_memory.server import app_lifespan

        async with app_lifespan(MagicMock()):
            pass
        # Second invocation must not raise
        async with app_lifespan(MagicMock()) as ctx:
            row = ctx.conn.execute("SELECT name FROM sqlite_master WHERE name='memory_entries'").fetchone()
        assert row is not None


# ===========================================================================
# AC5: scripts/setup.py — owlbearMemory entry
# ===========================================================================


class TestFromAC_SetupMcp:
    """create_mcp_config() includes owlbearMemory; docstring updated to mention five servers."""

    def _setup_source(self) -> str:
        return (_REPO_ROOT / "setup" / "init.py").read_text(encoding="utf-8")

    def test_setup_source_contains_owlbear_memory_key(self) -> None:
        assert "owlbear-memory" in self._setup_source(), (
            "setup/init.py must include 'owlbear-memory' server key in create_mcp_config() (kebab-case)"
        )

    def test_setup_source_contains_owlbear_mcp_memory_module(self) -> None:
        assert "owlbear_mcp_memory" in self._setup_source(), (
            "setup/init.py must reference -m owlbear_mcp_memory for the memory server"
        )

    def test_create_mcp_config_produces_five_servers(self, tmp_path: Path) -> None:
        """create_mcp_config() writes a config with 5 server entries."""
        from setup.init import create_mcp_config  # type: ignore[import]

        owlbear_dir = _REPO_ROOT
        create_mcp_config(tmp_path, owlbear_dir)
        mcp_json = tmp_path / ".vscode" / "mcp.json"
        assert mcp_json.is_file(), "mcp.json was not created"
        config = json.loads(mcp_json.read_text(encoding="utf-8"))
        servers = config["servers"]
        assert len(servers) == 5, f"Expected 5 server entries (github + 4 stdio), got {len(servers)}: {list(servers)}"

    def test_create_mcp_config_owlbear_memory_entry_shape(self, tmp_path: Path) -> None:
        """owlbear-memory entry has type=stdio, command=uv, -m owlbear_mcp_memory in args."""
        from setup.init import create_mcp_config  # type: ignore[import]

        create_mcp_config(tmp_path, _REPO_ROOT)
        config = json.loads((tmp_path / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
        assert "owlbear-memory" in config["servers"], (
            f"'owlbear-memory' key missing from servers: {list(config['servers'])}"
        )
        entry = config["servers"]["owlbear-memory"]
        assert entry.get("type") == "stdio"
        assert entry.get("command") == "uv"
        assert "-m" in entry.get("args", [])
        assert "owlbear_mcp_memory" in entry.get("args", [])

    def test_create_mcp_config_docstring_mentions_five_servers(self) -> None:
        """create_mcp_config() docstring must mention five MCP server entries."""
        tree = ast.parse(self._setup_source())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "create_mcp_config":
                docstring = ast.get_docstring(node) or ""
                assert "five" in docstring.lower(), (
                    f"create_mcp_config docstring must say 'five' (was updated from four), got: {docstring!r}"
                )
                return
        pytest.fail("create_mcp_config function not found in setup/init.py")

    def test_create_mcp_config_docstring_mentions_four_stdio_servers(self) -> None:
        """create_mcp_config() docstring must mention four owlbear stdio servers (updated from three)."""
        tree = ast.parse(self._setup_source())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "create_mcp_config":
                docstring = ast.get_docstring(node) or ""
                # Post-update: "four owlbear stdio servers" (not "three owlbear stdio")
                assert "four owlbear stdio" in docstring.lower(), (
                    f"create_mcp_config docstring must say 'four owlbear stdio servers' "
                    f"(updated from 'three'), got: {docstring!r}"
                )
                return
        pytest.fail("create_mcp_config function not found in setup/init.py")


# ===========================================================================
# AC6: test_package_boundary.py — ALLOWED_IMPORTS updated
# ===========================================================================


class TestFromAC_PackageBoundary:
    """ALLOWED_IMPORTS in test_package_boundary.py includes owlbear_mcp_memory: set()."""

    def _boundary_source(self) -> str:
        return (_REPO_ROOT / "tests" / "test_package_boundary.py").read_text(encoding="utf-8")

    def test_boundary_source_has_mcp_memory_key(self) -> None:
        """ALLOWED_IMPORTS literal in test_package_boundary.py must include 'owlbear_mcp_memory'."""
        assert "owlbear_mcp_memory" in self._boundary_source(), (
            "test_package_boundary.py ALLOWED_IMPORTS must include 'owlbear_mcp_memory: set()'"
        )

    def test_boundary_mcp_memory_maps_to_empty_set(self) -> None:
        """owlbear_mcp_memory entry must map to set() — no allowed cross-namespace imports."""
        source = self._boundary_source()
        # Find the ALLOWED_IMPORTS assignment and verify owlbear_mcp_memory: set()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "ALLOWED_IMPORTS"
            ):
                # Unparse and check for the entry
                unparsed = ast.unparse(node.value)
                assert "owlbear_mcp_memory" in unparsed, "owlbear_mcp_memory not found in ALLOWED_IMPORTS dict"
                return
        pytest.fail("ALLOWED_IMPORTS assignment not found in test_package_boundary.py")


# ===========================================================================
# AC7: Root pyproject.toml — ruff src array updated
# ===========================================================================


class TestFromAC_RuffSrcArray:
    """Root pyproject.toml has serve/mcp-memory/src in tool.ruff.src."""

    def test_ruff_src_includes_mcp_memory(self) -> None:
        data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        ruff_src = data["tool"]["ruff"]["src"]
        assert "serve/mcp-memory/src" in ruff_src, f"'serve/mcp-memory/src' missing from tool.ruff.src, got: {ruff_src}"
