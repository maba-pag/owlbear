"""Tests for lazy-singleton OwlBearSettings migration (#536).

Verifies that all bearclaw/commands/ modules use ``get_settings()`` instead of
direct ``OwlBearSettings()`` instantiation, and that ``tests/conftest.py``
provides an autouse fixture that clears the ``get_settings`` cache between tests.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# The command modules that must be migrated per AC
# (auth:1, browser:2, chat:1, daemon:3, knowledge_source:1,
#  project:3, slack:1, usage:1 = 13 total calls across 8 modules)
# ---------------------------------------------------------------------------
COMMAND_MODULES = [
    "bearclaw.commands.auth",
    "bearclaw.commands.browser",
    "bearclaw.commands.chat",
    "bearclaw.commands.daemon",
    "bearclaw.commands.knowledge_source",
    "bearclaw.commands.project",
    "bearclaw.commands.slack",
    "bearclaw.commands.usage",
]


def _find_owlbearsettings_call_lines(source: str) -> list[int]:
    """Return line numbers where ``OwlBearSettings()`` is called directly."""
    tree = ast.parse(source)
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == "OwlBearSettings") or (
            isinstance(func, ast.Attribute) and func.attr == "OwlBearSettings"
        ):
            lines.append(node.lineno)
    return lines


# ── AC: All 13 OwlBearSettings() calls replaced with get_settings() ──────


class TestFromAC_CallSiteReplacement:
    """Each command module must import and use get_settings(), not OwlBearSettings()."""

    @pytest.mark.parametrize("module_name", COMMAND_MODULES)
    def test_module_imports_get_settings(self, module_name: str) -> None:
        """Command module must have ``get_settings`` in its namespace."""
        mod = importlib.import_module(module_name)
        assert hasattr(mod, "get_settings"), (
            f"{module_name} must import get_settings from owlbear.config"
        )

    @pytest.mark.parametrize("module_name", COMMAND_MODULES)
    def test_no_direct_owlbearsettings_instantiation(self, module_name: str) -> None:
        """No command module should directly call ``OwlBearSettings()``."""
        mod = importlib.import_module(module_name)
        source = inspect.getsource(mod)
        call_lines = _find_owlbearsettings_call_lines(source)
        assert not call_lines, (
            f"{module_name} still has direct OwlBearSettings() calls at lines {call_lines}"
        )


# ── AC: 32 test patch targets unified — no per-module OwlBearSettings ────


class TestFromAC_UnifiedPatchTarget:
    """Command modules must not re-export OwlBearSettings in their namespace.

    After migration, the only valid patch target is
    ``owlbear.config.OwlBearSettings``. Per-module patches
    (``bearclaw.commands.{mod}.OwlBearSettings``) must be removed.
    """

    @pytest.mark.parametrize("module_name", COMMAND_MODULES)
    def test_owlbearsettings_not_in_module_namespace(self, module_name: str) -> None:
        """``OwlBearSettings`` must not be importable from command modules."""
        mod = importlib.import_module(module_name)
        assert not hasattr(mod, "OwlBearSettings"), (
            f"{module_name} must not import OwlBearSettings — use get_settings() instead"
        )


# ── AC: Autouse fixture in tests/conftest.py calls cache_clear ───────────


class TestFromAC_CacheClearFixture:
    """``tests/conftest.py`` must have an autouse fixture clearing the cache."""

    def test_conftest_imports_get_settings(self) -> None:
        """conftest.py must import ``get_settings`` from ``owlbear.config``."""
        import tests.conftest as conftest_mod

        assert hasattr(conftest_mod, "get_settings"), (
            "conftest.py must import get_settings from owlbear.config"
        )

    def test_conftest_source_contains_cache_clear(self) -> None:
        """conftest.py source must contain ``get_settings.cache_clear()``."""
        conftest_path = Path(__file__).parent / "conftest.py"
        source = conftest_path.read_text(encoding="utf-8")
        assert "get_settings.cache_clear()" in source, (
            "conftest.py must call get_settings.cache_clear()"
        )

    def test_conftest_has_autouse_fixture_with_cache_clear(self) -> None:
        """An ``@pytest.fixture(autouse=True)`` in conftest.py must call cache_clear."""
        conftest_path = Path(__file__).parent / "conftest.py"
        source = conftest_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        found = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Check for autouse=True in decorator
            has_autouse = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if (
                            kw.arg == "autouse"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True
                        ):
                            has_autouse = True
            if not has_autouse:
                continue
            # Check body for cache_clear attribute access
            func_source = ast.get_source_segment(source, node) or ""
            if "cache_clear" in func_source:
                found = True
                break

        assert found, (
            "conftest.py must have an autouse fixture that calls get_settings.cache_clear()"
        )


# ── AC: 32 test patch targets use owlbear.config.OwlBearSettings, not per-module ──

# Pattern that matches old-style per-module patch targets:
#   "bearclaw.commands.<module>.OwlBearSettings"
_STALE_PATCH_RE = re.compile(r"bearclaw\.commands\.\w+\.OwlBearSettings")

# Test files to audit (all tests/ *.py files except this one)
_TESTS_DIR = Path(__file__).parent


class TestFromAC_TestFilePatchTargets:
    """All test files must use ``owlbear.config.OwlBearSettings`` as the patch
    target — no per-module ``bearclaw.commands.{mod}.OwlBearSettings`` strings
    remain anywhere in the test suite.

    AC line: "32 test patch targets updated from bearclaw.commands.{module}.OwlBearSettings
    to owlbear.config.OwlBearSettings"
    """

    def _collect_stale_targets(self) -> list[tuple[str, int, str]]:
        """Return (relative_path, lineno, line_text) for every stale patch target."""
        hits: list[tuple[str, int, str]] = []
        for test_file in sorted(_TESTS_DIR.glob("*.py")):
            if test_file.name == Path(__file__).name:
                continue  # skip this file — the docstring references the pattern
            lines = test_file.read_text(encoding="utf-8").splitlines()
            for lineno, line in enumerate(lines, start=1):
                if _STALE_PATCH_RE.search(line):
                    hits.append((test_file.name, lineno, line.strip()))
        return hits

    def test_no_stale_per_module_patch_targets_in_test_suite(self) -> None:
        """No test file may patch ``bearclaw.commands.*.OwlBearSettings``.

        After migration the only valid patch target is
        ``owlbear.config.OwlBearSettings``.  Any remaining per-module targets
        are inert because the command modules no longer import OwlBearSettings
        at module scope.
        """
        stale = self._collect_stale_targets()
        assert not stale, (
            "Stale per-module OwlBearSettings patch targets found "
            "(must be changed to 'owlbear.config.OwlBearSettings'):\n"
            + "\n".join(f"  {f}:{n}  {line}" for f, n, line in stale)
        )

    def test_test_client_cleanup_uses_correct_patch_target(self) -> None:
        """test_client_cleanup.py must not patch bearclaw.commands.chat.OwlBearSettings.

        Regression test for the specific stale target identified in audit AC3.
        """
        target_file = _TESTS_DIR / "test_client_cleanup.py"
        source = target_file.read_text(encoding="utf-8")
        assert "bearclaw.commands.chat.OwlBearSettings" not in source, (
            "test_client_cleanup.py still patches bearclaw.commands.chat.OwlBearSettings — "
            "update to 'owlbear.config.OwlBearSettings'"
        )
