"""OwlBear MCP memory server — scaffold with lifespan and SQLite DDL."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "AppContext",
    "_apply_tool_exclusions",  # noqa: F822 — defined in tools.py
    "app_lifespan",
    "get_knowledge",  # noqa: F822 — defined in tools.py
    "list_entries",  # noqa: F822 — defined in tools.py
    "mark_for_deletion",  # noqa: F822 — defined in tools.py
    "mcp",
    "record_learning",  # noqa: F822 — defined in tools.py
]

_DEFAULT_DB_PATH = "data/memory/memory.db"

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL,
    scope_agent TEXT,
    scope_project TEXT,
    approval_state TEXT NOT NULL DEFAULT 'pending',
    deleted_at TEXT
)
"""


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    conn: sqlite3.Connection
    project_name: str | None


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Initialise the memory database; close the connection on exit.

    Steps:
    (a) Resolve DB path from OWLBEAR_MEMORY_DB_PATH env var; default data/memory/memory.db.
    (b) Create parent directories if absent.
    (c) Open sqlite3 connection.
    (d) Set PRAGMA journal_mode=WAL and PRAGMA busy_timeout=5000.
    (e) Read project name from owlbear-project.json via stdlib json.
    (f) Run CREATE TABLE IF NOT EXISTS memory_entries DDL.
    (g) Yield AppContext.
    (h) Close connection in finally.
    """
    # (a) Resolve DB path
    db_path = Path(os.environ.get("OWLBEAR_MEMORY_DB_PATH", _DEFAULT_DB_PATH))

    # (b) Create parent directories
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # (c) Open connection
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    try:
        # (d) Set PRAGMAs
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        # (e) Read project name
        project_name: str | None = None
        project_json = Path("owlbear-project.json")
        if project_json.is_file():  # noqa: ASYNC240
            data = json.loads(project_json.read_text(encoding="utf-8"))  # noqa: ASYNC240
            project_name = data.get("name")

        # (f) Create table
        conn.execute(_DDL)
        conn.commit()

        # (g) Yield AppContext
        yield AppContext(conn=conn, project_name=project_name)
    finally:
        # (h) Close connection
        conn.close()


mcp = FastMCP("owlbear-memory", lifespan=app_lifespan)
