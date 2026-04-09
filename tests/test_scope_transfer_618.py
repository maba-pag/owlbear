"""Failing tests for task #618: import/export scope transfer for project-local knowledge.

Tests the contract for:
- owlbear_knowledge.scope_transfer: import_scope / export_scope core functions
- MCP tool wiring in mcp-knowledge server.py (import_scope / export_scope tools)
- Path sandboxing (AC4), auto-detect (AC5), schema validation (AC6)
- Content-hash dedup (AC2), ToolAnnotations, error: prefix convention

All tests FAIL in RED phase:
  - Core module tests: ImportError (scope_transfer.py not yet created)
  - MCP tool tests: AttributeError (import_scope/export_scope not in server.py)

AC coverage:
  AC1 - import_scope copies documents/document_status/chunks/entities/edges under
        scope="project:{name}", new UUIDs, FK remapping, atomic transaction
  AC2 - Duplicate documents (same content hash) skipped on import
  AC3 - export_scope creates valid SQLite file (init_db schema) with scoped rows only
  AC4 - Import path sandboxed via sandbox_path; traversal rejected with error: message
  AC5 - Auto-detect .owlbear/knowledge/knowledge.db when path=None; error: when missing
  AC6 - Source validated: must be valid SQLite with schema_version table
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge import init_db
from owlbear_knowledge.status_store import compute_content_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def _make_dest_conn() -> sqlite3.Connection:
    """Return an in-memory destination SQLite connection with full knowledge schema."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _seed_source(
    conn: sqlite3.Connection,
    *,
    doc_id: str = "doc-src-1",
    scope: str = "global",
    content: str | None = None,
) -> dict[str, str]:
    """Insert one complete document/status/chunk/entity/edge row-set into *conn*.

    Returns a dict with the original IDs used in the source DB.
    """
    content = content or f"source content for {doc_id}"
    c_hash = compute_content_hash(content)
    chunk_id = f"chunk-{doc_id}"
    entity_id = f"entity-{doc_id}"
    edge_id = f"edge-{doc_id}"

    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, "Test Doc", content, "{}", _TIMESTAMP, scope),
    )
    conn.execute(
        "INSERT INTO document_status "
        "(document_id, status, source, scope, created_at, updated_at, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "ingested", "file://test.md", scope, _TIMESTAMP, _TIMESTAMP, c_hash),
    )
    conn.execute(
        "INSERT INTO chunks "
        "(id, document_id, chunk_index, content, metadata, created_at, scope) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (chunk_id, doc_id, 0, content, "{}", _TIMESTAMP, scope),
    )
    conn.execute(
        "INSERT INTO entities "
        "(id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (entity_id, "TestEntity", "concept", "desc", "{}", _TIMESTAMP, scope, doc_id, chunk_id),
    )
    conn.execute(
        "INSERT INTO edges "
        "(id, source_id, target_id, relation, weight, metadata, created_at, scope) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (edge_id, entity_id, entity_id, "related_to", 1.0, "{}", _TIMESTAMP, scope),
    )
    conn.commit()
    return {
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "entity_id": entity_id,
        "edge_id": edge_id,
        "content": content,
        "content_hash": c_hash,
    }


def _make_source_file(base: Path, *, populate: bool = True, doc_id: str = "doc-src-1") -> Path:
    """Create a populated SQLite source file in *base*. Returns the path."""
    db = base / "source.db"
    conn = sqlite3.connect(str(db))
    init_db(conn)
    if populate:
        _seed_source(conn, doc_id=doc_id)
    conn.close()
    return db


def _count_rows(conn: sqlite3.Connection, table: str, scope: str | None = None) -> int:
    """Count rows in *table*, optionally filtered by scope."""
    if scope:
        return conn.execute(
            f"SELECT count(*) FROM {table} WHERE scope = ?",  # noqa: S608
            (scope,),
        ).fetchone()[0]
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608


def _get_tool_annotations_from_server(tool_name: str) -> Any:
    """Retrieve ToolAnnotations for a named MCP tool from the server module."""
    from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

    mcp_instance = server_mod.mcp
    if hasattr(mcp_instance, "_tool_manager"):
        for t in mcp_instance._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ===========================================================================
