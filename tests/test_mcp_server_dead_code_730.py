"""Failing tests for task #730: dead code removal from server.py after KanbanEngine migration.

Refined AC (Architecture Review approved):
- Dead code removed from server.py: _run_kanban(), _ForwardSlashPath, _parse_task_json(),
  _DEFAULT_KANBAN_BIN, stale __all__ entries (_run_kanban, _parse_task_json)
- asyncio remains — now used by asyncio.to_thread(), not _run_kanban()
- Old subprocess test files removed: serve/mcp-kanban/tests/test_server.py,
  serve/mcp-kanban/tests/test_integration.py
- No import of _run_kanban or kanban_bin remains in serve/mcp-kanban/ tree

All tests FAIL until builder removes dead code and deletes obsolete test files.
"""

from __future__ import annotations

from pathlib import Path

import owlbear_mcp_kanban.server as _srv

_MCP_KANBAN_ROOT = Path(__file__).parent.parent / "serve" / "mcp-kanban"


class TestFromAC_DeadCodeRemoval:
    """Dead code symbols are absent from the server module namespace (AC line 1)."""

    def test_run_kanban_not_in_module(self) -> None:
        """_run_kanban() has been removed — not present in server module."""
        assert not hasattr(_srv, "_run_kanban"), "_run_kanban should be removed from server.py but is still present"

    def test_forward_slash_path_not_in_module(self) -> None:
        """_ForwardSlashPath class has been removed — not present in server module."""
        assert not hasattr(_srv, "_ForwardSlashPath"), (
            "_ForwardSlashPath should be removed from server.py but is still present"
        )

    def test_parse_task_json_not_in_module(self) -> None:
        """_parse_task_json() has been removed — not present in server module."""
        assert not hasattr(_srv, "_parse_task_json"), (
            "_parse_task_json should be removed from server.py but is still present"
        )

    def test_default_kanban_bin_not_in_module(self) -> None:
        """_DEFAULT_KANBAN_BIN constant has been removed — not present in server module."""
        assert not hasattr(_srv, "_DEFAULT_KANBAN_BIN"), (
            "_DEFAULT_KANBAN_BIN should be removed from server.py but is still present"
        )

    def test_asyncio_used_only_for_to_thread(self) -> None:
        """asyncio remains — but only for asyncio.to_thread(), not _run_kanban()."""
        assert hasattr(_srv, "asyncio"), "asyncio should still be imported (used by asyncio.to_thread)"

    def test_all_excludes_run_kanban(self) -> None:
        """__all__ no longer contains the stale _run_kanban entry."""
        assert "_run_kanban" not in _srv.__all__, "_run_kanban should be removed from __all__ in server.py"

    def test_all_excludes_parse_task_json(self) -> None:
        """__all__ no longer contains the stale _parse_task_json entry."""
        assert "_parse_task_json" not in _srv.__all__, "_parse_task_json should be removed from __all__ in server.py"


class TestFromAC_ObsoleteTestFilesRemoved:
    """Obsolete subprocess test files deleted from serve/mcp-kanban/tests/ (AC line 2)."""

    def test_test_server_py_deleted(self) -> None:
        """test_server.py no longer exists — it tests the obsolete subprocess API (#56/#89)."""
        stale = _MCP_KANBAN_ROOT / "tests" / "test_server.py"
        assert not stale.exists(), f"Obsolete test file still present: {stale} — delete it"

    def test_test_integration_py_deleted(self) -> None:
        """test_integration.py no longer exists — it requires the eliminated binary."""
        stale = _MCP_KANBAN_ROOT / "tests" / "test_integration.py"
        assert not stale.exists(), f"Obsolete test file still present: {stale} — delete it"


class TestFromAC_NoStaleReferences:
    """No kanban_bin or _run_kanban identifiers remain in the serve/mcp-kanban/ tree (AC line 5)."""

    def _py_files(self) -> list[Path]:
        return list(_MCP_KANBAN_ROOT.rglob("*.py"))

    def test_no_kanban_bin_in_tree(self) -> None:
        """'kanban_bin' does not appear in any Python file under serve/mcp-kanban/."""
        offenders = [
            str(f) for f in self._py_files() if "kanban_bin" in f.read_text(encoding="utf-8", errors="replace")
        ]
        assert offenders == [], f"'kanban_bin' still referenced in: {offenders}"

    def test_no_run_kanban_in_tree(self) -> None:
        """'_run_kanban' does not appear in any Python file under serve/mcp-kanban/."""
        offenders = [
            str(f) for f in self._py_files() if "_run_kanban" in f.read_text(encoding="utf-8", errors="replace")
        ]
        assert offenders == [], f"'_run_kanban' still referenced in: {offenders}"
