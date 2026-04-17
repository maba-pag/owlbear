"""Failing tests for task #750: Verify clean build after voice I/O removal.

AC coverage (TDD RED phase — targeted failing tests for remaining cleanup work):
  AC3: No orphan owlbear.voice / owlbear_voice import statements in serve/ or tests/
  AC4: serve/voice/ does not exist
  AC5: serve/orchestrator/src/owlbear/voice/ does not exist
  AC6: No test_voice_*.py files exist in tests/
  AC7: pyproject.toml contains no voice references in ruff sources or coverage source_pkgs
  AC8: README.md contains no serve/voice/ reference

CRITICAL (regression guard):
  share/ domain opinion agents (ideation-architect.agent.md, ideation-critic.agent.md, etc.)
  MUST still exist after removal — these are NOT part of the voice I/O addon.

Note: AC1 (pytest suite passes) and AC2 (ruff passes workspace-wide) are verified
by running the quality suite directly — they are not testable from within pytest.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SERVE_DIR = ROOT / "serve"
TESTS_DIR = ROOT / "tests"
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"

# Matches only actual Python import statements (anchored at line start, optional indent).
# Does NOT match string literals, comments, or regex patterns that contain the substrings.
_VOICE_IMPORT_PATTERN = re.compile(r"^\s*(?:from owlbear[._]voice|import owlbear[._]voice)")

_THIS_FILE = Path(__file__).name


# ---------------------------------------------------------------------------
# AC4: serve/voice/ directory removed
# ---------------------------------------------------------------------------


class TestFromAC_VoiceDirectoryRemoval:
    """AC4 + AC5: voice I/O directories must be absent after deletion."""

    def test_serve_voice_dir_does_not_exist(self) -> None:
        """serve/voice/ must be absent after voice I/O addon removal."""
        assert not (SERVE_DIR / "voice").exists(), "serve/voice/ still exists — builder must delete this directory"

    def test_orchestrator_voice_subdir_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/ must be absent after removal."""
        path = SERVE_DIR / "orchestrator" / "src" / "owlbear" / "voice"
        assert not path.exists(), (
            "serve/orchestrator/src/owlbear/voice/ still exists — builder must delete this directory"
        )


# ---------------------------------------------------------------------------
# AC6: No test_voice_*.py files in tests/
# ---------------------------------------------------------------------------


class TestFromAC_VoiceTestFilesRemoval:
    """AC6: test_voice_*.py files must be absent from tests/ after removal."""

    def test_no_test_voice_files_in_tests_dir(self) -> None:
        """No test_voice_*.py files may remain in tests/ after removal."""
        voice_test_files = sorted(TESTS_DIR.glob("test_voice_*.py"))
        assert voice_test_files == [], (
            f"test_voice_*.py files still exist in tests/: {[f.name for f in voice_test_files]}"
        )


# ---------------------------------------------------------------------------
# AC3: No orphan owlbear.voice / owlbear_voice imports in serve/ or tests/
# ---------------------------------------------------------------------------


class TestFromAC_OrphanImportCleanup:
    """AC3: Actual import statements for owlbear.voice or owlbear_voice must
    be absent in serve/ and tests/. String literals, comments, regex patterns,
    and docstrings that mention the names are not flagged.
    """

    def _collect_matches(self, search_root: Path) -> list[str]:
        matches: list[str] = []
        for py_file in search_root.rglob("*.py"):
            # Skip this verification file itself (its content cannot self-violate).
            if py_file.name == _THIS_FILE:
                continue
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if _VOICE_IMPORT_PATTERN.match(line):
                    matches.append(f"{py_file.relative_to(ROOT)}:{lineno}: {line.strip()}")
        return matches

    def test_no_voice_imports_in_serve(self) -> None:
        """No owlbear.voice or owlbear_voice import statements may remain in serve/."""
        matches = self._collect_matches(SERVE_DIR)
        assert matches == [], "Orphan voice import statements found in serve/:\n" + "\n".join(matches)

    def test_no_voice_imports_in_tests(self) -> None:
        """No owlbear.voice or owlbear_voice import statements may remain in tests/."""
        matches = self._collect_matches(TESTS_DIR)
        assert matches == [], "Orphan voice import statements found in tests/:\n" + "\n".join(matches)

    def test_no_voice_references_in_serve_toml_files(self) -> None:
        """No owlbear_voice or owlbear-voice references in any serve/ pyproject.toml files."""
        matches: list[str] = []
        for toml_file in SERVE_DIR.rglob("pyproject.toml"):
            content = toml_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if re.search(r"owlbear[_-]voice", line):
                    matches.append(f"{toml_file.relative_to(ROOT)}:{lineno}: {line.strip()}")
        assert matches == [], "Voice references remain in serve/ pyproject.toml files:\n" + "\n".join(matches)


# ---------------------------------------------------------------------------
# AC7: pyproject.toml — no voice in ruff.src or coverage.source_pkgs
# ---------------------------------------------------------------------------


class TestFromAC_PyprojectTomlCleanup:
    """AC7: Root pyproject.toml must not reference voice in ruff or coverage config."""

    def test_ruff_src_no_voice_entry(self) -> None:
        """serve/voice/src must be absent from [tool.ruff] src list."""
        content = PYPROJECT.read_text(encoding="utf-8")
        assert "serve/voice/src" not in content, (
            "pyproject.toml still has 'serve/voice/src' in ruff src — builder must remove it"
        )

    def test_coverage_source_pkgs_no_owlbear_voice(self) -> None:
        """owlbear_voice must be absent from [tool.coverage.run] source_pkgs."""
        content = PYPROJECT.read_text(encoding="utf-8")
        assert "owlbear_voice" not in content, (
            "pyproject.toml still lists 'owlbear_voice' in coverage source_pkgs — builder must remove it"
        )


# ---------------------------------------------------------------------------
# AC8: README.md — no serve/voice/ reference
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeCleanup:
    """AC8: README.md must not reference serve/voice/ after removal."""

    def test_readme_no_serve_voice_reference(self) -> None:
        """serve/voice/ path reference must be absent from README.md."""
        content = README.read_text(encoding="utf-8")
        assert "serve/voice/" not in content, "README.md still references serve/voice/ — builder must remove that entry"


# ---------------------------------------------------------------------------
# CRITICAL (builder reminder — not testable in RED phase):
# share/agents/ideation-architect.agent.md, share/agents/ideation-critic.agent.md,
# and all other share/ domain opinion agents MUST NOT be deleted.
# Only serve/voice/ (the I/O hardware addon) is being removed.
# The builder must manually verify share/ is untouched after performing the cleanup.
# ---------------------------------------------------------------------------