# AC: scope_transfer module is importable
# ===========================================================================


class TestFromAC_ScopeTransferModule:  # noqa: N801
    """scope_transfer.py exists and exports import_scope / export_scope functions."""

    def test_import_scope_function_importable(self) -> None:
        """import_scope is importable from owlbear_knowledge.scope_transfer."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        assert callable(import_scope)

    def test_export_scope_function_importable(self) -> None:
        """export_scope is importable from owlbear_knowledge.scope_transfer."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        assert callable(export_scope)


# ===========================================================================
# AC1 -- import_scope copies all 5 tables into dest DB under project scope
# ===========================================================================


class TestFromAC_ImportScopeHappyPath:  # noqa: N801
    """import_scope copies documents/document_status/chunks/entities/edges with new project scope."""

    def test_documents_appear_in_dest_after_import(self, tmp_path: Path) -> None:
        """After import_scope, dest DB contains documents under scope project:myproject."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "myproject", dest)
        count = _count_rows(dest, "documents", scope="project:myproject")
        assert count >= 1

    def test_document_status_appears_in_dest_after_import(self, tmp_path: Path) -> None:
        """document_status rows are copied to dest DB under project scope."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "acme", dest)
        count = _count_rows(dest, "document_status", scope="project:acme")
        assert count >= 1

    def test_chunks_appear_in_dest_after_import(self, tmp_path: Path) -> None:
        """Chunk rows are copied into dest DB under project scope."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        count = _count_rows(dest, "chunks", scope="project:proj")
        assert count >= 1

    def test_entities_appear_in_dest_after_import(self, tmp_path: Path) -> None:
        """Entity rows are copied into dest DB under project scope."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        count = _count_rows(dest, "entities", scope="project:proj")
        assert count >= 1

    def test_edges_appear_in_dest_after_import(self, tmp_path: Path) -> None:
        """Edge rows are copied into dest DB under project scope."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        count = _count_rows(dest, "edges", scope="project:proj")
        assert count >= 1

    def test_imported_scope_format_is_project_colon_name(self, tmp_path: Path) -> None:
        """All imported rows carry scope=project:{project_name} -- not the source scope."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "owlbear", dest)
        docs = dest.execute("SELECT scope FROM documents WHERE scope = 'project:owlbear'").fetchall()
        assert len(docs) >= 1
        assert all(row[0] == "project:owlbear" for row in docs)

    def test_new_uuids_generated_not_original_source_ids(self, tmp_path: Path) -> None:
        """Imported document IDs are new UUIDs -- original IDs must not be reused verbatim."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        original_ids = {"doc-src-1", "chunk-doc-src-1", "entity-doc-src-1", "edge-doc-src-1"}
        src = _make_source_file(tmp_path, doc_id="doc-src-1")
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        dest_doc_ids = {row[0] for row in dest.execute("SELECT id FROM documents").fetchall()}
        assert not dest_doc_ids & original_ids, "Original source IDs must not be reused in dest -- new UUIDs required"

    def test_import_returns_string_result(self, tmp_path: Path) -> None:
        """import_scope returns a string (success message or summary)."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        result = import_scope(src, "proj", dest)
        assert isinstance(result, str)

    def test_import_result_does_not_start_with_error_prefix(self, tmp_path: Path) -> None:
        """Successful import result must NOT start with error: ."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        result = import_scope(src, "proj", dest)
        assert not result.startswith("error: "), f"Unexpected error on valid import: {result!r}"

    def test_empty_source_imports_zero_rows_and_returns_string(self, tmp_path: Path) -> None:
        """Empty source DB: import produces 0 dest rows and returns a string."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path, populate=False)
        dest = _make_dest_conn()
        result = import_scope(src, "empty", dest)
        assert isinstance(result, str)
        assert _count_rows(dest, "documents", scope="project:empty") == 0


# ===========================================================================
# AC2 -- content-hash dedup: duplicate documents skipped
# ===========================================================================


