"""Contract tests for #541 — daemon _log_to_journal async migration.

Tests verify AC lines NOT covered by #841 (test_daemon_journal_async.py):
- AC3: All 6 call sites in _recover_from_error use ``await _log_to_journal``
- AC4: ErrorJournal / JsonlStore remain purely synchronous (zero async methods)
- AC5: loop_detection.py._log_to_journal is NOT async (sync orchestrator)
- AC6: No new third-party dependencies added to daemon.py imports

Note: AC1 & AC2 are covered by tests/test_daemon_journal_async.py (#841).
Note: AC7 (existing daemon tests pass) is a meta-verification, not a unit test.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Source paths (relative to repo root, resolved at import time)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DAEMON_SRC = _REPO_ROOT / "src" / "owlbear" / "daemon.py"
_LOOP_DETECTION_SRC = _REPO_ROOT / "src" / "owlbear" / "orchestrator" / "loop_detection.py"
_ERROR_JOURNAL_SRC = _REPO_ROOT / "src" / "owlbear" / "memory" / "error_journal.py"
_JSONL_STORE_SRC = _REPO_ROOT / "src" / "owlbear" / "core" / "jsonl_store.py"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _parse_module(path: Path) -> ast.Module:
    """Parse a Python source file into an AST module node."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_function(
    tree: ast.Module,
    name: str,
) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
    """Find a top-level or class-level function by *name* in *tree*."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _count_await_calls(func_node: ast.AST, callee_name: str) -> int:
    """Count ``await callee_name(...)`` expressions inside *func_node*."""
    count = 0
    for node in ast.walk(func_node):
        if (
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == callee_name
        ):
            count += 1
    return count


def _count_bare_calls(func_node: ast.AST, callee_name: str) -> int:
    """Count non-awaited ``callee_name(...)`` calls inside *func_node*.

    A "bare" call is any Call node whose func is ``callee_name`` but the
    Call is NOT the immediate child of an Await node.
    """
    awaited_ids: set[int] = set()
    for node in ast.walk(func_node):
        if (
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == callee_name
        ):
            awaited_ids.add(id(node.value))

    bare = 0
    for node in ast.walk(func_node):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == callee_name
            and id(node) not in awaited_ids
        ):
            bare += 1
    return bare


# ---------------------------------------------------------------------------
# AC3 — All 6 call sites in _recover_from_error use await _log_to_journal
# ---------------------------------------------------------------------------


class TestFromAC_RecoverCallSitesAwait:  # noqa: N801
    """_recover_from_error must ``await _log_to_journal(...)`` at every call site."""

    def test_recover_from_error_is_async(self) -> None:
        """_recover_from_error itself must be declared as ``async def``."""
        tree = _parse_module(_DAEMON_SRC)
        func = _find_function(tree, "_recover_from_error")
        assert func is not None, "_recover_from_error not found in daemon.py"
        assert isinstance(func, ast.AsyncFunctionDef), "_recover_from_error must be async def"

    def test_exactly_six_await_log_to_journal_calls(self) -> None:
        """_recover_from_error must contain exactly 6 ``await _log_to_journal(...)`` calls."""
        tree = _parse_module(_DAEMON_SRC)
        func = _find_function(tree, "_recover_from_error")
        assert func is not None, "_recover_from_error not found"
        count = _count_await_calls(func, "_log_to_journal")
        assert count == 6, f"Expected 6 await _log_to_journal() calls, found {count}"

    def test_no_bare_log_to_journal_calls_in_recover(self) -> None:
        """There must be zero non-awaited _log_to_journal() calls."""
        tree = _parse_module(_DAEMON_SRC)
        func = _find_function(tree, "_recover_from_error")
        assert func is not None, "_recover_from_error not found"
        bare = _count_bare_calls(func, "_log_to_journal")
        assert bare == 0, (
            f"Found {bare} non-awaited _log_to_journal() call(s) in _recover_from_error"
        )

    def test_log_to_journal_is_async_def_in_daemon(self) -> None:
        """_log_to_journal in daemon.py must be ``async def`` (not plain def)."""
        tree = _parse_module(_DAEMON_SRC)
        func = _find_function(tree, "_log_to_journal")
        assert func is not None, "_log_to_journal not found in daemon.py"
        assert isinstance(func, ast.AsyncFunctionDef), (
            "_log_to_journal must be async def in daemon.py"
        )


# ---------------------------------------------------------------------------
# AC4 — ErrorJournal and JsonlStore remain purely synchronous
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalSynchronous:  # noqa: N801
    """ErrorJournal and JsonlStore must have zero async methods."""

    def test_error_journal_log_is_not_coroutine(self) -> None:
        """ErrorJournal.log must be a regular function, not a coroutine."""
        from owlbear.memory.error_journal import ErrorJournal

        assert not inspect.iscoroutinefunction(ErrorJournal.log), (
            "ErrorJournal.log must be synchronous"
        )

    def test_error_journal_query_is_not_coroutine(self) -> None:
        """ErrorJournal.query must be a regular function, not a coroutine."""
        from owlbear.memory.error_journal import ErrorJournal

        assert not inspect.iscoroutinefunction(ErrorJournal.query), (
            "ErrorJournal.query must be synchronous"
        )

    def test_jsonl_store_append_is_not_coroutine(self) -> None:
        """JsonlStore.append must be a regular function, not a coroutine."""
        from owlbear.core.jsonl_store import JsonlStore

        assert not inspect.iscoroutinefunction(JsonlStore.append), (
            "JsonlStore.append must be synchronous"
        )

    def test_error_journal_source_has_no_async_methods(self) -> None:
        """error_journal.py must contain zero ``async def`` declarations."""
        tree = _parse_module(_ERROR_JOURNAL_SRC)
        async_methods = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert async_methods == [], f"error_journal.py has async methods: {async_methods}"

    def test_jsonl_store_source_has_no_async_methods(self) -> None:
        """jsonl_store.py must contain zero ``async def`` declarations."""
        tree = _parse_module(_JSONL_STORE_SRC)
        async_methods = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert async_methods == [], f"jsonl_store.py has async methods: {async_methods}"


# ---------------------------------------------------------------------------
# AC5 — loop_detection.py._log_to_journal is NOT changed (sync orchestrator)
# ---------------------------------------------------------------------------


class TestFromAC_LoopDetectionUnchanged:  # noqa: N801
    """loop_detection.py._log_to_journal must remain synchronous."""

    def test_loop_detection_log_to_journal_is_sync_def(self) -> None:
        """LoopDetector._log_to_journal must be ``def``, not ``async def``."""
        tree = _parse_module(_LOOP_DETECTION_SRC)
        func = _find_function(tree, "_log_to_journal")
        assert func is not None, "_log_to_journal not found in loop_detection.py"
        assert isinstance(func, ast.FunctionDef), "loop_detection._log_to_journal must be sync def"
        assert not isinstance(func, ast.AsyncFunctionDef), (
            "loop_detection._log_to_journal must NOT be async"
        )

    def test_loop_detection_does_not_use_to_thread(self) -> None:
        """loop_detection._log_to_journal must call journal.log() directly."""
        tree = _parse_module(_LOOP_DETECTION_SRC)
        func = _find_function(tree, "_log_to_journal")
        assert func is not None
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "to_thread":
                    pytest.fail("loop_detection._log_to_journal must not use asyncio.to_thread")
                if isinstance(node.func, ast.Name) and node.func.id == "to_thread":
                    pytest.fail("loop_detection._log_to_journal must not use to_thread")

    def test_loop_detection_does_not_import_asyncio(self) -> None:
        """loop_detection.py must not import asyncio (sync-only module)."""
        tree = _parse_module(_LOOP_DETECTION_SRC)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "asyncio", "loop_detection.py must not import asyncio"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "asyncio" not in node.module, (
                    "loop_detection.py must not import from asyncio"
                )


# ---------------------------------------------------------------------------
# AC6 — No new dependencies added
# ---------------------------------------------------------------------------


class TestFromAC_NoNewDependencies:  # noqa: N801
    """daemon.py must not introduce new third-party imports for async journal."""

    # Known third-party imports in daemon.py (pre-#541 baseline).
    _EXPECTED_THIRD_PARTY = frozenset(
        {
            "httpx",
            "logfire",
            "pydantic_ai",
            "rich",
        }
    )

    def test_daemon_no_new_third_party_imports(self) -> None:
        """daemon.py top-level imports must not exceed the known baseline set."""
        tree = _parse_module(_DAEMON_SRC)
        third_party: set[str] = set()
        stdlib_prefixes = {
            "__future__",
            "asyncio",
            "contextlib",
            "dataclasses",
            "json",
            "logging",
            "os",
            "random",
            "signal",
            "datetime",
            "pathlib",
            "typing",
            "types",
            "collections",
            "functools",
            "enum",
            "inspect",
            "sys",
            "io",
            "abc",
            "re",
            "warnings",
        }
        owlbear_prefixes = {"owlbear", "bearclaw"}

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in stdlib_prefixes and root not in owlbear_prefixes:
                        third_party.add(root)
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root not in stdlib_prefixes and root not in owlbear_prefixes:
                    third_party.add(root)

        unexpected = third_party - self._EXPECTED_THIRD_PARTY
        assert not unexpected, f"daemon.py imported unexpected third-party packages: {unexpected}"
