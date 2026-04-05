"""Tests for task #606: Update mcp-kanban path resolution for .owlbear/kanban/.

AC coverage:
  AC1: _DEFAULT_KANBAN_DIR updated to Path(".owlbear/kanban"); _DEFAULT_KANBAN_BIN auto-derives.
  AC2: FileNotFoundError message updated to reference .owlbear/kanban/kanban-md.exe.
  AC3: .vscode/mcp.json owlbear-kanban entry relies on defaults (verified by AC1 — no separate test).

All tests must FAIL in RED phase — current defaults still point to Path("kanban").
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (
    _DEFAULT_KANBAN_BIN,
    _DEFAULT_KANBAN_DIR,
    AppContext,
    app_lifespan,
)


class TestFromAC_KanbanPathResolution:
    """Contract tests for task #606 AC1 and AC2."""

    # -----------------------------------------------------------------------
    # AC1 — _DEFAULT_KANBAN_DIR and _DEFAULT_KANBAN_BIN constant values
    # -----------------------------------------------------------------------

    def test_default_kanban_dir_is_owlbear_dotdir(self) -> None:
        """AC1: _DEFAULT_KANBAN_DIR must equal Path('.owlbear/kanban')."""
        assert Path(".owlbear/kanban") == _DEFAULT_KANBAN_DIR, (
            "_DEFAULT_KANBAN_DIR still points to the old 'kanban' location; "
            "update to Path('.owlbear/kanban') in server.py L52"
        )

    def test_default_kanban_bin_reflects_new_dir(self) -> None:
        """AC1: _DEFAULT_KANBAN_BIN must equal Path('.owlbear/kanban/kanban-md.exe')."""
        assert Path(".owlbear/kanban") / "kanban-md.exe" == _DEFAULT_KANBAN_BIN, (
            "_DEFAULT_KANBAN_BIN still resolves to 'kanban/kanban-md.exe'; "
            "it auto-derives from _DEFAULT_KANBAN_DIR — update L52 in server.py"
        )

    # AC1 — boundary: old path must not be present in the derived bin path
    def test_default_kanban_bin_not_bare_kanban_prefix(self) -> None:
        """AC1 boundary: _DEFAULT_KANBAN_BIN must not start with 'kanban/'."""
        parts = Path(_DEFAULT_KANBAN_BIN).as_posix()
        assert not parts.startswith("kanban/"), (
            f"_DEFAULT_KANBAN_BIN still uses old 'kanban/' prefix: '{parts}'; "
            "expected prefix '.owlbear/kanban/'"
        )

    # AC1 — runtime: lifespan must yield AppContext with kanban_dir == new path
    @pytest.mark.asyncio
    async def test_lifespan_yields_ctx_with_new_kanban_dir(self) -> None:
        """AC1 runtime: app_lifespan yields AppContext with kanban_dir == Path('.owlbear/kanban')."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.Path.exists", return_value=True):
            async with app_lifespan(mock_server) as ctx:
                assert isinstance(ctx, AppContext)
                assert ctx.kanban_dir == Path(".owlbear/kanban"), (
                    f"Expected kanban_dir=Path('.owlbear/kanban') but got {ctx.kanban_dir!r}"
                )

    # -----------------------------------------------------------------------
    # AC2 — FileNotFoundError message must reflect new .owlbear path
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_error_message_names_new_path(self) -> None:
        """AC2 happy: FileNotFoundError message must contain '.owlbear/kanban/kanban-md.exe'."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.Path.exists", return_value=False), pytest.raises(FileNotFoundError) as exc_info:
            async with app_lifespan(mock_server) as _:
                pass  # pragma: no cover
        assert ".owlbear/kanban/kanban-md.exe" in str(exc_info.value), (
            "FileNotFoundError message must reference '.owlbear/kanban/kanban-md.exe'; "
            "update L115-119 in server.py"
        )

    @pytest.mark.asyncio
    async def test_lifespan_error_message_not_old_bare_kanban_path(self) -> None:
        """AC2 boundary: error message must NOT contain the old 'place binary at kanban/kanban-md.exe' string."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.Path.exists", return_value=False), pytest.raises(FileNotFoundError) as exc_info:
            async with app_lifespan(mock_server) as _:
                pass  # pragma: no cover
        msg = str(exc_info.value)
        assert "place binary at kanban/kanban-md.exe" not in msg, (
            "Old path string 'place binary at kanban/kanban-md.exe' still present in "
            "FileNotFoundError message; update L115-119 in server.py"
        )
