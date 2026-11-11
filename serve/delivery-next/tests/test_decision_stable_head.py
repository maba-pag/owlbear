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
from owlbear_delivery_next.local_system.data_repo import DataRepo
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
    """Forward each real proof, observing its captured-SHA reads only inside that call."""

    def __init__(self, tmp_path: Path, monkeypatch) -> None:
        self.tmp_path = tmp_path
        self.armed = ""
        self.moved = self.head_at_move = self.generation = self.journal = self.index = None
        self.worktree = {}
        self.reads = {"committed": [], "landed": []}
        self.ancestry = {"committed": [], "landed": []}
        for module, name, proof in (
            (decision_recovery, "_committed", "committed"),
            (decision_transaction, "landed", "landed"),
        ):
            real = getattr(module, name)
            monkeypatch.setattr(module, name, self.observer(real, proof, monkeypatch))

    def observer(self, real, proof, monkeypatch):
        def observed(shared, *args):
            files = args[0].files if proof == "committed" else args[1]
            paths = {rel for rel, _, _ in files}
            real_git = DataRepo.git

            def forwarding(repo, *command, **kwargs):
                said = real_git(repo, *command, **kwargs)
                if command[:2] == ("merge-base", "--is-ancestor") and not said.returncode:
                    self.ancestry[proof].append(command[3])
                    if self.armed == proof and self.moved is None:
                        self._move(repo, command[3])
                if command[:1] == ("show",) and command[1].partition(":")[2] in paths:
                    self.reads[proof].append(command[1].partition(":")[0])
                return said

            with monkeypatch.context() as scoped:
                scoped.setattr(DataRepo, "git", forwarding)
                return real(shared, *args)
        return observed

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
    with monkeypatch.context() as patched:
        yield OwnerMove(tmp_path, patched)


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


@pytest.mark.parametrize("moved", [False, True], ids=["healthy", "owner-head-move"])
def test_save_landing_requires_one_stable_commit(
    shared_repo, tmp_path, owner_move, moved
) -> None:
    root, remote = shared_repo
    pre = owner_commit(root, "owner words\n")
    shared = DataRepo(inside_tmp(root, tmp_path))
    owner_move.armed = "landed" if moved else ""

    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")
    if not moved:
        head = git(root, "rev-parse", "HEAD")
        assert (receipt.saved, receipt.committed, receipt.published) == (True, True, True), receipt.notice
        assert owner_move.moved is None
        assert owner_move.ancestry["landed"] == owner_move.reads["landed"] == [head]
        assert git(remote, "rev-parse", "main") == head
        assert git(root, "status", "--porcelain") == ""
        assert decision_batch.pending(shared) is None
        return

    moved, batch_commit = owner_move.moved, owner_move.head_at_move
    assert moved is not None
    assert batch_commit != pre
    assert is_ancestor(root, pre, batch_commit)  # the batch's own commit descends from the owner's head
    assert not is_ancestor(root, batch_commit, moved)  # unrelated in ancestry...
    assert not is_ancestor(root, pre, moved)
    # ...yet with the same tree
    assert git(root, "rev-parse", f"{moved}^{{tree}}") == git(root, "rev-parse", f"{batch_commit}^{{tree}}")
    assert owner_move.ancestry["landed"] == owner_move.reads["landed"] == [batch_commit]

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


