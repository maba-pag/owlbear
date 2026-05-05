"""Failing tests for #1310: git integration — commit batch semantics for mcp-memory.

AC coverage:
  AC1 (td:1): save_memory does NOT create a git commit (file exists uncommitted)
  AC2 (td:2): curation batch: multiple curate/delete ops produce single batch commit
  AC3 (td:2): review batch: multiple approve/curate/delete ops produce single batch commit
  AC4 (td:2): hard-deleted (pending) files never appear in git history
  AC5 (td:1): soft-deleted entries are included in batch commit
  AC6 (td:1): batch commit message matches expected format
  AC7 (td:0): all tests fail (RED state) — no test needed, guaranteed by ImportError

Interface strategy:
  commit_batch(memory_dir, *, session_type) does not exist in
  owlbear_mcp_memory.git yet.  The deferred _commit_batch() helper imports it
  at call time → ImportError on every test that invokes it.  For AC1 the same
  import is performed inline, ensuring the test fails in RED too.

  Expected signature: commit_batch(memory_dir: Path, *, session_type: str) -> str
  Returns commit SHA on success, "" when there is nothing to commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TS = "2026-05-05T10:00:00Z"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-446655{n:06d}"


def _make_entry(**overrides: object) -> MemoryEntry:
    """Return a valid MemoryEntry; defaults to pending state."""
    defaults: dict[str, object] = {
        "id": _uuid(1),
        "title": "Test entry",
        "categories": ["domain-knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "content": "Entry body.",
        "scope_agents": ["builder"],
        "source_agent": "builder",
        "created_at": _TS,
        "updated_at": _TS,
        "approved_at": None,
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _git(*args: str, cwd: Path) -> str:
    """Run a git command in cwd and return stripped stdout."""
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
    )
    return result.stdout.strip()


def _commit_count(repo_dir: Path) -> int:
    """Return total number of commits reachable from HEAD."""
    return int(_git("rev-list", "--count", "HEAD", cwd=repo_dir))


def _commit_message(repo_dir: Path) -> str:
    """Return the subject line of the most recent commit."""
    return _git("log", "-1", "--pretty=format:%s", cwd=repo_dir)


def _all_committed_filenames(repo_dir: Path) -> set[str]:
    """Return the set of all filenames ever committed (any branch, any commit)."""
    raw = _git(
        "log", "--all", "--name-only", "--pretty=format:", cwd=repo_dir
    )
    return {line.strip() for line in raw.splitlines() if line.strip()}


def _commit_batch(memory_dir: Path, *, session_type: str) -> str:
    """Deferred import of commit_batch — raises ImportError until implemented."""
    from owlbear_mcp_memory.git import commit_batch  # noqa: PLC0415

    return commit_batch(memory_dir, session_type=session_type)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Return tmp_path initialised as a git repo with one empty initial commit."""
    subprocess.run(  # noqa: S603
        ["git", "init", str(tmp_path)],  # noqa: S607
        capture_output=True,
        check=True,
    )
    for key, val in [
        ("user.email", "test@owlbear.test"),
        ("user.name", "OwlBear Test"),
    ]:
        subprocess.run(  # noqa: S603
            ["git", "config", key, val],  # noqa: S607
            capture_output=True,
            check=True,
            cwd=tmp_path,
        )
    subprocess.run(  # noqa: S603
        ["git", "commit", "--allow-empty", "-m", "chore: initial (test)"],  # noqa: S607
        capture_output=True,
        check=True,
        cwd=tmp_path,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# AC1 (td:1): save_memory does NOT create a git commit
# ---------------------------------------------------------------------------


class TestFromAC_SaveNoCommit:
    """AC1: Writing a pending entry to disk must not create a git commit."""

    def test_save_does_not_commit(self, git_repo: Path) -> None:
        """After MemoryEngine.write with a pending entry, commit count stays at 1.

        The deferred import of commit_batch ensures this test fails in RED when
        the owlbear_mcp_memory.git module does not exist.
        """
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        engine.write(_make_entry(id=_uuid(1), state="pending"))

        # This import guarantees RED: module does not exist yet.
        from owlbear_mcp_memory.git import commit_batch  # noqa: PLC0415, F401

        # Only the initial empty commit must exist — no automatic commit was made.
        assert _commit_count(git_repo) == 1


# ---------------------------------------------------------------------------
# AC2 (td:2): curation batch — multiple operations produce a single commit
# ---------------------------------------------------------------------------


class TestFromAC_CurationBatch:
    """AC2: Multiple curation-phase operations are batched into one git commit."""

    def test_multiple_curated_produce_single_commit(self, git_repo: Path) -> None:
        """Three curated entries → commit_batch("curation") → exactly one new commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        for i in range(1, 4):
            engine.write(
                _make_entry(id=_uuid(i), state="curated", title=f"Entry {i}")
            )

        before = _commit_count(git_repo)
        _commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert after - before == 1

    def test_curation_batch_no_extra_commit_when_nothing_changed(
        self, git_repo: Path
    ) -> None:
        """A second commit_batch call with nothing new to stage returns "" (no commit)."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        engine.write(_make_entry(id=_uuid(1), state="curated", title="Once"))

        _commit_batch(memory_dir, session_type="curation")
        before = _commit_count(git_repo)
        result = _commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert after == before  # no extra commit when nothing changed
        assert result == ""


# ---------------------------------------------------------------------------
# AC3 (td:2): review batch — multiple operations produce a single commit
# ---------------------------------------------------------------------------


class TestFromAC_ReviewBatch:
    """AC3: Multiple review-phase operations are batched into one git commit."""

    def test_mixed_review_operations_produce_single_commit(
        self, git_repo: Path
    ) -> None:
        """Two approved + one curated → commit_batch("review") → exactly one new commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        for i in range(1, 3):
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    state="approved",
                    title=f"Approved {i}",
                    approved_at=_TS,
                )
            )
        engine.write(_make_entry(id=_uuid(3), state="curated", title="Curated"))

        before = _commit_count(git_repo)
        _commit_batch(memory_dir, session_type="review")
        after = _commit_count(git_repo)

        assert after - before == 1

    def test_review_batch_leaves_clean_working_tree(self, git_repo: Path) -> None:
        """After commit_batch("review") with only non-pending entries, working tree is clean."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        engine.write(
            _make_entry(
                id=_uuid(1), state="approved", title="Approved", approved_at=_TS
            )
        )
        engine.write(_make_entry(id=_uuid(2), state="curated", title="Curated"))

        _commit_batch(memory_dir, session_type="review")

        # All staged files were committed; no modifications or untracked non-pending files
        result = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=git_repo,
            stdin=subprocess.DEVNULL,
        )
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# AC4 (td:2): hard-deleted pending files never appear in git history
# ---------------------------------------------------------------------------


