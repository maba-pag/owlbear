"""A batch's journalled head stays on the remote, so a rebase replays only the batch's own later commit (F7).

Each test drives the public save and finish paths over a real disposable Git remote; only the remote's movement and the
acknowledgement loss are injected.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_recovery, decision_sync
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable, save

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
OWNER = "notes.txt"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    ran = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=root, check=False)  # noqa: S603, S607
    return ran.returncode == 0


def checkout(path: Path, remote: Path) -> DataRepo:
    git(path.parent, "clone", "-q", str(remote), str(path))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(path, "config", key, value)
    return DataRepo(path)


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def owner_commit(root: Path, text: str) -> str:
    """An owner commit that is not pushed: the batch's head once the batch begins."""
    (root / OWNER).write_text(text)
    git(root, "add", OWNER)
    git(root, "commit", "-q", "-m", "owner: notes")
    return git(root, "rev-parse", "HEAD")


def tree_bytes(root: Path) -> dict[str, bytes]:
    files = (p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files}


@pytest.fixture
def lost_ack(monkeypatch) -> list[bool]:
    """Publishing lands in Git and on the remote, but the acknowledgement is lost while the switch holds True."""
    real, lost = decision_sync.publish, [True]

    def publish(shared, paths, message, until, head):
        sent = real(shared, paths, message, until, head)
        return decision_sync.Sent(notice="acknowledgement lost", ambiguous=True) if lost[0] else sent

    monkeypatch.setattr(decision_sync, "publish", publish)
    return lost


def test_a_remote_that_moves_before_the_push_is_rebased_over_only_the_new_commit(
    shared_repo, tmp_path, monkeypatch
) -> None:
    root, remote = shared_repo
    owner = owner_commit(root, "owner words\n")
    other = checkout(tmp_path / "other", remote)
    real_commit, moved = DataRepo.commit, []

    def move_remote_first(self, paths, message, until):
        if not moved:  # another checkout pushes after this publish's proof and before its push
            moved.append(True)
            git(other.root, "pull", "-q", "--ff-only", "origin", "main")  # the owner's commit is on the remote by now
            (other.root / "elsewhere.txt").write_text("other\n")
            git(other.root, "add", "elsewhere.txt")
            git(other.root, "commit", "-q", "-m", "elsewhere")
            git(other.root, "push", "-q", "origin", "HEAD")
        return real_commit(self, paths, message, until)

    monkeypatch.setattr(DataRepo, "commit", move_remote_first)
    said = save(DataRepo(root), make(), expected_revision=None, message="decisions: notes")

    assert moved == [True]
    assert (said.saved, said.committed, said.published) == (True, True, True), said.notice
    assert is_ancestor(root, owner, "HEAD")  # the owner's commit was never rewritten
    assert (root / OWNER).read_text() == "owner words\n"
    assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    assert git(root, "status", "--porcelain") == ""


def test_a_lost_acknowledgement_is_finished_from_the_published_head(shared_repo, lost_ack) -> None:
    root, remote = shared_repo
    owner = owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")

    pending = decision_batch.pending(shared)
    assert pending is not None
    assert pending.head == owner
    lost_ack[0] = False
    done = decision_recovery.finish(shared, pending.generation)

    assert done.done, done.notice
    assert decision_batch.pending(shared) is None
    assert is_ancestor(root, owner, "HEAD")
    assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    assert (root / OWNER).read_text() == "owner words\n"


def test_a_foreign_head_with_the_same_tree_is_refused_and_nothing_changes(shared_repo, lost_ack) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    before, published = tree_bytes(root), git(remote, "rev-parse", "main")

    foreign = git(root, "commit-tree", git(root, "rev-parse", "HEAD^{tree}"), "-m", "foreign")
    git(root, "update-ref", "HEAD", foreign)
    lost_ack[0] = False
    with pytest.raises(DecisionsUnavailable):
        decision_recovery.finish(shared, pending.generation)

    assert decision_batch.pending(shared).generation == pending.generation
    assert tree_bytes(root) == before
    assert git(root, "rev-parse", "HEAD") == foreign
    assert git(remote, "rev-parse", "main") == published


def test_a_dirty_checkout_behind_a_remote_that_moved_on_is_refused_before_the_journal(shared_repo, tmp_path) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    (root / OWNER).write_text("owner edit not committed\n")
    other = checkout(tmp_path / "rewriter", remote)
    (other.root / "rewritten.txt").write_text("rewritten\n")
    git(other.root, "add", "rewritten.txt")
    git(other.root, "commit", "-q", "-m", "rewritten")
    git(other.root, "push", "-q", "origin", "HEAD:main")
    before, head, published = tree_bytes(root), git(root, "rev-parse", "HEAD"), git(remote, "rev-parse", "main")

    shared = DataRepo(root)
    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    assert not receipt.saved
    assert decision_batch.pending(shared) is None
    assert tree_bytes(root) == before
    assert git(root, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "main") == published