class TestFromAC_ImportScopeDedup:  # noqa: N801
    """import_scope skips documents whose content hash already exists in dest under same scope."""

    def test_same_content_hash_not_imported_twice(self, tmp_path: Path) -> None:
        """Re-importing the same source file does not duplicate documents in dest."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        count_first = _count_rows(dest, "documents", scope="project:proj")
        import_scope(src, "proj", dest)
        count_second = _count_rows(dest, "documents", scope="project:proj")
        assert count_second == count_first, "Re-importing same source must not create duplicate documents"

    def test_different_content_imported(self, tmp_path: Path) -> None:
        """A document with different content IS imported -- no false-positive dedup."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src1 = tmp_path / "s1.db"
        conn1 = sqlite3.connect(str(src1))
        init_db(conn1)
        _seed_source(conn1, doc_id="doc-a", content="first unique content version A")
        conn1.close()

        src2 = tmp_path / "s2.db"
        conn2 = sqlite3.connect(str(src2))
        init_db(conn2)
        _seed_source(conn2, doc_id="doc-b", content="second unique content version B")
        conn2.close()

        dest = _make_dest_conn()
        import_scope(src1, "proj", dest)
        import_scope(src2, "proj", dest)
        count = _count_rows(dest, "documents", scope="project:proj")
        assert count == 2, "Two documents with distinct content must both be imported"

    def test_dedup_uses_content_hash_not_document_id(self, tmp_path: Path) -> None:
        """Dedup is based on content hash -- same content in two DBs: only one import."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        shared_content = "identical content in two different source documents"
        src1 = tmp_path / "dup1.db"
        conn1 = sqlite3.connect(str(src1))
        init_db(conn1)
        _seed_source(conn1, doc_id="doc-dup-1", content=shared_content)
        conn1.close()

        src2 = tmp_path / "dup2.db"
        conn2 = sqlite3.connect(str(src2))
        init_db(conn2)
        _seed_source(conn2, doc_id="doc-dup-2", content=shared_content)
        conn2.close()

        dest = _make_dest_conn()
        import_scope(src1, "proj", dest)
        import_scope(src2, "proj", dest)
        count = _count_rows(dest, "documents", scope="project:proj")
        assert count == 1, "Documents with identical content hash: second import must be skipped (dedup)"

    def test_dedup_skip_does_not_add_orphan_entities(self, tmp_path: Path) -> None:
        """When a document is deduped, its child entities are also not re-imported."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        import_scope(src, "proj", dest)
        count_first = _count_rows(dest, "entities", scope="project:proj")
        import_scope(src, "proj", dest)
        count_second = _count_rows(dest, "entities", scope="project:proj")
        assert count_second == count_first, "Duplicate entity rows must not accumulate when parent document is deduped"


# ===========================================================================
# AC3 -- export_scope creates SQLite file with schema and scoped rows only
# ===========================================================================


