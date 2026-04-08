"""Failing tests for task #674: Fix stale packages/ path constants in root test files.

AC coverage:
  AC1: Grep all files under tests/ for packages/ path references (both string literals
       and Path objects) — verified by asserting no stale references remain.
  AC2: Every operational Path constant updated from packages/ → serve/ — verified by
       asserting / "serve" / division appears in each affected file after the fix.
  AC5: No remaining Path(... / "packages" / ...) constructions in tests/ — verified by
       the parametrised scan across all 14 affected files with path divisions, plus a
       dedicated check for the standalone "packages" sentinel in test_scratch_dir_enforcement.py.

Explicitly excluded from scan (per AC3 / architecture review):
  - test_rename_packages_601.py — intentionally tests that packages/ was removed
  - test_deny_src_writes_hook_589.py — "packages/" strings are test fixture data

AC3 (do not change comments / docstrings) and AC4 (tests pass) are not covered by
dedicated tests here: AC3 is a builder constraint checked during review; AC4 is
satisfied implicitly when the other ACs pass and the affected test files run cleanly.

All tests FAIL on current HEAD (packages/ path constants not yet updated).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_REPO_ROOT = _TESTS_DIR.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Matches Python Path /-division with "packages" or 'packages' as the operand.
# Captures: / "packages", / 'packages' (with optional inner whitespace).
# Does NOT match plain-text occurrences like "packages/foo/" inside docstrings,
# because those lack the leading Python / operator followed by a quoted token.
_STALE_DIVISION_RE = re.compile(r'/\s*["\']packages["\']')

# Matches Python Path /-division with "serve" or 'serve'.
_SERVE_DIVISION_RE = re.compile(r'/\s*["\']serve["\']')


def _source(filename: str) -> str:
    return (_TESTS_DIR / filename).read_text(encoding="utf-8")


def _runtime_stale_lines(source: str) -> list[str]:
    """Return code lines that contain a stale / "packages" Path division.

    Pure comment lines (stripped line starts with #) are excluded, consistent
    with AC3 which protects comments and docstrings from modification.
    """
    stale: list[str] = []
    for line in source.splitlines():
        if line.strip().startswith("#"):
            continue
        if _STALE_DIVISION_RE.search(line):
            stale.append(line.rstrip())
    return stale


def _has_serve_division(source: str) -> bool:
    """Return True if any non-comment line contains a / "serve" Path division."""
    for line in source.splitlines():
        if line.strip().startswith("#"):
            continue
        if _SERVE_DIVISION_RE.search(line):
            return True
    return False


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

# The 14 files that contain Python Path division expressions using "packages".
# (test_scratch_dir_enforcement.py uses a standalone "packages" string value —
# it is handled separately below.)
_FILES_WITH_PATH_DIVISION: list[str] = [
    "test_approve_memory_531.py",
    "test_approve_memory_585.py",
    "test_cleanup_tools_223.py",
    "test_knowledge_engine_extraction.py",
    "test_knowledge_foundation.py",
    "test_knowledge_intake_ingest_158.py",
    "test_knowledge_package_34.py",
    "test_knowledge_strictyaml_dep_308.py",
    "test_knowledge_vector_pipeline_32.py",
    "test_mcp_kanban_server.py",
    "test_memory_tools_525.py",
    "test_set_approval_state_529.py",
    "test_voice_package_scaffolding.py",
    "test_voice_workspace_package.py",
]


class TestFromAC_StalePackagesPathFix:
    """Task #674: verify all stale packages/ runtime Path constants are updated to serve/."""

    # ------------------------------------------------------------------
    # AC1 / AC5 — no stale runtime / "packages" / path divisions remain
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("filename", _FILES_WITH_PATH_DIVISION)
    def test_no_stale_path_division_in_file(self, filename: str) -> None:
        """AC1/AC5: / \"packages\" / path division must not exist in non-comment code lines."""
        stale = _runtime_stale_lines(_source(filename))
        assert stale == [], (
            f"{filename} still has stale packages/ path division expression(s) (AC5):\n"
            + "\n".join(f"  {ln}" for ln in stale)
        )

    # AC5: special case — standalone "packages" in test_scratch_dir_enforcement.py parametrize
    def test_scratch_dir_safe_paths_list_has_no_packages_entry(self) -> None:
        """AC5: standalone 'packages' entry in the safe-paths parametrize list must be removed."""
        source = _source("test_scratch_dir_enforcement.py")
        # The parametrize list contains bare string values like "packages" as path sentinels.
        # Detect lines that are *only* a quoted "packages" value (possibly with trailing comma).
        standalone_re = re.compile(r'^\s*["\']packages["\']\s*,?\s*$', re.MULTILINE)
        matches = standalone_re.findall(source)
        assert not matches, (
            "test_scratch_dir_enforcement.py still has 'packages' as a standalone "
            f"safe-path parametrize entry (AC5); found {len(matches)} occurrence(s) — "
            "update to 'serve'"
        )

    # ------------------------------------------------------------------
    # AC2 — serve/ substitution confirmed (/ "serve" / present after fix)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("filename", _FILES_WITH_PATH_DIVISION)
    def test_file_has_serve_path_division_after_fix(self, filename: str) -> None:
        """AC2: at least one / 'serve' / Path division must be present after the fix."""
        assert _has_serve_division(_source(filename)), (
            f'{filename} has no / "serve" / path division -- builder has not yet '
            "substituted 'packages' -> 'serve' in the runtime Path constants (AC2)"
        )

    # AC2: scratch_dir standalone entry updated to "serve"
    def test_scratch_dir_safe_paths_list_includes_serve_entry(self) -> None:
        """AC2: 'serve' must appear as a standalone safe-path entry replacing 'packages'."""
        source = _source("test_scratch_dir_enforcement.py")
        standalone_serve_re = re.compile(r'^\s*["\']serve["\']\s*,?\s*$', re.MULTILINE)
        assert standalone_serve_re.search(source), (
            "test_scratch_dir_enforcement.py: 'serve' is not in the safe-paths parametrize "
            "list — the 'packages' entry must be replaced with 'serve' (AC2)"
        )
