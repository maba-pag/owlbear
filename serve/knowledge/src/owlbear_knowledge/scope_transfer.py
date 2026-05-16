"""Scope-transfer utilities: import/export of project-local knowledge snapshots.

Provides :func:`import_scope` and :func:`export_scope` for portable, SQLite-based
project-local knowledge portability.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.status_store import compute_content_hash

_AUTO_DETECT_RELATIVE = Path(".owlbear") / "knowledge" / "local.db"
_ENV_VAR = "OWLBEAR_LOCAL_KB_PATH"

# FK-ordered tables for import and export (insert order respects FK constraints)
_TRANSFER_TABLES = ("documents", "document_status", "chunks", "entities", "edges")


# ---------------------------------------------------------------------------
# Global DB path resolution
# ---------------------------------------------------------------------------


def resolve_global_db_path(cwd: Path) -> Path | str:
    """Resolve the global knowledge DB path.

    The global resolution path depended on owlbear-project.json infrastructure,
    which has been removed.
    """
    _ = cwd
    msg = "global DB path resolution removed — see #1296"
    raise NotImplementedError(msg)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_source(src_path: Path) -> str | None:
    """Validate that *src_path* is a SQLite file with a ``schema_version`` table.

    Returns an ``error: `` string on failure, or ``None`` if valid.
    """
    if not src_path.exists():
        return f"error: source file not found: {src_path}"
    try:
        conn = sqlite3.connect(str(src_path))
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
        conn.close()
    except sqlite3.DatabaseError as exc:
        return f"error: source is not a valid SQLite database: {exc}"
    if row is None:
        return "error: source missing schema_version table — not an owlbear knowledge database"
    return None


# ---------------------------------------------------------------------------
# Core import — private helpers
# ---------------------------------------------------------------------------


def _insert_documents(
    dest_conn: sqlite3.Connection,
    docs: list[sqlite3.Row],
    skipped_doc_ids: set[str],
    doc_id_map: dict[str, str],
    target_scope: str,
) -> None:
    for doc in docs:
        old_id = doc["id"]
        if old_id in skipped_doc_ids:
            continue
        dest_conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
            (
                doc_id_map[old_id],
                doc["title"],
                doc["content"],
                doc["metadata"],
                doc["created_at"],
                target_scope,
            ),
        )


def _insert_document_statuses(
    dest_conn: sqlite3.Connection,
    doc_statuses: dict[str, sqlite3.Row],
    skipped_doc_ids: set[str],
    doc_id_map: dict[str, str],
    target_scope: str,
) -> None:
    for old_doc_id, status in doc_statuses.items():
        if old_doc_id in skipped_doc_ids:
            continue
        new_doc_id = doc_id_map.get(old_doc_id)
        if new_doc_id is None:
            continue
        dest_conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                new_doc_id,
                status["status"],
                status["source"],
                target_scope,
                status["created_at"],
                status["updated_at"],
                status["content_hash"],
            ),
        )


def _insert_chunks(  # noqa: PLR0913
    dest_conn: sqlite3.Connection,
    chunks: list[sqlite3.Row],
    skipped_doc_ids: set[str],
    doc_id_map: dict[str, str],
    chunk_id_map: dict[str, str],
    target_scope: str,
) -> None:
    for chunk in chunks:
        if chunk["document_id"] in skipped_doc_ids:
            continue
        new_id = chunk_id_map.get(chunk["id"])
        if new_id is None:
            continue
        new_doc_id = doc_id_map.get(chunk["document_id"])
        dest_conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                new_id,
                new_doc_id,
                chunk["chunk_index"],
                chunk["content"],
                chunk["metadata"],
                chunk["created_at"],
                target_scope,
            ),
        )


def _insert_entities(  # noqa: PLR0913
    dest_conn: sqlite3.Connection,
    entities: list[sqlite3.Row],
    skipped_doc_ids: set[str],
    doc_id_map: dict[str, str],
    chunk_id_map: dict[str, str],
    entity_id_map: dict[str, str],
    target_scope: str,
) -> None:
    for entity in entities:
        if entity["document_id"] in skipped_doc_ids:
            continue
        new_id = entity_id_map.get(entity["id"])
        if new_id is None:
            continue
        new_doc_id = doc_id_map.get(entity["document_id"])
        old_chunk_id = entity["chunk_id"]
        new_chunk_id = chunk_id_map.get(old_chunk_id) if old_chunk_id else None
        dest_conn.execute(
            "INSERT INTO entities "
            "(id, name, entity_type, description, metadata, created_at, "
            " scope, document_id, chunk_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id,
                entity["name"],
                entity["entity_type"],
                entity["description"],
                entity["metadata"],
                entity["created_at"],
                target_scope,
                new_doc_id,
                new_chunk_id,
            ),
        )


def _insert_edges(
    dest_conn: sqlite3.Connection,
    edges: list[sqlite3.Row],
    entity_id_map: dict[str, str],
    target_scope: str,
) -> None:
    for edge in edges:
        new_src = entity_id_map.get(edge["source_id"])
        new_tgt = entity_id_map.get(edge["target_id"])
        if new_src is None or new_tgt is None:
            continue
        dest_conn.execute(
            "INSERT INTO edges "
            "(id, source_id, target_id, relation, weight, metadata, created_at, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                new_src,
                new_tgt,
                edge["relation"],
                edge["weight"],
                edge["metadata"],
                edge["created_at"],
                target_scope,
            ),
        )


# ---------------------------------------------------------------------------
# Core import
# ---------------------------------------------------------------------------


def _do_import(
    src_conn: sqlite3.Connection,
    dest_conn: sqlite3.Connection,
    target_scope: str,
    source_scope: str | None = None,
) -> str:
    """Execute the row-level copy from *src_conn* into *dest_conn* under *target_scope*.

    All inserts are wrapped in a single transaction (atomic).  Duplicate documents
    (same scope + content_hash already in dest) are skipped along with their child rows.

    Args:
        src_conn: Source SQLite connection to read rows from.
        dest_conn: Destination SQLite connection to write rows into.
        target_scope: Scope value assigned to all imported rows in *dest_conn*.
        source_scope: When non-None, only rows with ``scope = source_scope`` in the
            source are copied.  Defaults to ``None`` (copy all rows, backward-compatible).
    """
    # Gather content hashes already in dest under this scope for dedup
    existing_hashes: set[str] = {
        row[0]
        for row in dest_conn.execute(
            "SELECT content_hash FROM document_status WHERE scope = ? AND content_hash IS NOT NULL",
            (target_scope,),
        )
    }

    # Read source data (snapshots before transaction begins)
    src_conn.row_factory = sqlite3.Row
    if source_scope is not None:
        docs = src_conn.execute("SELECT * FROM documents WHERE scope = ?", (source_scope,)).fetchall()
        doc_ids_placeholder = ",".join("?" * len(docs)) if docs else "NULL"
        doc_ids = [doc["id"] for doc in docs]
        doc_statuses: dict[str, sqlite3.Row] = {
            row["document_id"]: row
            for row in src_conn.execute(
                f"SELECT * FROM document_status WHERE document_id IN ({doc_ids_placeholder})",  # noqa: S608
                doc_ids,
            ).fetchall()
        }
        chunks = src_conn.execute(
            f"SELECT * FROM chunks WHERE document_id IN ({doc_ids_placeholder})",  # noqa: S608
            doc_ids,
        ).fetchall()
        entities = src_conn.execute(
            f"SELECT * FROM entities WHERE document_id IN ({doc_ids_placeholder})",  # noqa: S608
            doc_ids,
        ).fetchall()
        # Edges are filtered to those where both endpoints belong to included entities
        entity_ids = [e["id"] for e in entities]
        if entity_ids:
            eid_placeholder = ",".join("?" * len(entity_ids))
            # fmt: off
            edges = src_conn.execute(
                f"SELECT * FROM edges WHERE source_id IN ({eid_placeholder})"  # noqa: S608
                f" AND target_id IN ({eid_placeholder})",
                entity_ids + entity_ids,
            ).fetchall()
            # fmt: on
        else:
            edges = []
    else:
        docs = src_conn.execute("SELECT * FROM documents").fetchall()
        doc_statuses = {row["document_id"]: row for row in src_conn.execute("SELECT * FROM document_status").fetchall()}
        chunks = src_conn.execute("SELECT * FROM chunks").fetchall()
        entities = src_conn.execute("SELECT * FROM entities").fetchall()
        edges = src_conn.execute("SELECT * FROM edges").fetchall()

    # Decide which documents to import vs skip (content-hash dedup)
    skipped_doc_ids: set[str] = set()
    doc_id_map: dict[str, str] = {}
    for doc in docs:
        old_id = doc["id"]
        status = doc_statuses.get(old_id)
        content = doc["content"] or ""
        content_hash = status["content_hash"] if status else compute_content_hash(content)
        if content_hash and content_hash in existing_hashes:
            skipped_doc_ids.add(old_id)
        else:
            doc_id_map[old_id] = str(uuid.uuid4())
            if content_hash:
                existing_hashes.add(content_hash)  # prevent within-batch duplicates

    # Build ID maps for child rows (only for non-skipped documents)
    chunk_id_map: dict[str, str] = {
        chunk["id"]: str(uuid.uuid4()) for chunk in chunks if chunk["document_id"] not in skipped_doc_ids
    }
    entity_id_map: dict[str, str] = {
        entity["id"]: str(uuid.uuid4()) for entity in entities if entity["document_id"] not in skipped_doc_ids
    }

    try:
        with dest_conn:
            _insert_documents(dest_conn, docs, skipped_doc_ids, doc_id_map, target_scope)
            _insert_document_statuses(dest_conn, doc_statuses, skipped_doc_ids, doc_id_map, target_scope)
            _insert_chunks(
                dest_conn,
                chunks,
                skipped_doc_ids,
                doc_id_map,
                chunk_id_map,
                target_scope,
            )
            _insert_entities(
                dest_conn,
                entities,
                skipped_doc_ids,
                doc_id_map,
                chunk_id_map,
                entity_id_map,
                target_scope,
            )
            _insert_edges(dest_conn, edges, entity_id_map, target_scope)
    except sqlite3.Error as exc:
        return f"error: import failed: {exc}"

    imported = len(doc_id_map)
    skipped = len(skipped_doc_ids)
    return f"Imported {imported} documents (skipped {skipped} duplicates) into scope {target_scope}"


def import_scope(  # noqa: PLR0912
    src_path: Path | str | None,
    project_name: str,
    dest_conn: sqlite3.Connection,
    *,
    workspace_root: Path | None = None,
) -> str:
    """Import a project-local knowledge snapshot into *dest_conn* under a project scope.

    Args:
        src_path: Path to the source SQLite file, or ``None`` to trigger auto-detect.
        project_name: Project name; all rows are imported under scope
            ``"project:{project_name}"``.
        dest_conn: Open SQLite connection to the destination knowledge base.
        workspace_root: If provided, the source path is sandboxed within this directory
            and auto-detect resolves ``.owlbear/knowledge/knowledge.db`` relative to it.

    Returns:
        A string result message; starts with ``"error: "`` on failure.
    """
    target_scope = f"project:{project_name}"

    # -- Resolve the source path --
    if src_path is not None:
        resolved_path = Path(src_path)
    else:
        # Check env var override first
        env_val = os.environ.get(_ENV_VAR)
        if env_val:
            resolved_path = Path(env_val)
        elif workspace_root is not None:
            # Check local.db (primary) then knowledge.db (backward compat)
            for _candidate in (
                workspace_root / _AUTO_DETECT_RELATIVE,
                workspace_root / Path(".owlbear") / "knowledge" / "knowledge.db",
            ):
                if _candidate.exists():
                    resolved_path = _candidate
                    break
            else:
                return "error: explicit source path required (local DB is the running DB)"
        else:
            return "error: explicit source path required (local DB is the running DB)"

    # -- Sandbox check (when workspace_root is provided) --
    if workspace_root is not None:
        try:
            resolved_path = sandbox_path(workspace_root, resolved_path)
        except PermissionError as exc:
            return f"error: {exc}"
    else:
        resolved_path = Path(resolved_path)

    # -- Validate source file --
    err = _validate_source(resolved_path)
    if err:
        return err

    # -- Open source and execute import --
    src_conn = sqlite3.connect(str(resolved_path))
    try:
        return _do_import(src_conn, dest_conn, target_scope)
    finally:
        src_conn.close()


# ---------------------------------------------------------------------------
# Core export
# ---------------------------------------------------------------------------


def export_scope(
    scope: str,
    output_path: Path | str,
    source_conn: sqlite3.Connection,
) -> str:
    """Export all rows for *scope* from *source_conn* to a new SQLite file.

    The output file is created (or overwritten) at *output_path* with a full
    ``init_db`` schema.  Only rows matching ``scope`` are copied; Qdrant
    embeddings are excluded (ephemeral — re-embedded on import).

    Args:
        scope: The scope to export (e.g., ``"project:myapp"``).
        output_path: Destination file path for the exported SQLite database.
        source_conn: Open SQLite connection to the source knowledge base.

    Returns:
        A string result message; starts with ``"error: "`` on failure.
    """
    out = Path(output_path)
    try:
        dest_conn = sqlite3.connect(str(out))
        init_db(dest_conn)

        for table in _TRANSFER_TABLES:
            # Get column names from destination (canonical schema)
            cursor = dest_conn.execute(f"SELECT * FROM {table} LIMIT 0")  # noqa: S608
            cols = [d[0] for d in cursor.description]
            col_names = ", ".join(cols)
            placeholders = ", ".join("?" * len(cols))

            rows = source_conn.execute(
                f"SELECT {col_names} FROM {table} WHERE scope = ?",  # noqa: S608
                (scope,),
            ).fetchall()

            for row in rows:
                dest_conn.execute(
                    f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",  # noqa: S608
                    tuple(row),
                )

        dest_conn.commit()
        dest_conn.close()
    except Exception as exc:  # noqa: BLE001
        return f"error: export failed: {exc}"

    doc_count = source_conn.execute("SELECT count(*) FROM documents WHERE scope = ?", (scope,)).fetchone()[0]
    return f"Exported {doc_count} documents from scope {scope!r} to {out}"