class TestFromAC_HardDeletedNeverInHistory:
    """AC4: Pending entries that are hard-deleted must never enter git history."""

    def test_hard_deleted_pending_absent_from_git_log(
        self, git_repo: Path
    ) -> None:
        """Create pending entry, hard-delete it, run commit_batch → filename absent from log."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        ephemeral = _make_entry(id=_uuid(1), state="pending", title="Ephemeral")
        written_path = engine.write(ephemeral)
        filename = written_path.name

        engine.delete(ephemeral.id)  # hard-delete before any commit

        # Give commit_batch something non-pending to stage
        engine.write(_make_entry(id=_uuid(2), state="curated", title="Keeper"))
        _commit_batch(memory_dir, session_type="curation")

        committed = _all_committed_filenames(git_repo)
        # The deleted pending filename must not appear anywhere in history
        assert not any(filename in path for path in committed)

    def test_pending_file_on_disk_not_staged_by_commit_batch(
        self, git_repo: Path
    ) -> None:
        """A pending file that still exists on disk is NOT staged by commit_batch."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        pending = _make_entry(id=_uuid(1), state="pending", title="Pending Only")
        written_path = engine.write(pending)
        filename = written_path.name

        _commit_batch(memory_dir, session_type="curation")

        committed = _all_committed_filenames(git_repo)
        assert not any(filename in path for path in committed)


# ---------------------------------------------------------------------------
# AC5 (td:1): soft-deleted entries are included in the batch commit
# ---------------------------------------------------------------------------