class TestFromAC_ExportScope:  # noqa: N801
    """export_scope produces a valid SQLite file containing only rows matching the scope."""

    def test_export_creates_output_file(self, tmp_path: Path) -> None:
        """export_scope creates a file at output_path."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, doc_id="doc-1", scope="project:myapp")
        out = tmp_path / "export.db"
        export_scope("project:myapp", out, src_conn)
        assert out.exists(), "export_scope must create the output file"

    def test_export_file_contains_schema_version_table(self, tmp_path: Path) -> None:
        """Exported SQLite file has schema_version table (init_db was applied)."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:myapp")
        out = tmp_path / "export.db"
        export_scope("project:myapp", out, src_conn)
        exported = sqlite3.connect(str(out))
        row = exported.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
        exported.close()
        assert row is not None, "Exported file must have schema_version table"

    def test_export_copies_documents_matching_scope(self, tmp_path: Path) -> None:
        """Exported file contains document rows for the specified scope."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, doc_id="doc-target", scope="project:target")
        out = tmp_path / "export.db"
        export_scope("project:target", out, src_conn)
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "documents", scope="project:target")
        exported.close()
        assert count >= 1

    def test_export_excludes_documents_from_other_scopes(self, tmp_path: Path) -> None:
        """Exported file does NOT include rows from scopes other than the requested one."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, doc_id="doc-target", scope="project:target")
        _seed_source(src_conn, doc_id="doc-other", scope="project:other")
        out = tmp_path / "export.db"
        export_scope("project:target", out, src_conn)
        exported = sqlite3.connect(str(out))
        other_count = _count_rows(exported, "documents", scope="project:other")
        exported.close()
        assert other_count == 0, "Rows from other scopes must not appear in export"

    def test_export_copies_chunks(self, tmp_path: Path) -> None:
        """Chunk rows matching the scope are included in the exported file."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:app")
        out = tmp_path / "export.db"
        export_scope("project:app", out, src_conn)
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "chunks", scope="project:app")
        exported.close()
        assert count >= 1

    def test_export_copies_entities(self, tmp_path: Path) -> None:
        """Entity rows matching the scope are included in the exported file."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:app")
        out = tmp_path / "export.db"
        export_scope("project:app", out, src_conn)
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "entities", scope="project:app")
        exported.close()
        assert count >= 1

    def test_export_copies_edges(self, tmp_path: Path) -> None:
        """Edge rows matching the scope are included in the exported file."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:app")
        out = tmp_path / "export.db"
        export_scope("project:app", out, src_conn)
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "edges", scope="project:app")
        exported.close()
        assert count >= 1

    def test_export_copies_document_status(self, tmp_path: Path) -> None:
        """document_status rows matching the scope are included in the exported file."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:app")
        out = tmp_path / "export.db"
        export_scope("project:app", out, src_conn)
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "document_status", scope="project:app")
        exported.close()
        assert count >= 1

    def test_export_returns_string_result(self, tmp_path: Path) -> None:
        """export_scope returns a string (success message or summary)."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        _seed_source(src_conn, scope="project:app")
        out = tmp_path / "export.db"
        result = export_scope("project:app", out, src_conn)
        assert isinstance(result, str)

    def test_export_empty_scope_creates_schema_valid_sqlite(self, tmp_path: Path) -> None:
        """Exporting a scope with no rows creates an empty-but-schema-valid SQLite file."""
        from owlbear_knowledge.scope_transfer import export_scope  # noqa: PLC0415

        src_conn = _make_dest_conn()
        out = tmp_path / "empty_export.db"
        export_scope("project:nonexistent", out, src_conn)
        assert out.exists()
        exported = sqlite3.connect(str(out))
        count = _count_rows(exported, "documents")
        exported.close()
        assert count == 0


# ===========================================================================
# AC4 -- import path is sandboxed via sandbox_path
# ===========================================================================


class TestFromAC_ImportScopeSandboxing:  # noqa: N801
    """import_scope rejects path traversal attempts with an error: prefix message."""

    def test_path_traversal_returns_error_prefix(self, tmp_path: Path) -> None:
        """Paths that escape workspace_root return error: message."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        traversal = tmp_path / ".." / ".." / "etc" / "passwd"
        dest = _make_dest_conn()
        result = import_scope(traversal, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"Path traversal must return error: prefix, got: {result!r}"

    def test_null_byte_in_path_returns_error_prefix(self, tmp_path: Path) -> None:
        """Paths containing null bytes are rejected with error: prefix."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        null_path = tmp_path / "evil\x00path.db"
        dest = _make_dest_conn()
        result = import_scope(null_path, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"Null-byte path must return error: prefix, got: {result!r}"

    def test_valid_path_within_workspace_root_is_accepted(self, tmp_path: Path) -> None:
        """A valid path inside workspace_root does NOT trigger sandbox rejection."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        result = import_scope(src, "proj", dest, workspace_root=tmp_path)
        assert not result.startswith("error: "), f"Valid path must not be sandboxed, got: {result!r}"


# ===========================================================================
# AC5 -- auto-detect .owlbear/knowledge/knowledge.db when path=None
# ===========================================================================


class TestFromAC_ImportScopeAutoDetect:  # noqa: N801
    """import_scope auto-detects .owlbear/knowledge/knowledge.db when path is None."""

    def test_auto_detect_uses_owlbear_knowledge_db_when_exists(self, tmp_path: Path) -> None:
        """When path=None and .owlbear/knowledge/knowledge.db exists it is used."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        auto_dir = tmp_path / ".owlbear" / "knowledge"
        auto_dir.mkdir(parents=True)
        auto_db = auto_dir / "knowledge.db"
        conn = sqlite3.connect(str(auto_db))
        init_db(conn)
        _seed_source(conn, doc_id="auto-doc")
        conn.close()

        dest = _make_dest_conn()
        result = import_scope(None, "autoproject", dest, workspace_root=tmp_path)
        assert not result.startswith("error: "), f"Auto-detect should find .owlbear/knowledge/knowledge.db: {result!r}"
        assert _count_rows(dest, "documents", scope="project:autoproject") >= 1

    def test_auto_detect_returns_error_when_no_path_and_no_file(self, tmp_path: Path) -> None:
        """When path=None and .owlbear/knowledge/knowledge.db missing, returns error: ."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        dest = _make_dest_conn()
        result = import_scope(None, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"Missing auto-detect file must return error: prefix, got: {result!r}"

    def test_env_var_overrides_auto_detect(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_LOCAL_KB_PATH env var takes precedence over auto-detect."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        env_db = tmp_path / "env_kb.db"
        conn = sqlite3.connect(str(env_db))
        init_db(conn)
        _seed_source(conn, doc_id="env-doc")
        conn.close()

        auto_dir = tmp_path / ".owlbear" / "knowledge"
        auto_dir.mkdir(parents=True)
        sqlite3.connect(str(auto_dir / "knowledge.db")).close()

        monkeypatch.setenv("OWLBEAR_LOCAL_KB_PATH", str(env_db))
        dest = _make_dest_conn()
        result = import_scope(None, "envproj", dest, workspace_root=tmp_path)
        assert not result.startswith("error: "), f"Env-var path must be used: {result!r}"
        assert _count_rows(dest, "documents", scope="project:envproj") >= 1

    def test_explicit_path_overrides_auto_detect(self, tmp_path: Path) -> None:
        """Explicit path argument takes precedence over auto-detect."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        explicit = _make_source_file(tmp_path, doc_id="explicit-doc")
        dest = _make_dest_conn()
        result = import_scope(explicit, "explicitproj", dest, workspace_root=tmp_path)
        assert not result.startswith("error: ")
        assert _count_rows(dest, "documents", scope="project:explicitproj") >= 1


# ===========================================================================
# AC6 -- source file validation
# ===========================================================================


class TestFromAC_ImportScopeSchemaValidation:  # noqa: N801
    """import_scope validates source: must be SQLite with schema_version table."""

    def test_non_sqlite_file_returns_error_prefix(self, tmp_path: Path) -> None:
        """A non-SQLite file returns error: message and does not raise."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        bad_file = tmp_path / "not_sqlite.db"
        bad_file.write_bytes(b"this is not a sqlite file at all !!!!")
        dest = _make_dest_conn()
        result = import_scope(bad_file, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"Non-SQLite file must return error: prefix, got: {result!r}"

    def test_sqlite_without_schema_version_returns_error_prefix(self, tmp_path: Path) -> None:
        """A valid SQLite without schema_version table returns error: message."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        no_schema = tmp_path / "no_schema_version.db"
        conn = sqlite3.connect(str(no_schema))
        conn.execute("CREATE TABLE some_other_table (id TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()
        dest = _make_dest_conn()
        result = import_scope(no_schema, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"SQLite without schema_version must return error: prefix, got: {result!r}"

    def test_file_not_found_returns_error_prefix(self, tmp_path: Path) -> None:
        """A path that does not exist returns error: message."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        missing = tmp_path / "does_not_exist.db"
        dest = _make_dest_conn()
        result = import_scope(missing, "proj", dest, workspace_root=tmp_path)
        assert result.startswith("error: "), f"Missing file must return error: prefix, got: {result!r}"

    def test_valid_sqlite_with_schema_version_does_not_error(self, tmp_path: Path) -> None:
        """A valid SQLite with schema_version does not produce an error: result."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest = _make_dest_conn()
        result = import_scope(src, "proj", dest, workspace_root=tmp_path)
        assert not result.startswith("error: "), f"Valid SQLite with schema_version must not error: {result!r}"


# ===========================================================================
# AC1 (atomic transaction) -- all-or-nothing import
# ===========================================================================


class TestFromAC_ImportScopeTransaction:  # noqa: N801
    """Entire import is wrapped in a single transaction: all-or-nothing."""

    def test_no_partial_state_when_import_fails_mid_way(self, tmp_path: Path) -> None:
        """If import fails (broken dest schema), no partial rows committed."""
        from owlbear_knowledge.scope_transfer import import_scope  # noqa: PLC0415

        src = _make_source_file(tmp_path)
        dest_bad = _make_dest_conn()
        dest_bad.execute("DROP TABLE IF EXISTS entities")
        dest_bad.commit()

        result = import_scope(src, "proj", dest_bad, workspace_root=tmp_path)
        if not result.startswith("error: "):
            pytest.skip("Forced-failure scenario did not trigger on this DB state")
        count = dest_bad.execute("SELECT count(*) FROM documents WHERE scope = 'project:proj'").fetchone()[0]
        assert count == 0, "Partial state must not be committed on failed import (atomic txn)"


# ===========================================================================
# MCP tool wiring -- server.py registration and ToolAnnotations
# ===========================================================================


class TestFromAC_MCPToolWiring:  # noqa: N801
    """import_scope and export_scope are registered MCP tools with ToolAnnotations."""

    def test_import_scope_tool_registered_on_server(self) -> None:
        """server.py exposes import_scope as a module-level callable (MCP tool)."""
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "import_scope"), "import_scope MCP tool missing from mcp-knowledge server.py"

    def test_export_scope_tool_registered_on_server(self) -> None:
        """server.py exposes export_scope as a module-level callable (MCP tool)."""
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "export_scope"), "export_scope MCP tool missing from mcp-knowledge server.py"

    def test_import_scope_tool_has_tool_annotations(self) -> None:
        """import_scope tool declares ToolAnnotations on the MCP instance."""
        annotations = _get_tool_annotations_from_server("import_scope")
        assert annotations is not None, "import_scope must declare ToolAnnotations"

    def test_export_scope_tool_has_tool_annotations(self) -> None:
        """export_scope tool declares ToolAnnotations on the MCP instance."""
        annotations = _get_tool_annotations_from_server("export_scope")
        assert annotations is not None, "export_scope must declare ToolAnnotations"

    def test_import_scope_is_not_read_only(self) -> None:
        """import_scope writes to dest KB -- readOnlyHint must not be True."""
        annotations = _get_tool_annotations_from_server("import_scope")
        if annotations is None:
            pytest.fail("import_scope has no ToolAnnotations -- cannot verify readOnlyHint")
        assert annotations.readOnlyHint is not True, (  # type: ignore[union-attr]
            "import_scope writes to the KB -- readOnlyHint must be False or unset"
        )

    def test_export_scope_is_read_only(self) -> None:
        """export_scope only reads source KB -- readOnlyHint must be True."""
        annotations = _get_tool_annotations_from_server("export_scope")
        if annotations is None:
            pytest.fail("export_scope has no ToolAnnotations -- cannot verify readOnlyHint")
        assert annotations.readOnlyHint is True, (  # type: ignore[union-attr]
            "export_scope only reads source KB -- readOnlyHint must be True"
        )

    @pytest.mark.asyncio
    async def test_import_scope_tool_returns_error_prefix_when_no_file(self) -> None:
        """MCP import_scope returns error: string when source file is missing."""
        from owlbear_mcp_knowledge.server import import_scope as mcp_import_scope  # noqa: PLC0415

        mock_app_ctx = MagicMock()
        mock_app_ctx.conn = _make_dest_conn()
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app_ctx

        result = await mcp_import_scope(mock_ctx, path=None, project_name="testproject")
        assert isinstance(result, str)
        assert result.startswith("error: "), f"MCP import_scope must return error: prefix when file missing: {result!r}"
