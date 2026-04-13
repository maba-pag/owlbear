"""Failing tests for task #860: sync_from_global and sync_to_global MCP tools.

AC coverage:
  AC-di   - _do_import gains source_scope kwarg; filters source rows when non-None (arch-review refinement)
  AC-reg  - sync_from_global and sync_to_global registered in server.__all__ and mcp instance
  AC-sigs - Both tools have exactly one parameter (ctx) — zero user-facing parameters
  AC-ann  - ToolAnnotations: readOnlyHint=False, destructiveHint=False for both tools
  AC-sf   - sync_from_global: error paths (unresolvable path, missing file) + happy-path return format
  AC-st   - sync_to_global: error path, DB auto-create, scope filter, return format, dedup
"""

from __future__ import annotations

import inspect
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge import init_db
from owlbear_knowledge.status_store import compute_content_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(path: str = ":memory:") -> sqlite3.Connection:
    """Return a SQLite connection with full knowledge schema."""
    conn = sqlite3.connect(path)
    init_db(conn)
    return conn


def _seed_document(
    conn: sqlite3.Connection,
    scope: str,
    title: str = "Doc",
    content: str = "hello",
) -> str:
    """Insert a minimal document + document_status row; returns the document id."""
    doc_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, title, content, "{}", "2024-01-01T00:00:00", scope),
    )
    content_hash = compute_content_hash(content)
    conn.execute(
        "INSERT INTO document_status "
        "(document_id, status, source, scope, created_at, updated_at, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "active", "test", scope, "2024-01-01", "2024-01-01", content_hash),
    )
    conn.commit()
    return doc_id


def _make_ctx(conn: sqlite3.Connection) -> MagicMock:
    """Return a mock FastMCP Context with app_ctx.conn pointing to *conn*."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = MagicMock(conn=conn)
    return ctx


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations for a named mcp-knowledge tool, or None."""
    from owlbear_mcp_knowledge.server import mcp  # noqa: PLC0415

    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ===========================================================================
# AC-di — _do_import source_scope kwarg (architecture-review refinement)
# ===========================================================================


class TestFromAC_DoImportSourceScope:
    """_do_import gains source_scope: str | None = None kwarg; filters source rows when set."""

    def test_source_scope_in_signature(self) -> None:
        """_do_import signature must include a source_scope parameter."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        sig = inspect.signature(_do_import)
        assert "source_scope" in sig.parameters, (
            "_do_import missing source_scope kwarg — add: source_scope: str | None = None"
        )

    def test_source_scope_default_is_none(self) -> None:
        """source_scope defaults to None (backward-compatible)."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        sig = inspect.signature(_do_import)
        param = sig.parameters.get("source_scope")
        assert param is not None, "_do_import missing source_scope parameter"
        assert param.default is None, (
            f"source_scope default must be None, got: {param.default!r}"
        )

    def test_source_scope_none_imports_all_docs(self) -> None:
        """source_scope=None (default) imports ALL documents regardless of their scope."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        src = _make_conn()
        _seed_document(src, "global", "GlobalDoc", "global content here")
        _seed_document(src, "project:foo", "ProjectDoc", "project content here")
        dest = _make_conn()

        _do_import(src, dest, target_scope="imported", source_scope=None)

        count = dest.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert count == 2, f"Expected 2 docs with source_scope=None, got {count}"

    def test_source_scope_filters_to_matching_scope_only(self) -> None:
        """source_scope='global' copies only documents with scope='global' from source."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        src = _make_conn()
        _seed_document(src, "global", "GlobalOnly", "global content abc")
        _seed_document(src, "project:foo", "ProjectOnly", "project content xyz")
        dest = _make_conn()

        _do_import(src, dest, target_scope="global", source_scope="global")

        count = dest.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert count == 1, (
            f"Expected 1 doc when source_scope='global', got {count} — check WHERE scope=? filter"
        )
        title = dest.execute("SELECT title FROM documents").fetchone()[0]
        assert title == "GlobalOnly"

    def test_source_scope_no_match_imports_zero(self) -> None:
        """source_scope with no matching documents results in 0 imported."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        src = _make_conn()
        _seed_document(src, "project:bar", "BarDoc", "bar content")
        dest = _make_conn()

        _do_import(src, dest, target_scope="global", source_scope="global")

        count = dest.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert count == 0, (
            f"Expected 0 docs when source_scope='global' but source has only 'project:bar', got {count}"
        )

    def test_source_scope_multi_scope_copies_only_matching(self) -> None:
        """With multiple scopes in source, only docs matching source_scope are copied."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        src = _make_conn()
        _seed_document(src, "global", "A", "content a unique")
        _seed_document(src, "global", "B", "content b unique")
        _seed_document(src, "project:x", "C", "content c unique")
        _seed_document(src, "local", "D", "content d unique")
        dest = _make_conn()

        _do_import(src, dest, target_scope="dest_scope", source_scope="global")

        titles = {r[0] for r in dest.execute("SELECT title FROM documents").fetchall()}
        assert titles == {"A", "B"}, (
            f"Expected only {{A, B}} (scope='global'), got: {titles!r}"
        )

    def test_source_scope_child_rows_excluded_for_filtered_docs(self) -> None:
        """Child rows (chunks, entities) for filtered-out docs are NOT copied."""
        from owlbear_knowledge.scope_transfer import _do_import  # noqa: PLC0415

        src = _make_conn()
        # Only project:foo doc — source_scope="global" should copy nothing
        doc_id = _seed_document(src, "project:foo", "FooDoc", "foo content unique")
        chunk_id = str(uuid.uuid4())
        src.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chunk_id, doc_id, 0, "chunk text", "{}", "2024-01-01", "project:foo"),
        )
        src.commit()
        dest = _make_conn()

        _do_import(src, dest, target_scope="global", source_scope="global")

        chunk_count = dest.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        assert chunk_count == 0, (
            f"Expected 0 chunks when source doc was filtered out, got {chunk_count}"
        )


