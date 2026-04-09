"""Failing tests for task #679: Add cleanup policy for .owlbear/scratch directory.

Tests verify the contract for `.owlbear/scripts/clean_scratch.py`:
- AC1: Files in scratch dir (including subdirs) with mtime > 30 days are deleted.
- AC2: Script is invokable via `python .owlbear/scripts/clean_scratch.py`.
- AC3: Protected files (.gitkeep, .instructions.md) are never deleted, regardless of age.
- AC4: --dry-run flag prints targets without deleting.
- AC5: Summary of deleted, preserved, and errors is printed to stdout.
- AC6: Not tested (gitignore state is a config fact, not a runtime behavior).

Tests use --scratch-dir to accept a test-controlled directory; the builder must
implement this optional flag so the script can be tested against temp directories.

All tests FAIL on current HEAD (script not yet created).
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "scripts" / "clean_scratch.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _age_ts(days: float) -> float:
    """Return a POSIX timestamp ``days`` days in the past."""
    return (datetime.now(tz=UTC) - timedelta(days=days)).timestamp()


def _set_mtime(path: Path, ts: float) -> None:
    os.utime(path, (ts, ts))


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run clean_scratch.py with the given CLI arguments."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture()
def scratch(tmp_path: Path) -> Path:
    """Temporary scratch directory populated per-test."""
    d = tmp_path / "scratch"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# AC2 — Script invokability
# ---------------------------------------------------------------------------


class TestFromAC_CleanScratchInvocable:
    """AC2: script must be invokable via `python .owlbear/scripts/clean_scratch.py`."""

    def test_script_file_exists_at_expected_path(self) -> None:
        assert _SCRIPT_PATH.exists(), (
            f"Script not found at {_SCRIPT_PATH}. Builder must create `.owlbear/scripts/clean_scratch.py`."
        )

    def test_script_exits_zero_on_dry_run(self, scratch: Path) -> None:
        """Script must exit 0 when invoked with --dry-run on an empty directory."""
        result = _run("--scratch-dir", str(scratch), "--dry-run")
        assert result.returncode == 0, f"Script exited {result.returncode}.\nstderr: {result.stderr}"

    def test_script_exits_zero_on_normal_run(self, scratch: Path) -> None:
        result = _run("--scratch-dir", str(scratch))
        assert result.returncode == 0, f"Script exited {result.returncode}.\nstderr: {result.stderr}"


# ---------------------------------------------------------------------------
# AC1 — Age-based deletion
# ---------------------------------------------------------------------------


class TestFromAC_CleanScratchAgeFiltering:
    """AC1: files with mtime > 30 days are deleted; recent files are preserved."""

    def test_file_older_than_30_days_is_deleted(self, scratch: Path) -> None:
        old = scratch / "stale.txt"
        old.write_text("old content")
        _set_mtime(old, _age_ts(31))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert not old.exists(), "File with 31-day mtime should have been deleted."

    def test_file_newer_than_30_days_is_preserved(self, scratch: Path) -> None:
        recent = scratch / "recent.txt"
        recent.write_text("content")
        _set_mtime(recent, _age_ts(1))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert recent.exists(), "File with 1-day mtime should NOT have been deleted."

    def test_files_in_subdirectory_are_included(self, scratch: Path) -> None:
        """AC1: 'including subdirectories' — old files in subdirs must also be deleted."""
        subdir = scratch / "subdir"
        subdir.mkdir()
        old = subdir / "nested_old.txt"
        old.write_text("old")
        _set_mtime(old, _age_ts(60))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert not old.exists(), "Old file in subdirectory should have been deleted."

    def test_recent_file_in_subdirectory_is_preserved(self, scratch: Path) -> None:
        subdir = scratch / "subdir"
        subdir.mkdir()
        recent = subdir / "nested_recent.txt"
        recent.write_text("recent")
        _set_mtime(recent, _age_ts(5))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert recent.exists(), "Recent file in subdirectory should NOT have been deleted."

    # --- Boundary conditions ---

    def test_file_exactly_30_days_old_is_preserved(self, scratch: Path) -> None:
        """Boundary: exactly 30 days old is NOT strictly older — must be preserved."""
        boundary = scratch / "boundary.txt"
        boundary.write_text("boundary")
        _set_mtime(boundary, _age_ts(30))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert boundary.exists(), "File exactly 30 days old should NOT be deleted."

    def test_file_30_days_and_1_second_old_is_deleted(self, scratch: Path) -> None:
        """Boundary: 30 days + 1 second is strictly older than 30 days — must be deleted."""
        just_over = scratch / "just_over.txt"
        just_over.write_text("just over")
        ts = _age_ts(30) - 1  # 1 second more than 30 days ago
        _set_mtime(just_over, ts)

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert not just_over.exists(), "File 30 days + 1 second old should have been deleted."

    def test_empty_scratch_dir_exits_zero(self, scratch: Path) -> None:
        """Edge: empty directory must not cause an error."""
        result = _run("--scratch-dir", str(scratch))
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# AC3 — Protected file exclusion
# ---------------------------------------------------------------------------


class TestFromAC_CleanScratchProtectedFiles:
    """AC3: .gitkeep and .instructions.md are never deleted, regardless of age."""

    def test_gitkeep_preserved_regardless_of_age(self, scratch: Path) -> None:
        gitkeep = scratch / ".gitkeep"
        gitkeep.write_text("")
        _set_mtime(gitkeep, _age_ts(365))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert gitkeep.exists(), ".gitkeep must never be deleted."

    def test_instructions_md_preserved_regardless_of_age(self, scratch: Path) -> None:
        instructions = scratch / ".instructions.md"
        instructions.write_text("# instructions")
        _set_mtime(instructions, _age_ts(365))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert instructions.exists(), ".instructions.md must never be deleted."

    def test_gitkeep_in_subdirectory_is_preserved(self, scratch: Path) -> None:
        """Edge: protected files in subdirectories must also be preserved."""
        subdir = scratch / "subdir"
        subdir.mkdir()
        gitkeep = subdir / ".gitkeep"
        gitkeep.write_text("")
        _set_mtime(gitkeep, _age_ts(365))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert gitkeep.exists(), ".gitkeep in subdirectory must never be deleted."

    def test_instructions_md_in_subdirectory_is_preserved(self, scratch: Path) -> None:
        subdir = scratch / "subdir"
        subdir.mkdir()
        instructions = subdir / ".instructions.md"
        instructions.write_text("# instructions")
        _set_mtime(instructions, _age_ts(365))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert instructions.exists(), ".instructions.md in subdirectory must never be deleted."

    def test_only_non_protected_old_files_deleted_when_mixed(self, scratch: Path) -> None:
        """AC3 + AC1 together: protected files stay, non-protected old files go."""
        old_file = scratch / "deleteme.txt"
        old_file.write_text("stale")
        _set_mtime(old_file, _age_ts(60))

        protected = scratch / ".gitkeep"
        protected.write_text("")
        _set_mtime(protected, _age_ts(60))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert not old_file.exists(), "Non-protected old file should be deleted."
        assert protected.exists(), ".gitkeep should still exist."


# ---------------------------------------------------------------------------
# AC4 — Dry-run flag
# ---------------------------------------------------------------------------


class TestFromAC_CleanScratchDryRun:
    """AC4: --dry-run prints what would be deleted without deleting anything."""

    def test_dry_run_does_not_delete_old_file(self, scratch: Path) -> None:
        old = scratch / "would_be_deleted.txt"
        old.write_text("old")
        _set_mtime(old, _age_ts(31))

        result = _run("--scratch-dir", str(scratch), "--dry-run")

        assert result.returncode == 0
        assert old.exists(), "Dry-run must NOT delete any files."

    def test_dry_run_prints_name_of_file_that_would_be_deleted(self, scratch: Path) -> None:
        old = scratch / "would_be_deleted.txt"
        old.write_text("old")
        _set_mtime(old, _age_ts(31))

        result = _run("--scratch-dir", str(scratch), "--dry-run")

        assert result.returncode == 0
        assert "would_be_deleted.txt" in result.stdout, (
            f"Dry-run must print the name of files that would be deleted. stdout: {result.stdout!r}"
        )

    def test_dry_run_does_not_print_recent_files_as_targets(self, scratch: Path) -> None:
        recent = scratch / "keep_me.txt"
        recent.write_text("recent")
        _set_mtime(recent, _age_ts(1))

        result = _run("--scratch-dir", str(scratch), "--dry-run")

        assert result.returncode == 0
        assert "keep_me.txt" not in result.stdout, "Dry-run must not list recent files as deletion targets."


# ---------------------------------------------------------------------------
# AC5 — Summary output
# ---------------------------------------------------------------------------


class TestFromAC_CleanScratchSummary:
    """AC5: script prints summary to stdout: count deleted, count preserved, any errors."""

    def test_summary_reports_deleted_count(self, scratch: Path) -> None:
        old = scratch / "stale.txt"
        old.write_text("old")
        _set_mtime(old, _age_ts(31))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        # Summary must mention 1 file deleted (or "deleted: 1" style)
        assert "1" in result.stdout, f"Summary must report 1 deleted file. stdout: {result.stdout!r}"

    def test_summary_reports_preserved_count(self, scratch: Path) -> None:
        recent = scratch / "recent.txt"
        recent.write_text("new content")
        _set_mtime(recent, _age_ts(1))

        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert "1" in result.stdout, f"Summary must report 1 preserved file. stdout: {result.stdout!r}"

    def test_summary_contains_deleted_keyword(self, scratch: Path) -> None:
        old = scratch / "a.txt"
        old.write_text("old")
        _set_mtime(old, _age_ts(60))

        result = _run("--scratch-dir", str(scratch))

        stdout_lower = result.stdout.lower()
        assert "deleted" in stdout_lower or "removed" in stdout_lower, (
            f"Summary must use 'deleted' or 'removed'. stdout: {result.stdout!r}"
        )

    def test_summary_contains_preserved_keyword(self, scratch: Path) -> None:
        recent = scratch / "keep.txt"
        recent.write_text("keep")
        _set_mtime(recent, _age_ts(1))

        result = _run("--scratch-dir", str(scratch))

        stdout_lower = result.stdout.lower()
        assert "preserved" in stdout_lower or "skipped" in stdout_lower or "kept" in stdout_lower, (
            f"Summary must use 'preserved', 'skipped', or 'kept'. stdout: {result.stdout!r}"
        )

    def test_summary_zero_counts_on_empty_dir(self, scratch: Path) -> None:
        result = _run("--scratch-dir", str(scratch))

        assert result.returncode == 0
        assert "0" in result.stdout, f"Summary must report 0 for empty dir. stdout: {result.stdout!r}"
