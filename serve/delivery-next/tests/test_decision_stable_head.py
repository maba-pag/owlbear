"""A batch's proof reads one HEAD SHA for ancestry and every blob, and refuses when HEAD moves while it collects proof.

Each test drives the public save and Finish paths over a disposable remote and clone under tmp_path. The only injected
fault is an owner HEAD move to an unrelated commit with HEAD's exact tree. It is made at the production Git boundary,
right after the landing proof's successful ancestry command and before its blob reads. Every Git mutation targets a
path under tmp_path.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_recovery, decision_sync, decision_transaction
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable, save

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
OWNER = "notes.txt"


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    ran = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=root, check=False)  # noqa: S603, S607
    return ran.returncode == 0


def inside_tmp(path: Path, tmp_path: Path) -> Path:
    """Every Git mutation in this module targets a disposable repository under the test's tmp_path."""
    assert path.resolve().is_relative_to(tmp_path.resolve()), f"{path} is outside {tmp_path}"
    return path


def make() -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**fields)


def owner_commit(root: Path, text: str) -> str:
    """An owner commit that is not pushed: the batch's head once the batch begins."""
    (root / OWNER).write_text(text)
    git(root, "add", OWNER)
    git(root, "commit", "-q", "-m", "owner: notes")
    return git(root, "rev-parse", "HEAD")


def tree_bytes(root: Path) -> dict[str, bytes]:
    files = (p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files}


class OwnerMove:
    """Observes every Git command at the production boundary and, once armed, moves HEAD at the landing proof.

    The landing phase is the one ancestry command `merge-base --is-ancestor <batch head> HEAD` that succeeds while the
    journal is pending with that head and HEAD is the commit it checked. Preparation checks run before the journal is
    written or against the remote, so they never match. The move is a parentless commit with HEAD's exact tree, set by
    a compare-and-swap `update-ref`, so the index and worktree are not touched. Snapshots taken at the move let a test
    assert that nothing was undone afterwards.
    """

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.real = DataRepo.git
        self.armed = False
        self.window = False  # open from a landing ancestry check until the proof re-reads HEAD
        self.files: set[str] = set()  # the batch's paths, once a landing proof has been seen
        self.reads: list[str] = []  # the commit each blob read of the batch's files used, in order
        self.moved: str | None = None  # the owner's unrelated commit, once injected
        self.head_at_move: str | None = None
        self.generation: str | None = None
        self.journal: bytes | None = None
        self.index: bytes | None = None
        self.worktree: dict[str, bytes] = {}

    def __call__(
        self, shared: DataRepo, *args: str, until: float | None = None, **kwargs
    ) -> subprocess.CompletedProcess[str]:
        said = self.real(shared, *args, until=until, **kwargs)  # a push's guard goes on to the real wrapper
        if args[:2] == ("merge-base", "--is-ancestor") and not said.returncode and self._landing(shared, args):
            self.window = True
            if self.armed and self.moved is None:
                self._move(shared, args[3])
        elif self.window and args == ("rev-parse", "--verify", "-q", "HEAD"):
            self.window = False
        elif self.window and args[:1] == ("show",) and args[1].partition(":")[2] in self.files:
            self.reads.append(args[1].partition(":")[0])
        return said

    def _landing(self, shared: DataRepo, args: tuple[str, ...]) -> bool:
        pending = decision_batch.pending(shared)
        if pending is None or pending.head != args[2]:
            return False
        current = self.real(shared, "rev-parse", "--verify", "-q", "HEAD")
        if current.stdout.strip() != args[3]:
            return False
        self.files = {rel for rel, _, _ in pending.files}
        return True

    def _move(self, shared: DataRepo, head: str) -> None:
        root = inside_tmp(shared.root, self.tmp_path)
        pending = decision_batch.pending(shared)
        assert pending is not None
        self.generation = pending.generation
        self.journal = decision_batch.journal_path(shared).read_bytes()
        self.index = (root / git(root, "rev-parse", "--git-path", "index")).read_bytes()
        self.worktree = tree_bytes(root)
        self.head_at_move = head
        tree = git(root, "rev-parse", f"{head}^{{tree}}")
        self.moved = git(root, "commit-tree", tree, "-m", "owner: unrelated commit, same tree")
        git(root, "update-ref", "HEAD", self.moved, head)


