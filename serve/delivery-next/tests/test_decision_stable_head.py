"""Stable-HEAD landing proofs and authority reads, including an ordinary pull that stops in a conflicting rebase.

The public save, Finish and read paths use disposable remotes and clones under tmp_path. Injected races move the owner's
HEAD or start a rebase marker during collection and blocking probes; failed rebase probes remain unknown. Every Git
mutation targets a path under tmp_path.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, snapshot, write
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import (
    decision_batch,
    decision_cache,
    decision_recovery,
    decision_store,
    decision_sync,
    decision_transaction,
)
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


READERS = [decision_store.load, decision_store.file_snapshot]


def checkout_state(shared: DataRepo) -> tuple:
    """HEAD, index, rebase metadata and files, none of which an ordinary reader may change."""
    admin = shared.root / git(shared.root, "rev-parse", "--absolute-git-dir")
    rebases = {name: tree_bytes(admin / name) for name in ("rebase-merge", "rebase-apply") if (admin / name).exists()}
    return git(shared.root, "rev-parse", "HEAD"), (admin / "index").read_bytes(), rebases, tree_bytes(shared.root)


@pytest.fixture
def readable(shared_repo, seed_once) -> DataRepo:
    shared = DataRepo(shared_repo[0])

    def seed() -> None:
        assert save(shared, make(), expected_revision=None, message="decisions: seed").published

    seed_once("stable-head", seed)
    return shared


@pytest.fixture
def conflicting_replacement(readable, shared_repo, tmp_path) -> tuple[DataRepo, Decision, Decision]:
    shared, remote = readable, shared_repo[1]
    old = decision_store.load(shared, PROJECT).snapshot.entries[0].decision
    second = inside_tmp(tmp_path / "second", tmp_path)
    git(tmp_path, "clone", "-q", str(remote), str(second))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(second, "config", key, value)
    successor = make().model_copy(
        update={"statement": "Notes live in PostgreSQL.", "links": (Link(type=LinkType.REPLACES, target=old.id),)}
    )
    write(old.model_copy(update={"state": State.REPLACED}), shared.root / PROJECT, old.revision)
    write(successor, shared.root / PROJECT, None)
    git(shared.root, "add", "--", f"{PROJECT}/decisions")
    git(shared.root, "commit", "-q", "-m", "decisions: complete replacement")
    seen = snapshot(shared.root, PROJECT)
    assert seen.complete
    assert not seen.findings
    assert seen.active(successor.id)
    assert not seen.active(old.id)
    write(
        old.model_copy(update={"rationale": "The remote owner edited the predecessor."}), second / PROJECT, old.revision
    )
    git(second, "add", "--", f"{PROJECT}/decisions")
    git(second, "commit", "-q", "-m", "decisions: edit predecessor")
    git(second, "push", "-q")
    return shared, old, successor


@pytest.mark.parametrize("reader", READERS, ids=["load", "file_only"])
def test_a_conflicting_ordinary_pull_makes_both_readers_unavailable_without_changing_git(
    conflicting_replacement, reader
) -> None:
    shared, old, successor = conflicting_replacement
    assert "rebase is in progress" in shared.pull()
    assert shared.rebasing()
    assert decision_batch.pending(shared) is None
    assert not decision_batch.journal_path(shared).exists()
    assert f"{PROJECT}/decisions/{old.id}.md" in git(shared.root, "ls-files", "--unmerged")
    partial = snapshot(shared.root, PROJECT)
    assert partial.complete
    assert not partial.findings
    assert partial.active(old.id)
    assert partial.active(successor.id)  # usable files, but only half the replacement landed
    before = checkout_state(shared)

    with pytest.raises(DecisionsUnavailable, match="rebase") as raised:
        reader(shared, PROJECT)

    assert raised.value.action == decision_store.REPAIR
    assert checkout_state(shared) == before


@pytest.mark.parametrize("reader", READERS, ids=["load", "file_only"])
@pytest.mark.parametrize("project", ["", PROJECT], ids=["global", "project"])
def test_both_readers_keep_healthy_authority(readable, reader, project) -> None:
    seen = reader(readable, project)
    if isinstance(seen, decision_store.DataView):
        assert seen.commit == git(readable.root, "rev-parse", "HEAD")
        seen = seen.snapshot
    assert seen.complete
    assert not seen.findings
    assert len(seen.entries) == bool(project)
    assert all(seen.active(entry.decision.id) for entry in seen.entries)


@pytest.mark.parametrize(
    ("marker", "when", "reader"),
    [
        ("rebase-merge", "before", decision_store.load),
        ("rebase-apply", "before", decision_store.file_snapshot),
        ("rebase-merge", "during", decision_store.file_snapshot),
        ("rebase-apply", "during", decision_store.load),
    ],
    ids=["merge-before-load", "apply-before-file_only", "merge-during-file_only", "apply-during-load"],
)
def test_an_active_rebase_before_or_during_collection_refuses_both_readers(
    readable, warmth, marker, when, reader
) -> None:
    shared, project = readable, PROJECT
    warmth.ready(shared, project)
    path = shared.root / git(shared.root, "rev-parse", "--git-path", marker)
    held = []

    def started() -> None:
        path.mkdir()
        held.append(checkout_state(shared))

    def during(target, name):  # a kept snapshot is never parsed: the marker begins at its fingerprint instead
        real = getattr(target, name)

        def collect(root, project):
            seen = real(root, project)
            started()
            return seen

        warmth.monkeypatch.setattr(target, name, collect)

    if when == "before":
        started()
    else:
        during(*((decision_cache, "fingerprint") if warmth.warm else (decision_store, "snapshot")))

    with pytest.raises(DecisionsUnavailable, match="rebase"):
        reader(shared, project)

    assert len(held) == 1
    assert checkout_state(shared) == held[0]  # HEAD is unchanged even when the marker began during collection
    assert warmth.parses == ([] if when == "before" else warmth.collected(project))


@pytest.mark.parametrize(
    ("when", "reader"),
    [(1, decision_store.load), (2, decision_store.file_snapshot)],
    ids=["before-load", "after_collection-file_only"],
)
def test_an_unknown_rebase_at_either_probe_refuses_both_readers(readable, monkeypatch, warmth, when, reader) -> None:
    warmth.ready(readable, PROJECT)
    real, calls = DataRepo.rebasing, []

    def rebasing(shared, *args, **kwargs):
        calls.append(shared.root)
        if len(calls) == when:
            msg = "cannot tell whether a rebase is in progress"
            raise DataRepoError(msg)
        return real(shared, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "rebasing", rebasing)
    before = checkout_state(readable)
    with pytest.raises(DecisionsUnavailable) as raised:
        reader(readable, PROJECT)
    assert raised.value.action == (decision_store.REPAIR if when == 1 else decision_store.READ)
    assert len(calls) == when
    assert checkout_state(readable) == before
    assert warmth.parses == ([] if when == 1 else warmth.collected(PROJECT))


@pytest.mark.parametrize(
    ("probe", "change", "reader"),
    [
        ("journal", "head", decision_store.load),
        ("rebase", "head", decision_store.file_snapshot),
        ("journal", "rebase", decision_store.load),
    ],
    ids=["journal-head-load", "rebase-head-file_only", "journal-rebase-load"],
)
def test_terminal_checks_follow_the_blocking_probes(readable, warmth, probe, change, reader) -> None:
    warmth.ready(readable, PROJECT)
    monkeypatch = warmth.monkeypatch
    target, name = (decision_store, "_stamp") if probe == "journal" else (DataRepo, "rebasing")
    real, calls, moved = getattr(target, name), [], []

    def checked(shared, *args, **kwargs):
        result = real(shared, *args, **kwargs)
        calls.append(shared.root)
        if len(calls) == 2:
            if change == "head":
                owner_commit(shared.root, f"owner moved HEAD during the {probe} probe\n")
            else:
                (shared.root / git(shared.root, "rev-parse", "--git-path", "rebase-merge")).mkdir()
            moved.append(checkout_state(shared))
        return result

    monkeypatch.setattr(target, name, checked)
    with pytest.raises(DecisionsUnavailable, match="changed while they were read"):
        reader(readable, PROJECT)
    assert len(moved) == 1
    assert checkout_state(readable) == moved[0]
    assert warmth.parses == warmth.collected(PROJECT)
