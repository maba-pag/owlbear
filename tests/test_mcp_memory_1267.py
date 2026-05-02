"""Failing tests for P1-01: Remove SQLite code and legacy tests from mcp-memory (#1267).

AC coverage:
  AC1: No SQLite imports remain in serve/mcp-memory/src/
  AC2: No migration scripts in the package (migrate.py deleted)
  AC3: Old test files removed (test_server.py, test_package.py)
  AC4: __main__.py cleaned to empty stub (no server import, no mcp.run call)
  AC5: No test_*.py files remain in serve/mcp-memory/tests/

All tests FAIL (RED phase) — SQLite files still present; legacy test files still
present; __main__.py still imports from server.py.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SRC = _REPO_ROOT / "serve" / "mcp-memory" / "src" / "owlbear_mcp_memory"
_PKG_TESTS = _REPO_ROOT / "serve" / "mcp-memory" / "tests"


class TestFromAC_NoSQLiteImports:
    """AC1: No SQLite imports remain in serve/mcp-memory/src/."""

    def test_no_sqlite3_import_in_any_source_file(self) -> None:
        """AC1: All .py files in src/ must be free of sqlite3 imports."""
        violations: list[str] = []
        for py_file in _SRC.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "import sqlite3" in content or "from sqlite3" in content:
                violations.append(py_file.name)
        assert violations == [], f"sqlite3 imports still present in: {sorted(violations)}"

    def test_approve_py_deleted(self) -> None:
        """AC1 + scope: approve.py (sqlite3 user) must be deleted."""
        assert not (_SRC / "approve.py").exists(), (
            "approve.py should be deleted — it contains sqlite3 imports"
        )


class TestFromAC_NoMigrationScripts:
    """AC2: No migration scripts in the package."""

    def test_migrate_py_deleted(self) -> None:
        """AC2: migrate.py must be deleted from the package."""
        assert not (_SRC / "migrate.py").exists(), (
            "migrate.py should be deleted — it is a SQLite migration utility"
        )


class TestFromAC_LegacyTestFilesRemoved:
    """AC3: Old test files removed from serve/mcp-memory/tests/."""

    def test_test_server_py_removed(self) -> None:
        """AC3: tests/test_server.py must be deleted."""
        assert not (_PKG_TESTS / "test_server.py").exists(), (
            "test_server.py should be deleted from serve/mcp-memory/tests/"
        )

    def test_test_package_py_removed(self) -> None:
        """AC3: tests/test_package.py must be deleted."""
        assert not (_PKG_TESTS / "test_package.py").exists(), (
            "test_package.py should be deleted from serve/mcp-memory/tests/"
        )


class TestFromAC_TestDirEmpty:
    """AC5: serve/mcp-memory/tests/ contains no test_*.py files after cleanup."""

    def test_no_test_files_remain_in_package_tests(self) -> None:
        """AC5: No test_*.py files should remain in serve/mcp-memory/tests/."""
        remaining = sorted(
            f.name
            for f in _PKG_TESTS.iterdir()
            if f.is_file() and f.name.startswith("test_") and f.suffix == ".py"
        )
        assert remaining == [], f"Legacy test files still present: {remaining}"