@pytest.fixture
def owner_move(tmp_path, monkeypatch) -> Iterator[OwnerMove]:
    move = OwnerMove(tmp_path)

    def git(shared: DataRepo, *args: str, until: float | None = None, **kwargs) -> subprocess.CompletedProcess[str]:
        return move(shared, *args, until=until, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(DataRepo, "git", git)
        yield move


@pytest.fixture
def lost_ack(monkeypatch) -> Iterator[dict[str, list]]:
    """Publishing lands in Git and on the remote, but the acknowledgement is lost while `lost` is set."""
    real = decision_sync.publish
    switch: dict[str, list] = {"lost": [True], "calls": []}

    def publish(shared, paths, message, until, head):
        switch["calls"].append(head)
        sent = real(shared, paths, message, until, head)
        return decision_sync.Sent(notice="acknowledgement lost", ambiguous=True) if switch["lost"][0] else sent

    with monkeypatch.context() as patched:
        patched.setattr(decision_sync, "publish", publish)
        yield switch


def test_an_owner_head_move_after_ancestry_refuses_the_save_and_keeps_the_journal(
    shared_repo, tmp_path, owner_move
) -> None:
    root, remote = shared_repo
    pre = owner_commit(root, "owner words\n")
    shared = DataRepo(inside_tmp(root, tmp_path))
    owner_move.armed = True

    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    moved, batch_commit = owner_move.moved, owner_move.head_at_move
    assert moved is not None
    assert batch_commit != pre
    assert is_ancestor(root, pre, batch_commit)  # the batch's own commit descends from the owner's head
    assert not is_ancestor(root, batch_commit, moved)  # unrelated in ancestry...
    assert not is_ancestor(root, pre, moved)
    # ...yet with the same tree
    assert git(root, "rev-parse", f"{moved}^{{tree}}") == git(root, "rev-parse", f"{batch_commit}^{{tree}}")
    assert owner_move.reads == [batch_commit]  # every blob read used the SHA the proof pinned, never the owner's

    assert receipt.saved is False
    assert receipt.commit == moved
    assert "interrupted batch" in receipt.notice
    assert git(root, "rev-parse", "HEAD") == moved  # the owner's commit is kept; nothing is undone
    assert git(remote, "rev-parse", "main") == batch_commit  # the one push happened before the move
    assert git(root, "status", "--porcelain") == ""
    assert tree_bytes(root) == owner_move.worktree
    assert (root / git(root, "rev-parse", "--git-path", "index")).read_bytes() == owner_move.index

    pending = decision_batch.pending(shared)
    assert pending is not None
    assert pending.generation == owner_move.generation
    assert pending.head == pre
    assert decision_batch.journal_path(shared).read_bytes() == owner_move.journal

    with pytest.raises(DecisionsUnavailable):  # a later write refuses while the batch is in flight
        save(DataRepo(root), make(), expected_revision=None, message="decisions: later")
    with pytest.raises(DecisionsUnavailable):
        decision_transaction.guard(shared)
    with pytest.raises(DecisionsUnavailable):  # the owner's explicit undo refuses: HEAD is not the batch's head
        decision_recovery.abandon(shared, pending.generation)
    with pytest.raises(DecisionsUnavailable):
        decision_recovery.finish(shared, pending.generation)

    assert git(root, "rev-parse", "HEAD") == moved
    assert decision_batch.pending(shared) is not None
    assert decision_batch.journal_path(shared).read_bytes() == owner_move.journal


def test_an_owner_head_move_after_the_committed_ancestry_check_stops_finish(
    shared_repo, tmp_path, lost_ack, owner_move
) -> None:
    root, remote = shared_repo
    pre = owner_commit(root, "owner words\n")
    shared = DataRepo(inside_tmp(root, tmp_path))
    save(shared, make(), expected_revision=None, message="decisions: notes")  # pushed, acknowledgement lost

    pending = decision_batch.pending(shared)
    committed = git(root, "rev-parse", "HEAD")
    assert pending is not None
    assert pending.head == pre
    assert is_ancestor(root, pre, committed)
    assert git(remote, "rev-parse", "main") == committed
    assert len(lost_ack["calls"]) == 1  # the save published once, and Finish's committed path pushes nothing

    journal = decision_batch.journal_path(shared).read_bytes()
    worktree = tree_bytes(root)
    owner_move.armed = True
    with pytest.raises(DecisionsUnavailable):
        decision_recovery.finish(shared, pending.generation)

    moved = owner_move.moved
    assert moved is not None
    assert owner_move.head_at_move == committed
    assert owner_move.reads == [committed]  # Finish's ancestry and blob reads used the one SHA it captured
    assert not is_ancestor(root, pre, moved)
    assert git(root, "rev-parse", f"{moved}^{{tree}}") == git(root, "rev-parse", f"{committed}^{{tree}}")
    assert git(root, "rev-parse", "HEAD") == moved
    assert git(remote, "rev-parse", "main") == committed
    assert len(lost_ack["calls"]) == 1
    assert tree_bytes(root) == worktree
    pending_after = decision_batch.pending(shared)
    assert pending_after is not None
    assert pending_after.generation == pending.generation
    assert decision_batch.journal_path(shared).read_bytes() == journal


def test_a_stable_head_save_completes_normally(shared_repo, tmp_path, owner_move) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(inside_tmp(root, tmp_path))

    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    head = git(root, "rev-parse", "HEAD")
    assert (receipt.saved, receipt.committed, receipt.published) == (True, True, True), receipt.notice
    assert owner_move.moved is None
    assert owner_move.reads == [head]  # the one SHA every blob read used is the final HEAD
    assert git(remote, "rev-parse", "main") == head
    assert git(root, "status", "--porcelain") == ""
    assert decision_batch.pending(shared) is None


def test_a_stable_head_finish_completes_a_committed_batch(shared_repo, tmp_path, lost_ack, owner_move) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(inside_tmp(root, tmp_path))
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    head = git(root, "rev-parse", "HEAD")
    owner_move.reads.clear()  # only Finish's own blob reads are checked below

    done = decision_recovery.finish(shared, pending.generation)

    assert done.done, done.notice
    assert owner_move.moved is None
    assert owner_move.reads
    assert set(owner_move.reads) == {head}  # both of Finish's proofs read the one SHA they pinned
    assert decision_batch.pending(shared) is None
    assert git(root, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "main") == head
    assert len(lost_ack["calls"]) == 1
