"""DDL and database initialization for the knowledge graph.

Creates all relational tables required by the knowledge graph: documents,
entities, edges, chunks, document_status, knowledge_sources, bookmarks,
consolidations, and a schema version tracker.
Calling ``init_db`` multiple times is safe (idempotent).

Vector storage is handled externally by Qdrant (see ``qdrant.py``).
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION: int = 8
"""Current schema version written to the ``schema_version`` table."""

_SCOPE_TABLES: tuple[str, ...] = (
    "entities",
    "documents",
    "edges",
    "chunks",
    "document_status",
)
"""Tables that carry a ``scope`` column (added in v3)."""

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------

_CREATE_DOCUMENTS = """\
CREATE TABLE IF NOT EXISTS documents (
    id         TEXT PRIMARY KEY,
    title      TEXT,
    content    TEXT,
    metadata   TEXT,
    created_at TEXT,
    scope      TEXT DEFAULT 'global'
)
"""

_CREATE_ENTITIES = """\
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    entity_type TEXT,
    description TEXT,
    metadata    TEXT,
    created_at  TEXT,
    scope       TEXT DEFAULT 'global',
    document_id TEXT,
    chunk_id    TEXT,
    importance  REAL DEFAULT 0.5
)
"""

_CREATE_EDGES = """\
CREATE TABLE IF NOT EXISTS edges (
    id         TEXT PRIMARY KEY,
    source_id  TEXT REFERENCES entities(id),
    target_id  TEXT REFERENCES entities(id),
    relation   TEXT,
    weight     REAL,
    metadata   TEXT,
    created_at TEXT,
    scope      TEXT DEFAULT 'global'
)
"""

_CREATE_CHUNKS = """\
CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    document_id   TEXT REFERENCES documents(id),
    chunk_index   INTEGER,
    content       TEXT,
    metadata      TEXT,
    created_at    TEXT,
    scope         TEXT DEFAULT 'global',
    consolidated  INTEGER DEFAULT 0
)
"""

_CREATE_DOCUMENT_STATUS = """\
CREATE TABLE IF NOT EXISTS document_status (
    document_id    TEXT PRIMARY KEY,
    status         TEXT,
    source         TEXT,
    error          TEXT,
    created_at     TEXT,
    updated_at     TEXT,
    scope          TEXT DEFAULT 'global',
    content_hash   TEXT
)
"""

_CREATE_KNOWLEDGE_SOURCES = """\
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    source_type       TEXT NOT NULL,
    config            TEXT NOT NULL,
    scope             TEXT DEFAULT 'global',
    enabled           INTEGER DEFAULT 1,
    priority          INTEGER DEFAULT 0,
    last_refreshed_at TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
)
"""

_CREATE_BOOKMARKS = """\
CREATE TABLE IF NOT EXISTS bookmarks (
    id              TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    tags            TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    reason          TEXT,
    scope           TEXT NOT NULL DEFAULT 'global',
    document_id     TEXT,
    content_hash    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
)
"""

_CREATE_CONSOLIDATIONS = """\
CREATE TABLE IF NOT EXISTS consolidations (
    id         TEXT PRIMARY KEY,
    source_ids TEXT NOT NULL,
    summary    TEXT,
    insight    TEXT,
    created_at TEXT,
    scope      TEXT DEFAULT 'global'
)
"""

_CREATE_SCHEMA_VERSION = """\
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER,
    applied_at TEXT
)
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate a v1 knowledge-graph database to v2.

    Adds the ``chunks`` and ``document_status`` tables.  Safe to call
    multiple times (idempotent).
    """
    # New tables — IF NOT EXISTS makes this idempotent.
    conn.execute(_CREATE_CHUNKS)
    conn.execute(_CREATE_DOCUMENT_STATUS)

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (2, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Migrate a v2 knowledge-graph database to v3.

    Adds a ``scope`` column (``TEXT DEFAULT 'global'``) to: entities,
    documents, edges, chunks, and embedding_rowid_map.  Creates indexes
    on the new scope columns for query performance.  Safe to call
    multiple times (idempotent).
    """
    for table in _SCOPE_TABLES:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN scope TEXT DEFAULT 'global'")

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (3, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Migrate a v3 knowledge-graph database to v4.

    Adds ``content_hash`` TEXT column to ``document_status``,
    ``document_id`` TEXT column to ``entities``, and an index on
    ``document_status(source)``.  Safe to call multiple times
    (idempotent).
    """
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE document_status ADD COLUMN content_hash TEXT")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN document_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_status_source ON document_status(source)")

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (4, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Migrate a v4 knowledge-graph database to v5.

    Adds ``chunk_id`` TEXT column to ``entities``, linking each entity
    back to its source chunk.  Safe to call multiple times (idempotent).
    """
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN chunk_id TEXT")

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (5, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """Migrate a v5 knowledge-graph database to v6.

    Adds the ``knowledge_sources`` table and indexes.  Safe to call
    multiple times (idempotent).
    """
    conn.execute(_CREATE_KNOWLEDGE_SOURCES)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope "
        "ON knowledge_sources(name, scope)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_sources_scope ON knowledge_sources(scope)"
    )

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (6, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v6_to_v7(conn: sqlite3.Connection) -> None:
    """Migrate a v6 knowledge-graph database to v7.

    Adds the ``bookmarks`` table and indexes.  Safe to call
    multiple times (idempotent).
    """
    conn.execute(_CREATE_BOOKMARKS)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_scope ON bookmarks(url, scope)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_scope ON bookmarks(scope)")

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (7, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v7_to_v8(conn: sqlite3.Connection) -> None:
    """Migrate a v7 knowledge-graph database to v8.

    Adds ``importance`` REAL column to ``entities``, ``consolidated``
    INTEGER column to ``chunks``, and creates the ``consolidations``
    table.  Safe to call multiple times (idempotent).
    """
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN importance REAL DEFAULT 0.5")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE chunks ADD COLUMN consolidated INTEGER DEFAULT 0")
    conn.execute(_CREATE_CONSOLIDATIONS)

    # Bump the stored version.
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (8, datetime.now(tz=UTC).isoformat()),
    )


def init_db(conn: sqlite3.Connection) -> None:
    """Create all knowledge-graph relational tables if they do not exist.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection`.  Works with both file-backed
            and ``:memory:`` databases.

    The function is **idempotent** — calling it more than once on the same
    connection is safe and will not duplicate data or raise errors.

    If the database contains an older schema, it is automatically migrated
    through v2, v3, v4, v5, v6, v7, and v8.  The v2 migration adds ``chunks``
    and ``document_status``; the v3 migration adds ``scope`` columns to five
    tables; the v4 migration adds ``content_hash`` to ``document_status``,
    ``document_id`` to ``entities``, and indexes ``document_status(source)``;
    the v5 migration adds ``chunk_id`` to ``entities``; the v6 migration
    adds the ``knowledge_sources`` table with indexes; the v7 migration
    adds the ``bookmarks`` table with indexes; the v8 migration adds
    ``importance`` to ``entities``, ``consolidated`` to ``chunks``, and
    creates the ``consolidations`` table.

    Vector storage is handled externally by Qdrant — no sqlite-vec
    extension or vec0 virtual tables are used.
    """
    # Enable foreign-key enforcement for this connection.
    conn.execute("PRAGMA foreign_keys = ON")

    # Relational tables -----------------------------------------------------
    conn.execute(_CREATE_DOCUMENTS)
    conn.execute(_CREATE_ENTITIES)
    conn.execute(_CREATE_EDGES)
    conn.execute(_CREATE_CHUNKS)
    conn.execute(_CREATE_DOCUMENT_STATUS)
    conn.execute(_CREATE_KNOWLEDGE_SOURCES)
    conn.execute(_CREATE_BOOKMARKS)
    conn.execute(_CREATE_CONSOLIDATIONS)
    conn.execute(_CREATE_SCHEMA_VERSION)

    # Schema version — insert or migrate ------------------------------------
    row = conn.execute("SELECT count(*) FROM schema_version").fetchone()
    if row is None or row[0] == 0:
        # Fresh database — stamp current version.
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (_SCHEMA_VERSION, datetime.now(tz=UTC).isoformat()),
        )
    else:
        # Existing database — run migrations in sequence.
        ver_row = conn.execute("SELECT version FROM schema_version").fetchone()
        current = ver_row[0] if ver_row else 0
        if current < 2:  # noqa: PLR2004
            _migrate_v1_to_v2(conn)
        if current < 3:  # noqa: PLR2004
            _migrate_v2_to_v3(conn)
        if current < 4:  # noqa: PLR2004
            _migrate_v3_to_v4(conn)
        if current < 5:  # noqa: PLR2004
            _migrate_v4_to_v5(conn)
        if current < 6:  # noqa: PLR2004
            _migrate_v5_to_v6(conn)
        if current < 7:  # noqa: PLR2004
            _migrate_v6_to_v7(conn)
        if current < 8:  # noqa: PLR2004
            _migrate_v7_to_v8(conn)

    # Scope indexes (idempotent) --------------------------------------------
    for table in _SCOPE_TABLES:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_scope ON {table}(scope)")

    # Knowledge-sources indexes (idempotent) --------------------------------
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope "
        "ON knowledge_sources(name, scope)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_sources_scope ON knowledge_sources(scope)"
    )

    # Bookmarks indexes (idempotent) ----------------------------------------
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_scope ON bookmarks(url, scope)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_scope ON bookmarks(scope)")

    conn.commit()