class TestFromAC_SoftDeletedInBatch:
    """AC5: Entries with state=deleted (soft-delete) are staged and committed."""

    def test_soft_deleted_entry_included_in_commit(self, git_repo: Path) -> None:
        """An entry rewritten with state=deleted appears in the next batch commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        # Write curated, then rewrite as deleted to simulate soft-delete
        engine.write(_make_entry(id=_uuid(1), state="curated", title="Will Delete"))
        deleted_path = engine.write(
            _make_entry(id=_uuid(1), state="deleted", title="Will Delete")
        )
        filename = deleted_path.name

        before = _commit_count(git_repo)
        _commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert after - before == 1  # soft-delete triggered a commit
        committed = _all_committed_filenames(git_repo)
        assert any(filename in path for path in committed)


# ---------------------------------------------------------------------------
# AC6 (td:1): commit message matches exact project format
# ---------------------------------------------------------------------------


class TestFromAC_CommitMessageFormat:
    """AC6: Batch commit messages follow the project commit convention."""

    def test_curation_batch_commit_message(self, git_repo: Path) -> None:
        """Curation batch produces: 'chore: memory curation batch (mcp-memory, curator)'."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        engine.write(_make_entry(id=_uuid(1), state="curated", title="Entry"))

        _commit_batch(memory_dir, session_type="curation")

        assert _commit_message(git_repo) == (
            "chore: memory curation batch (mcp-memory, curator)"
        )

    def test_review_batch_commit_message(self, git_repo: Path) -> None:
        """Review batch produces: 'chore: memory review batch (mcp-memory, reviewer)'."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        engine.write(
            _make_entry(
                id=_uuid(1), state="approved", title="Approved", approved_at=_TS
            )
        )

        _commit_batch(memory_dir, session_type="review")

        assert _commit_message(git_repo) == (
            "chore: memory review batch (mcp-memory, reviewer)"
        )


# ---------------------------------------------------------------------------
# Retry: Revised AC2 (td:1) — save_memory discriminator: file exists AND untracked
# ---------------------------------------------------------------------------


class TestFromAC_SaveNoCommit_FilesystemProof:
    """Revised AC2: save_memory places file on disk without git-adding it.

    Strengthens the existing commit-count assertion by proving the file is both
    written to disk and visible as untracked (not staged) in git status.
    """

    def test_save_writes_file_as_untracked(self, git_repo: Path) -> None:
        """engine.write writes the pending file to disk without staging it.

        Discriminator: the file must exist on disk AND appear as '??' (untracked)
        in git status --porcelain — not as 'A' (staged) or 'M' (modified staged).
        """
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        written_path = engine.write(_make_entry(id=_uuid(10), state="pending"))

        assert written_path.exists(), "write() must create the file on disk"

        # Use --untracked-files=all so individual files inside new dirs are listed
        status_output = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain", "--untracked-files=all"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=git_repo,
            stdin=subprocess.DEVNULL,
        ).stdout

        filename = written_path.name
        matching = [line for line in status_output.splitlines() if filename in line]
        assert len(matching) == 1, f"{filename} not found in git status output"
        assert matching[0].startswith("??"), (
            f"Expected '??' (untracked) prefix, got: {matching[0]!r}"
        )


# ---------------------------------------------------------------------------
# Retry: Revised AC3 (td:2) — curation batch with curated AND soft-deleted entries
# ---------------------------------------------------------------------------


class TestFromAC_CurationBatch_MixedTypes:
    """Revised AC3: curation batch with both curated and soft-deleted entries → single commit.

    The original AC2 test only exercised multiple curated entries.  This class
    adds the mixed-type scenario the reviewer identified as missing.
    """

    def test_curation_batch_with_curated_and_deleted(self, git_repo: Path) -> None:
        """One curated entry + one soft-deleted entry → exactly one new commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        engine.write(_make_entry(id=_uuid(1), state="curated", title="Keep This"))
        engine.write(_make_entry(id=_uuid(2), state="deleted", title="Mark Deleted"))

        before = _commit_count(git_repo)
        _commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert after - before == 1, "Mixed curated+deleted curation must produce exactly one commit"


# ---------------------------------------------------------------------------
# Retry: Revised AC4 (td:2) — review batch with approved, curated AND soft-deleted entries
# ---------------------------------------------------------------------------