# ===========================================================================
# AC-reg — Tool registration: both tools in __all__ and bound to mcp instance
# ===========================================================================


class TestFromAC_SyncToolRegistration:
    """sync_from_global and sync_to_global are registered in server.__all__ and mcp."""

    def test_sync_from_global_registered_on_server_module(self) -> None:
        """sync_from_global must exist as an attribute of owlbear_mcp_knowledge.server."""
        from owlbear_mcp_knowledge import server as srv  # noqa: PLC0415

        assert hasattr(srv, "sync_from_global"), (
            "sync_from_global missing from server.py — add @mcp.tool and define the async function"
        )

    def test_sync_to_global_registered_on_server_module(self) -> None:
        """sync_to_global must exist as an attribute of owlbear_mcp_knowledge.server."""
        from owlbear_mcp_knowledge import server as srv  # noqa: PLC0415

        assert hasattr(srv, "sync_to_global"), (
            "sync_to_global missing from server.py — add @mcp.tool and define the async function"
        )

    def test_sync_from_global_in_all(self) -> None:
        """sync_from_global must appear in server.__all__."""
        from owlbear_mcp_knowledge import server as srv  # noqa: PLC0415

        assert "sync_from_global" in srv.__all__, (
            "'sync_from_global' missing from server.__all__"
        )

    def test_sync_to_global_in_all(self) -> None:
        """sync_to_global must appear in server.__all__."""
        from owlbear_mcp_knowledge import server as srv  # noqa: PLC0415

        assert "sync_to_global" in srv.__all__, (
            "'sync_to_global' missing from server.__all__"
        )

    def test_sync_from_global_zero_user_facing_params(self) -> None:
        """sync_from_global has exactly one parameter (ctx) — zero user-facing parameters."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        sig = inspect.signature(sync_from_global)
        params = list(sig.parameters.keys())
        assert params == ["ctx"], (
            f"sync_from_global must have only 'ctx' parameter; got: {params!r}"
        )

    def test_sync_to_global_zero_user_facing_params(self) -> None:
        """sync_to_global has exactly one parameter (ctx) — zero user-facing parameters."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        sig = inspect.signature(sync_to_global)
        params = list(sig.parameters.keys())
        assert params == ["ctx"], (
            f"sync_to_global must have only 'ctx' parameter; got: {params!r}"
        )


# ===========================================================================
# AC-ann — ToolAnnotations: readOnlyHint=False, destructiveHint=False
# ===========================================================================


