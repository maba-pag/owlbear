"""Tests for task #587: Fix row_factory in mcp-memory app_lifespan (TDD RED).

Contract-level tests verifying that app_lifespan sets conn.row_factory = sqlite3.Row
and that get_knowledge / list_entries return correct list[dict] results through the
production lifespan path.

AC coverage:
  - AC1: app_lifespan yields AppContext whose conn.row_factory is sqlite3.Row
  - AC2: Tests exercise production lifespan path (not test-helper _make_conn)
  - AC3: Tests fail before the fix  — sqlite3.connect() defaults row_factory to None
  - AC4: Tests use OWLBEAR_MEMORY_DB_PATH env var override (tmp_path) to avoid
          disk side effects
  - AC5: ruff clean

All tests FAIL in RED phase:
  - test_row_factory_* → AssertionError: conn.row_factory is None, not sqlite3.Row
  - test_*_returns_list_of_dicts_* → ValueError from dict(plain_sqlite3_tuple)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_memory.server import app_lifespan
from owlbear_mcp_memory.tools import get_knowledge, list_entries

_INSERT_SQL = """
INSERT INTO memory_entries
    (id, content, category, confidence, created_at, updated_at, source,
     scope_agent, scope_project, approval_state, deleted_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class TestFromAC_AppLifespanRowFactory:
    """AC1-AC4: app_lifespan must set conn.row_factory = sqlite3.Row.

    All tests use the production app_lifespan context manager (not _make_conn).
    All tests FAIL before the fix because conn.row_factory defaults to None.
    """

    @pytest.mark.asyncio
    async def test_row_factory_is_sqlite3_row(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1+AC2: app_lifespan yields AppContext with conn.row_factory == sqlite3.Row.

        Fails before fix: conn.row_factory is None (sqlite3.connect() default).
        """
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db"))

        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.conn.row_factory is sqlite3.Row  # FAILS: currently None

    @pytest.mark.asyncio
    async def test_row_factory_is_not_none(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Boundary: row_factory must be explicitly set — None breaks dict(row) calls."""
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db"))

        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.conn.row_factory is not None  # FAILS: currently None

    @pytest.mark.asyncio
    async def test_get_knowledge_returns_list_of_dicts_via_production_lifespan(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1+AC2: get_knowledge returns list[dict] when using production lifespan conn.

        Fails before fix: dict(plain_sqlite3_tuple) raises ValueError
        because plain tuples are not row-factory-enabled mappings.
        """
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db"))

        async with app_lifespan(MagicMock()) as ctx:
            ctx.conn.execute(
                _INSERT_SQL,
                (
                    "entry-001",
                    "builder discovered pattern",
                    "knowledge",
                    0.85,
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "builder",
                    None,  # scope_agent — NULL → visible to any agent query
                    None,  # scope_project — NULL
                    "pending",
                    None,
                ),
            )
            ctx.conn.commit()

            mock_mcp_ctx = MagicMock()
            mock_mcp_ctx.request_context.lifespan_context = ctx

            results = await get_knowledge(mock_mcp_ctx, agent_id="builder")

            assert isinstance(results, list)
            assert len(results) == 1
            assert isinstance(results[0], dict)  # FAILS before fix: dict(tuple) error
            assert results[0]["id"] == "entry-001"
            assert results[0]["content"] == "builder discovered pattern"

    @pytest.mark.asyncio
    async def test_list_entries_returns_list_of_dicts_via_production_lifespan(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1+AC2: list_entries returns list[dict] when using production lifespan conn.

        Fails before fix: dict(plain_sqlite3_tuple) raises ValueError.
        """
        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "test.db"))

        async with app_lifespan(MagicMock()) as ctx:
            ctx.conn.execute(
                _INSERT_SQL,
                (
                    "entry-002",
                    "reviewer pattern",
                    "behavior",
                    0.90,
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "reviewer",
                    "reviewer",  # scope_agent
                    None,
                    "approved",
                    None,
                ),
            )
            ctx.conn.commit()

            mock_mcp_ctx = MagicMock()
            mock_mcp_ctx.request_context.lifespan_context = ctx

            results = await list_entries(mock_mcp_ctx, agent_id="reviewer")

            assert isinstance(results, list)
            assert len(results) == 1
            assert isinstance(results[0], dict)  # FAILS before fix: dict(tuple) error
            assert results[0]["id"] == "entry-002"
            assert results[0]["category"] == "behavior"
