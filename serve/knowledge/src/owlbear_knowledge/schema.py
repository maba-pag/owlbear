"""DDL and database initialization for the knowledge graph.

Creates all relational tables required by the knowledge graph: documents,
entities, edges, chunks, document_status, knowledge_sources, bookmarks,
consolidations, and a schema version tracker.
Calling ``init_db`` multiple times is safe (idempotent).
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION: int = 9
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
    scope      TEXT DEFAULT 'global',
    source_id  TEXT
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

_CREATE_SOURCE_PAGES = """\
CREATE TABLE IF NOT EXISTS source_pages (
    id                TEXT PRIMARY KEY,
    source_id         TEXT REFERENCES knowledge_sources(id),
    url               TEXT NOT NULL,
    approval_state    TEXT DEFAULT 'discovered',
    extraction_status TEXT DEFAULT 'pending',
    scope             TEXT DEFAULT 'global',
    created_at        TEXT,
    updated_at        TEXT
)
"""

# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate a v1 database to v2 — adds chunks and document_status tables."""
    conn.execute(_CREATE_CHUNKS)
    conn.execute(_CREATE_DOCUMENT_STATUS)
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (2, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Migrate a v2 database to v3 — adds scope columns to core tables."""
    for table in _SCOPE_TABLES:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN scope TEXT DEFAULT 'global'")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (3, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Migrate a v3 database to v4 — adds content_hash and document_id columns."""
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE document_status ADD COLUMN content_hash TEXT")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN document_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_status_source ON document_status(source)")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (4, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Migrate a v4 database to v5 — adds chunk_id column to entities."""
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN chunk_id TEXT")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (5, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """Migrate a v5 database to v6 — adds knowledge_sources table."""
    conn.execute(_CREATE_KNOWLEDGE_SOURCES)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope ON knowledge_sources(name, scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_sources_scope ON knowledge_sources(scope)")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (6, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v6_to_v7(conn: sqlite3.Connection) -> None:
    """Migrate a v6 database to v7 — adds bookmarks table."""
    conn.execute(_CREATE_BOOKMARKS)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_scope ON bookmarks(url, scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_scope ON bookmarks(scope)")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (7, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v7_to_v8(conn: sqlite3.Connection) -> None:
    """Migrate a v7 database to v8 — adds importance, consolidated, and consolidations table."""
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE entities ADD COLUMN importance REAL DEFAULT 0.5")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE chunks ADD COLUMN consolidated INTEGER DEFAULT 0")
    conn.execute(_CREATE_CONSOLIDATIONS)
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (8, datetime.now(tz=UTC).isoformat()),
    )


def _migrate_v8_to_v9(conn: sqlite3.Connection) -> None:
    """Migrate a v8 database to v9 — adds source_pages table and source_id FK on documents."""
    conn.execute(_CREATE_SOURCE_PAGES)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_pages_source_id ON source_pages(source_id)")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE documents ADD COLUMN source_id TEXT")
    conn.execute(
        "UPDATE schema_version SET version = ?, applied_at = ?",
        (9, datetime.now(tz=UTC).isoformat()),
    )


def _apply_migrations(conn: sqlite3.Connection, current: int) -> None:
    """Apply all pending schema migrations starting from *current* version."""
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
    if current < 9:  # noqa: PLR2004
        _migrate_v8_to_v9(conn)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db(conn: sqlite3.Connection) -> None:
    """Create all knowledge-graph relational tables if they do not exist.

    The function is **idempotent** — calling it more than once on the same
    connection is safe and will not duplicate data or raise errors.

    If the database contains an older schema, it is automatically migrated
    through v2-v9.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection`.  Works with both
            file-backed and ``:memory:`` databases.
    """
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(_CREATE_DOCUMENTS)
    conn.execute(_CREATE_ENTITIES)
    conn.execute(_CREATE_EDGES)
    conn.execute(_CREATE_CHUNKS)
    conn.execute(_CREATE_DOCUMENT_STATUS)
    conn.execute(_CREATE_KNOWLEDGE_SOURCES)
    conn.execute(_CREATE_BOOKMARKS)
    conn.execute(_CREATE_CONSOLIDATIONS)
    conn.execute(_CREATE_SOURCE_PAGES)
    conn.execute(_CREATE_SCHEMA_VERSION)

    row = conn.execute("SELECT count(*) FROM schema_version").fetchone()
    if row is None or row[0] == 0:
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (_SCHEMA_VERSION, datetime.now(tz=UTC).isoformat()),
        )
    else:
        ver_row = conn.execute("SELECT version FROM schema_version").fetchone()
        current = ver_row[0] if ver_row else 0
        _apply_migrations(conn, current)

    for table in _SCOPE_TABLES:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_scope ON {table}(scope)")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope ON knowledge_sources(name, scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_sources_scope ON knowledge_sources(scope)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_scope ON bookmarks(url, scope)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_scope ON bookmarks(scope)")

    conn.commit()
