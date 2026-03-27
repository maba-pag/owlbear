"""Failing tests for task #88: Enforce scratch dir for agent temp files.

Covers:
  - AC-1: 9 stale root-level files deleted
  - AC-2: docs/scratch/.instructions.md created with placement + cleanup rules
  - AC-3: .gitignore has !docs/scratch/.instructions.md exception
  - AC-4: .gitignore adds patterns for uncovered root-level temp files;
          git check-ignore returns a match for each of the 8 previously uncovered stale names
  - AC-5: Invariant guards — key project files must still exist (pass by design;
          fail if builder accidentally deletes them)

All AC-1 through AC-4 tests fail on current HEAD: the 9 stale files exist, the
.instructions.md is absent, and .gitignore lacks *_err.txt, *_out.txt,
/kanban_show_*.txt, /tasklist*.json, /task-list*.json patterns.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GITIGNORE = ROOT / ".gitignore"
SCRATCH_INSTRUCTIONS = ROOT / "docs" / "scratch" / ".instructions.md"


# ---------------------------------------------------------------------------
# AC-1: Stale root-level files deleted
# ---------------------------------------------------------------------------


class TestFromAC_StaleRootFilesDeleted:
    """AC-1: All 9 stale root-level artifacts must be deleted."""

    @pytest.mark.parametrize(
        "filename",
        [
            "builder-notes-task6.md",
            "kanban_show_30.txt",
            "kanban_show_57.txt",
            "pytest_err.txt",
            "pytest_out.txt",
            "pytest_output.txt",
            "task-list.json",
            "tasklist.json",
            "tasklist2.json",
        ],
    )
    def test_stale_file_does_not_exist(self, filename: str) -> None:
        """Each stale root-level artifact must have been deleted."""
        assert not (ROOT / filename).exists(), (
            f"{filename!r} still exists at the project root — it must be deleted (AC-1)"
        )


# ---------------------------------------------------------------------------
# AC-2: docs/scratch/.instructions.md created with required content
# ---------------------------------------------------------------------------


class TestFromAC_ScratchInstructionsFile:
    """AC-2: docs/scratch/.instructions.md must exist with placement and cleanup rules."""

    def _read_content(self) -> str:
        """Read the instructions file; fail clearly if it does not exist yet."""
        if not SCRATCH_INSTRUCTIONS.exists():
            pytest.fail(
                "docs/scratch/.instructions.md does not exist — builder must create it (AC-2)"
            )
        return SCRATCH_INSTRUCTIONS.read_text(encoding="utf-8")

    def test_file_exists(self) -> None:
        """docs/scratch/.instructions.md must be present."""
        assert SCRATCH_INSTRUCTIONS.exists(), (
            "docs/scratch/.instructions.md not found (AC-2)"
        )

    def test_contains_placement_rule(self) -> None:
        """File must document: agent temp/debug output goes to docs/scratch/{task-id}-{desc}.{ext}."""
        content = self._read_content()
        assert "docs/scratch/" in content, (
            "Placement rule referencing docs/scratch/ not found (AC-2a)"
        )
        # Naming pattern must mention task-id
        assert re.search(r"task.?id", content, re.IGNORECASE), (
            "Placement rule must reference task-id naming convention (AC-2a)"
        )

    def test_contains_cleanup_rule(self) -> None:
        """File must document: delete docs/scratch/{task-id}-* before marking task done."""
        content = self._read_content()
        has_delete = bool(re.search(r"\bdelete\b|\bremove\b", content, re.IGNORECASE))
        has_done = bool(re.search(r"\bdone\b|\bmark(ing)?\b", content, re.IGNORECASE))
        assert has_delete, "Cleanup rule must mention deletion (AC-2b)"
        assert has_done, "Cleanup rule must reference 'done' gate / marking done (AC-2b)"

    def test_contains_at_least_two_naming_examples(self) -> None:
        """File must contain at least two naming convention examples.

        Expected form: ``88-debug-output.txt``, ``42-api-response.json``, or
        ``{task-id}-{desc}.{ext}``.
        """
        content = self._read_content()
        # Match numeric or placeholder-prefixed filenames: 88-something.ext or {task-id}-something.ext
        example_pattern = re.compile(
            r"(?:\d+|\{task-id\})[_\-][\w{}\-]+\.\w{2,5}"
        )
        examples = example_pattern.findall(content)
        assert len(set(examples)) >= 2, (
            f"Expected >= 2 naming examples, found {len(set(examples))}: {examples!r} (AC-2c)"
        )


# ---------------------------------------------------------------------------
# AC-3: .gitignore exception for docs/scratch/.instructions.md
# ---------------------------------------------------------------------------


class TestFromAC_GitignoreException:
    """AC-3: .gitignore must allow tracking of docs/scratch/.instructions.md."""

    def test_gitignore_has_instructions_exception(self) -> None:
        """!docs/scratch/.instructions.md must appear in .gitignore."""
        content = GITIGNORE.read_text(encoding="utf-8")
        assert "!docs/scratch/.instructions.md" in content, (
            "!docs/scratch/.instructions.md exception not found in .gitignore (AC-3). "
            "Without this, the new file is hidden by the docs/scratch/ ignore rule."
        )


# ---------------------------------------------------------------------------
# AC-4: .gitignore patterns prevent root-level temp recurrence
# ---------------------------------------------------------------------------


class TestFromAC_GitignorePatterns:
    """AC-4: .gitignore must add *_err.txt, *_out.txt, and root-scoped stale patterns."""

    def _gitignore_lines(self) -> set[str]:
        return {line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()}

    def test_gitignore_has_err_txt_pattern(self) -> None:
        """*_err.txt must be in .gitignore (parallel to existing *_output.txt)."""
        lines = self._gitignore_lines()
        assert "*_err.txt" in lines, "*_err.txt pattern not found in .gitignore (AC-4)"

    def test_gitignore_has_out_txt_pattern(self) -> None:
        """*_out.txt must be in .gitignore (parallel to existing *_output.txt)."""
        lines = self._gitignore_lines()
        assert "*_out.txt" in lines, "*_out.txt pattern not found in .gitignore (AC-4)"

    def test_gitignore_has_kanban_show_pattern(self) -> None:
        """Root-scoped kanban_show_*.txt pattern must be in .gitignore."""
        lines = self._gitignore_lines()
        assert "/kanban_show_*.txt" in lines or "kanban_show_*.txt" in lines, (
            "kanban_show_*.txt (or /kanban_show_*.txt) pattern not found in .gitignore (AC-4)"
        )

    def test_gitignore_has_tasklist_json_pattern(self) -> None:
        """Root-scoped tasklist*.json pattern must be in .gitignore."""
        content = GITIGNORE.read_text(encoding="utf-8")
        assert re.search(r"/?tasklist\*\.json", content), (
            "tasklist*.json pattern not found in .gitignore (AC-4)"
        )

    def test_gitignore_has_task_list_json_pattern(self) -> None:
        """Root-scoped task-list*.json pattern must be in .gitignore."""
        content = GITIGNORE.read_text(encoding="utf-8")
        assert re.search(r"/?task-list\*\.json", content), (
            "task-list*.json pattern not found in .gitignore (AC-4)"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            # pytest_output.txt excluded — already matched by existing *_output.txt pattern
            "builder-notes-task6.md",
            "kanban_show_30.txt",
            "kanban_show_57.txt",
            "pytest_err.txt",
            "pytest_out.txt",
            "task-list.json",
            "tasklist.json",
            "tasklist2.json",
        ],
    )
    def test_git_check_ignore_covers_stale_file(self, filename: str) -> None:
        """git check-ignore must match each stale filename not yet covered by .gitignore."""
        result = subprocess.run(
            ["git", "check-ignore", "-v", filename],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"git check-ignore returned exit {result.returncode} for {filename!r} — "
            f"no .gitignore pattern covers it (AC-4).\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# AC-5: Invariant guards — key project files must still exist
# ---------------------------------------------------------------------------


class TestFromAC_SafeFilesUnchanged:
    """AC-5: Essential project files must not be deleted by the builder.

    These tests pass on current HEAD and serve as regression guards against
    accidental deletion during the cleanup operation.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "README.md",
            "SECURITY.md",
            "pyproject.toml",
            ".gitignore",
            "Owlbear.code-profile",
            "kanban/config.yml",
            "docs/research",
            "packages",
            "agents",
            "skills",
            "instructions",
        ],
    )
    def test_safe_path_still_exists(self, path: str) -> None:
        """Essential project paths must not be deleted during the cleanup."""
        assert (ROOT / path).exists(), (
            f"{path!r} must not be deleted or moved by the builder (AC-5)"
        )