class TestFromAC_SyncToolAnnotations:
    """Both sync tools carry readOnlyHint=False, destructiveHint=False annotations."""

    def test_sync_from_global_not_read_only(self) -> None:
        """sync_from_global ToolAnnotations.readOnlyHint must be False."""
        ann = _get_tool_annotations("sync_from_global")
        assert ann is not None, (
            "sync_from_global not registered in mcp._tool_manager or has no ToolAnnotations"
        )
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"sync_from_global readOnlyHint must be False, got: {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    def test_sync_from_global_not_destructive(self) -> None:
        """sync_from_global ToolAnnotations.destructiveHint must be False."""
        ann = _get_tool_annotations("sync_from_global")
        assert ann is not None, "sync_from_global not in tool manager or missing annotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"sync_from_global destructiveHint must be False, got: {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )

    def test_sync_to_global_not_read_only(self) -> None:
        """sync_to_global ToolAnnotations.readOnlyHint must be False."""
        ann = _get_tool_annotations("sync_to_global")
        assert ann is not None, (
            "sync_to_global not registered in mcp._tool_manager or has no ToolAnnotations"
        )
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"sync_to_global readOnlyHint must be False, got: {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    def test_sync_to_global_not_destructive(self) -> None:
        """sync_to_global ToolAnnotations.destructiveHint must be False."""
        ann = _get_tool_annotations("sync_to_global")
        assert ann is not None, "sync_to_global not in tool manager or missing annotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"sync_to_global destructiveHint must be False, got: {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )


# ===========================================================================
# AC-sf — sync_from_global behavior
# ===========================================================================