class TestFromAC_ReviewBatch_MixedTypes:
    """Revised AC4: review batch with approved, curated, and soft-deleted → single commit.

    The original AC3 tests only covered approved+curated combinations.  This class
    adds the three-way mixed scenario the reviewer identified as missing.
    """

    def test_review_batch_with_approved_curated_and_deleted(
        self, git_repo: Path
    ) -> None:
        """One approved + one curated + one soft-deleted → exactly one new commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        engine.write(
            _make_entry(
                id=_uuid(1), state="approved", title="Approved", approved_at=_TS
            )
        )
        engine.write(_make_entry(id=_uuid(2), state="curated", title="Curated"))
        engine.write(_make_entry(id=_uuid(3), state="deleted", title="Soft Deleted"))

        before = _commit_count(git_repo)
        _commit_batch(memory_dir, session_type="review")
        after = _commit_count(git_repo)

        assert after - before == 1, (
            "Review batch with approved+curated+deleted must produce exactly one commit"
        )


# ---------------------------------------------------------------------------
# Retry: Revised AC6 (td:1) — soft-deleted file content assertion
# ---------------------------------------------------------------------------


class TestFromAC_SoftDeletedContent:
    """Revised AC6: committed soft-deleted file must contain 'state: deleted' in frontmatter.

    The original AC5 test only checked that the filename appeared in git history.
    This class adds the content-level discriminator the reviewer required.
    """

    def test_soft_deleted_content_has_deleted_state_in_commit(
        self, git_repo: Path
    ) -> None:
        """The committed version of a soft-deleted file has 'state: deleted' in frontmatter."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)

        deleted_path = engine.write(
            _make_entry(id=_uuid(20), state="deleted", title="Soft Deleted Content")
        )
        rel_path = str(deleted_path.relative_to(git_repo))

        _commit_batch(memory_dir, session_type="curation")

        committed_content = _git("show", f"HEAD:{rel_path}", cwd=git_repo)
        assert "state: deleted" in committed_content, (
            f"Committed file must contain 'state: deleted' in frontmatter, got:\n{committed_content}"
        )


# ---------------------------------------------------------------------------
# Retry: Revised AC8 (td:2) — scoped staging regression
# ---------------------------------------------------------------------------


class TestFromAC_ScopedStagingRegression:
    """Revised AC8: commit_batch must only commit the memory paths it staged.

    A pre-staged unrelated file must NOT be swept into the memory batch commit.
    This test fails against the current implementation because git.py uses
    'git commit -m <msg>' without '-- <paths>', causing it to commit all
    currently-staged files regardless of whether they belong to the memory store.
    """

    def test_commit_batch_does_not_sweep_unrelated_staged_file(
        self, git_repo: Path
    ) -> None:
        """Pre-staged unrelated file is excluded from the memory batch commit.

        Setup: stage an unrelated file, then call commit_batch with a curated entry.
        Expected: memory batch commit contains only the memory file; unrelated.txt
        remains staged (not committed) so it can be included in a separate commit.
        """
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        engine.write(_make_entry(id=_uuid(1), state="curated", title="Memory Entry"))

        # Stage an unrelated file before calling commit_batch
        unrelated = git_repo / "unrelated.txt"
        unrelated.write_text("unrelated content\n")
        subprocess.run(  # noqa: S603
            ["git", "add", "--", "unrelated.txt"],  # noqa: S607
            capture_output=True,
            check=True,
            cwd=git_repo,
            stdin=subprocess.DEVNULL,
        )

        _commit_batch(memory_dir, session_type="curation")

        # unrelated.txt must NOT appear in the files changed by the last commit
        committed_files = _git(
            "diff-tree", "--no-commit-id", "-r", "--name-only", "HEAD",
            cwd=git_repo,
        ).splitlines()
        assert "unrelated.txt" not in committed_files, (
            "commit_batch must not sweep pre-staged unrelated files into the memory commit"
        )

        # unrelated.txt must still be staged (indexed as 'A' — new file)
        status_lines = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=git_repo,
            stdin=subprocess.DEVNULL,
        ).stdout.splitlines()
        assert any(
            "unrelated.txt" in line and line.startswith("A") for line in status_lines
        ), "unrelated.txt must remain staged after commit_batch"