@pytest.mark.parametrize("moved", [False, True], ids=["healthy", "owner-head-move"])
def test_committed_finish_requires_one_stable_commit(
    shared_repo, tmp_path, lost_ack, owner_move, moved
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
    owner_move.reads["landed"].clear()
    owner_move.ancestry["landed"].clear()
    if not moved:
        done = decision_recovery.finish(shared, pending.generation)
        assert done.done, done.notice
        assert owner_move.moved is None
        for proof in ("committed", "landed"):
            assert owner_move.ancestry[proof] == owner_move.reads[proof] == [committed]
        assert decision_batch.pending(shared) is None
        assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main") == committed
        assert len(lost_ack["calls"]) == 1
        assert is_ancestor(root, pre, "HEAD")
        assert (root / OWNER).read_text() == "owner words\n"
        return
    owner_move.armed = "committed"
    with pytest.raises(DecisionsUnavailable):
        decision_recovery.finish(shared, pending.generation)

    moved = owner_move.moved
    assert moved is not None
    assert owner_move.head_at_move == committed
    assert owner_move.ancestry["committed"] == owner_move.reads["committed"] == [committed]
    assert not is_ancestor(root, pre, moved)
    assert git(root, "rev-parse", f"{moved}^{{tree}}") == git(root, "rev-parse", f"{committed}^{{tree}}")
    assert git(root, "rev-parse", "HEAD") == moved
    assert git(remote, "rev-parse", "main") == committed
    assert len(lost_ack["calls"]) == 1
    assert tree_bytes(root) == worktree
    assert (root / git(root, "rev-parse", "--git-path", "index")).read_bytes() == owner_move.index
    pending_after = decision_batch.pending(shared)
    assert pending_after is not None
    assert pending_after.generation == pending.generation
    assert decision_batch.journal_path(shared).read_bytes() == journal


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


@pytest.mark.parametrize("reader", [decision_store.load], ids=["load"])
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


@pytest.mark.parametrize(
    ("project", "reader"),
    [("", decision_store.file_snapshot), (PROJECT, decision_store.load), (PROJECT, decision_store.file_snapshot)],
    ids=["global-file_only", "project-load", "project-file_only"],
)
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
    ("warmth", "marker", "when", "reader"),
    [  # a marker before the read refuses before any cache use, so warmth matters only during collection
        ("cold", "rebase-merge", "before", decision_store.load),
        ("cold", "rebase-apply", "before", decision_store.file_snapshot),
        ("cold", "rebase-merge", "during", decision_store.file_snapshot),
        ("cold", "rebase-apply", "during", decision_store.load),
        ("warm", "rebase-merge", "during", decision_store.file_snapshot),
        ("warm", "rebase-apply", "during", decision_store.load),
    ],
    ids=[
        "cold-merge-before-load",
        "cold-apply-before-file_only",
        "cold-merge-during-file_only",
        "cold-apply-during-load",
        "warm-merge-during-file_only",
        "warm-apply-during-load",
    ],
    indirect=["warmth"],
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
    ("warmth", "when", "reader"),
    [  # the first probe fails before any cache use, so warmth matters only after collection
        ("cold", 1, decision_store.load),
        ("cold", 2, decision_store.file_snapshot),
        ("warm", 2, decision_store.file_snapshot),
    ],
    ids=["cold-before-load", "cold-after_collection-file_only", "warm-after_collection-file_only"],
    indirect=["warmth"],
)
def test_an_unknown_rebase_at_either_probe_refuses_both_readers(
    readable, warmth, failing_rebase_probe, when, reader
) -> None:
    warmth.ready(readable, PROJECT)
    calls = failing_rebase_probe.arm(lambda n: n == when)
    before = checkout_state(readable)
    with pytest.raises(DecisionsUnavailable) as raised:
        reader(readable, PROJECT)
    first = "a rebase is active or unknown, so the decisions are unavailable; resolve it in Git first"
    later = "the decisions or rebase state changed while they were read, so they are not settled; read them again"
    said = failing_rebase_probe.said(readable.root)
    assert (str(raised.value), raised.value.action) == (
        (f"{first}: {said}", decision_store.REPAIR) if when == 1 else (f"{later}: {said}", decision_store.READ)
    )
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
    if change == "rebase":  # caught at the end of the first read; the read made again meets the rebase at its start
        with pytest.raises(DecisionsUnavailable, match="a rebase is active") as raised:
            reader(readable, PROJECT)
        assert raised.value.action == decision_store.REPAIR
        parses = warmth.collected(PROJECT)
    else:  # caught at the end of the first read, so it is read again with no writer, parsed at the moved HEAD
        got = reader(readable, PROJECT)
        if reader is decision_store.load:
            assert got.commit == git(readable.root, "rev-parse", "HEAD")
        parses = [*warmth.collected(PROJECT), PROJECT]
    assert len(moved) == 1
    assert checkout_state(readable) == moved[0]
    assert warmth.parses == parses