class TestFromAC_SyncFromGlobal:
    """sync_from_global: error paths + happy-path return format + content-hash dedup."""

    @pytest.mark.asyncio
    async def test_returns_error_when_global_path_unresolvable(self) -> None:
        """Returns 'error: global DB path could not be resolved' when resolve returns error string."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with patch(
            "owlbear_mcp_knowledge.server.resolve_global_db_path",
            return_value="error: owlbear-project.json not found",
        ):
            result = await sync_from_global(ctx)

        assert result == "error: global DB path could not be resolved", (
            f"Expected path-unresolvable error string, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_returns_error_when_global_db_file_missing(
        self, tmp_path: Path
    ) -> None:
        """Returns 'error: global DB not found at {path}' when resolved path doesn't exist."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        missing = tmp_path / "global.db"
        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with patch(
            "owlbear_mcp_knowledge.server.resolve_global_db_path",
            return_value=missing,
        ):
            result = await sync_from_global(ctx)

        assert result.startswith("error: global DB not found at"), (
            f"Expected 'error: global DB not found at ...' for missing file, got: {result!r}"
        )
        assert str(missing) in result, (
            f"Error message must include the missing path; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_happy_path_returns_imported_count_string(
        self, tmp_path: Path
    ) -> None:
        """Happy path: returns 'Imported N documents (skipped M duplicates) from global ...' string."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        # Create global DB with two docs
        global_db_path = tmp_path / "global.db"
        global_conn = _make_conn(str(global_db_path))
        _seed_document(global_conn, "global", "GlobalDocA", "content alpha")
        _seed_document(global_conn, "global", "GlobalDocB", "content beta")
        global_conn.close()

        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_from_global(ctx)

        assert isinstance(result, str), f"Expected str result, got: {type(result)}"
        assert "Imported 2" in result, (
            f"Expected 'Imported 2 ...' in result, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_happy_path_return_string_format_matches_ac(
        self, tmp_path: Path
    ) -> None:
        """Return string must match AC format: '... from global into local under scope 'global''."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "global.db"
        global_conn = _make_conn(str(global_db_path))
        _seed_document(global_conn, "global", "Doc1", "content one unique")
        global_conn.close()

        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_from_global(ctx)

        assert "from global into local" in result, (
            f"Return string must contain 'from global into local'; got: {result!r}"
        )
        assert "scope 'global'" in result, (
            f"Return string must contain \"scope 'global'\"; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_content_hash_dedup_skips_already_present_docs(
        self, tmp_path: Path
    ) -> None:
        """Content-hash dedup: doc already in local under scope='global' is skipped."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        shared_content = "shared content identical"

        # Global DB: one doc
        global_db_path = tmp_path / "global.db"
        global_conn = _make_conn(str(global_db_path))
        _seed_document(global_conn, "global", "SharedDoc", shared_content)
        global_conn.close()

        # Local DB: same content already present under scope='global'
        local_conn = _make_conn()
        _seed_document(local_conn, "global", "ExistingCopy", shared_content)
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_from_global(ctx)

        assert "skipped 1" in result, (
            f"Expected 'skipped 1' for duplicate doc, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_imported_docs_land_in_local_under_scope_global(
        self, tmp_path: Path
    ) -> None:
        """Documents imported from global land in local DB under scope='global'."""
        from owlbear_mcp_knowledge.server import sync_from_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "global.db"
        global_conn = _make_conn(str(global_db_path))
        _seed_document(global_conn, "global", "Incoming", "incoming content here")
        global_conn.close()

        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            await sync_from_global(ctx)

        row = local_conn.execute(
            "SELECT scope FROM documents WHERE title=?", ("Incoming",)
        ).fetchone()
        assert row is not None, "Imported doc must appear in local DB"
        assert row[0] == "global", (
            f"Imported doc must have scope='global', got: {row[0]!r}"
        )


# ===========================================================================
# AC-st — sync_to_global behavior
# ===========================================================================


class TestFromAC_SyncToGlobal:
    """sync_to_global: error path, auto-create global DB, scope filter, return format, dedup."""

    @pytest.mark.asyncio
    async def test_returns_error_when_global_path_unresolvable(self) -> None:
        """Returns 'error: ...' when resolve_global_db_path returns an error string."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        local_conn = _make_conn()
        ctx = _make_ctx(local_conn)

        with patch(
            "owlbear_mcp_knowledge.server.resolve_global_db_path",
            return_value="error: malformed JSON",
        ):
            result = await sync_to_global(ctx)

        assert result.startswith("error:"), (
            f"Expected 'error: ...' when path unresolvable, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_creates_global_db_file_if_not_exists(
        self, tmp_path: Path
    ) -> None:
        """sync_to_global creates global DB file (with init_db schema) when it doesn't exist."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "new_dir" / "global.db"
        assert not global_db_path.exists()

        local_conn = _make_conn()
        _seed_document(local_conn, "global", "NewDoc", "new doc content")
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            await sync_to_global(ctx)

        assert global_db_path.exists(), (
            f"sync_to_global must create global DB at {global_db_path} if it doesn't exist"
        )

    @pytest.mark.asyncio
    async def test_only_exports_global_scope_docs_not_other_scopes(
        self, tmp_path: Path
    ) -> None:
        """Only documents with scope='global' in local are exported; other scopes are excluded."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "global.db"
        local_conn = _make_conn()
        _seed_document(local_conn, "global", "ShouldExport", "global export content")
        _seed_document(local_conn, "project:xyz", "ShouldSkip", "project skip content")
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            await sync_to_global(ctx)

        global_conn = sqlite3.connect(str(global_db_path))
        titles = {r[0] for r in global_conn.execute("SELECT title FROM documents").fetchall()}
        global_conn.close()
        assert "ShouldExport" in titles, "scope='global' doc must be exported"
        assert "ShouldSkip" not in titles, (
            "'project:xyz' scoped doc must NOT be exported by sync_to_global"
        )

    @pytest.mark.asyncio
    async def test_returns_exported_count_string(
        self, tmp_path: Path
    ) -> None:
        """Returns 'Exported N documents (skipped M duplicates) from local scope 'global' to global DB'."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "global.db"
        local_conn = _make_conn()
        _seed_document(local_conn, "global", "ExportMe", "export me content")
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_to_global(ctx)

        assert isinstance(result, str), f"Expected str result, got: {type(result)}"
        assert "Exported 1" in result, (
            f"Expected 'Exported 1 ...' in result, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_return_string_format_says_exported_not_imported(
        self, tmp_path: Path
    ) -> None:
        """Return string must say 'Exported' (not 'Imported') and reference 'global DB'."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        global_db_path = tmp_path / "global.db"
        local_conn = _make_conn()
        _seed_document(local_conn, "global", "ADoc", "a doc content unique xyz")
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_to_global(ctx)

        assert result.startswith("Exported"), (
            f"sync_to_global return string must start with 'Exported'; got: {result!r}"
        )
        assert "to global DB" in result, (
            f"sync_to_global return string must contain 'to global DB'; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_dedup_skips_docs_already_in_global(
        self, tmp_path: Path
    ) -> None:
        """Docs already in global DB (same content hash) are skipped — not duplicated."""
        from owlbear_mcp_knowledge.server import sync_to_global  # type: ignore[attr-defined]  # noqa: PLC0415

        shared_content = "shared content already in global"

        # Pre-populate global DB with the same content
        global_db_path = tmp_path / "global.db"
        existing_global_conn = _make_conn(str(global_db_path))
        _seed_document(existing_global_conn, "global", "AlreadyThere", shared_content)
        existing_global_conn.close()

        # Local DB also has same content under scope='global'
        local_conn = _make_conn()
        _seed_document(local_conn, "global", "Duplicate", shared_content)
        ctx = _make_ctx(local_conn)

        with (
            patch(
                "owlbear_mcp_knowledge.server.resolve_global_db_path",
                return_value=global_db_path,
            ),
            patch(
                "asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw)),
            ),
        ):
            result = await sync_to_global(ctx)

        assert "skipped 1" in result, (
            f"Expected 'skipped 1' for duplicate doc already in global, got: {result!r}"
        )
