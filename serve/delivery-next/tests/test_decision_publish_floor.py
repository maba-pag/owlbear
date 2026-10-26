"""The publication floor before any batch is journalled (F7 review): every writer proves its head on the remote first.

Each test drives a public writer over a real disposable Git remote. Only the remote's movement, the acknowledgement
loss and an owner edit are injected.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision as Rule
from owlbear_decisions import Link, LinkType, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change
from owlbear_delivery_next.change_contracts.models import Decision as ChangeDecision
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import (
    change_record,
    decision_archive,
    decision_batch,
    decision_recovery,
    decision_sync,
    decision_transaction,
)
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable, save

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
OWNER = "notes.txt"
STEM = "20261021-090000-notes"
LIMIT, WHERE, UI = "Limit the notes?", "Where do notes live?", "Not a UI change (brief v2, UI paths 1a2b)"
MERGED = PullRequest(
    repository="acme/shop-site", number=7, node_id="n", url="https://x/pull/7", head_branch="owlbear/notes",
    head_sha="a" * 40, base_branch="main", draft=False, state="closed", merged=True, merge_commit_sha="b" * 40,
)  # fmt: skip


class Store:
    """What a record needs of the clone's store: the shared repository and the project's folder in it."""

    def __init__(self, root: Path) -> None:
        self.shared, self.name = DataRepo(root), PROJECT


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def head_blob(cwd: Path, rel_path: str) -> bytes:
    return subprocess.run(["git", "show", f"HEAD:{rel_path}"], cwd=cwd, check=True, capture_output=True).stdout  # noqa: S603, S607


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=root, check=False).returncode == 0  # noqa: S603, S607


def checkout(path: Path, remote: Path) -> DataRepo:
    git(path.parent, "clone", "-q", str(remote), str(path))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(path, "config", key, value)
    return DataRepo(path)


def advance_remote(tmp_path: Path, remote: Path, name: str) -> None:
    """Another checkout pushes an unrelated commit, so the remote holds commits the owner's checkout lacks."""
    other = checkout(tmp_path / f"other-{name}", remote)
    (other.root / name).write_text("elsewhere\n")
    git(other.root, "add", name)
    git(other.root, "commit", "-q", "-m", f"elsewhere: {name}")
    git(other.root, "push", "-q", "origin", "HEAD")


def owner_commit(root: Path, text: str) -> str:
    """An owner commit that is not pushed: the head every batch proves before it is journalled."""
    (root / OWNER).write_text(text)
    git(root, "add", OWNER)
    git(root, "commit", "-q", "-m", "owner: notes")
    return git(root, "rev-parse", "HEAD")


def make(**changes) -> Rule:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Rule(**{**fields, **changes})


def finished() -> Change:
    """A finished, approved Change with a decided and a lasting decision, as the archive needs them."""
    decided = BriefDecision(id=new_id(AT), question=LIMIT, answer="Yes, 800 characters", origin="decided")
    lasting = BriefDecision(
        id=new_id(AT), question=WHERE, answer="One SQLite table", origin="autonomous", scope="project"
    )
    approved = Brief(version=2, title="Notes", outcome="Owners keep notes", decisions=[decided, lasting])
    c = Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=AT, approved=[approved]))
    c.decisions.append(ChangeDecision(id=new_id(AT), text=UI, origin="decided", at=AT + timedelta(hours=1)))
    return c


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


@pytest.fixture
def lost_before_commit(monkeypatch) -> list[list[Path]]:
    """The first publish is lost before its commit, leaving the batch journalled; later publishes are real."""
    real, calls = decision_sync.publish, []

    def publish(shared, paths, message, until, head):
        if not calls:
            calls.append(paths)
            return decision_sync.Sent(notice="acknowledgement lost before the commit", ambiguous=True)
        return real(shared, paths, message, until, head)

    monkeypatch.setattr(decision_sync, "publish", publish)
    return calls


def test_a_record_behind_its_remote_is_caught_up_before_its_commit_is_journalled(shared_repo, tmp_path) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    advance_remote(tmp_path, remote, "elsewhere.txt")

    assert change_record.save(Store(root), finished(), MERGED, AT) == ""

    assert decision_batch.pending(DataRepo(root)) is None
    assert "owner: notes" in git(root, "log", "--format=%s")  # rebased once under a new SHA, never lost
    assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    assert (root / OWNER).read_text() == "owner words\n"
    assert list((root / PROJECT).rglob("decisions/*.md"))


def test_an_archive_behind_its_remote_is_caught_up_before_its_commit_is_journalled(shared_repo, tmp_path) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    advance_remote(tmp_path, remote, "elsewhere.txt")

    _files, left = decision_archive.archive(root, PROJECT, finished(), STEM, "merged")

    assert not left
    assert decision_batch.pending(DataRepo(root)) is None
    assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    assert (root / OWNER).read_text() == "owner words\n"


def test_a_remote_that_moves_between_catch_up_and_proof_is_caught_up_again(shared_repo, tmp_path, monkeypatch) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    real_proved, moved = decision_sync.proved, []

    def move_then_prove(shared, head, until):
        if not moved:
            moved.append(True)
            advance_remote(tmp_path, remote, "moved.txt")
        return real_proved(shared, head, until)

    monkeypatch.setattr(decision_sync, "proved", move_then_prove)
    shared = DataRepo(root)
    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    assert moved == [True]
    assert receipt.saved, receipt.notice
    assert receipt.published, receipt.notice
    assert decision_batch.pending(shared) is None
    assert git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    assert (root / OWNER).read_text() == "owner words\n"


def test_a_committed_generation_completes_offline_without_fetch_push_or_rebase(
    shared_repo, tmp_path, lost_ack, monkeypatch
) -> None:
    root, _remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    git(root, "remote", "set-url", "origin", str(tmp_path / "gone"))  # the remote is unreachable from here on

    commands: list[str] = []
    real_git = DataRepo.git

    def recording(self, *args, **kwargs):
        commands.append(args[0] if args else "")
        return real_git(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", recording)
    lost_ack[0] = False
    done = decision_recovery.finish(shared, pending.generation)

    assert done.done
    assert "committed locally" in done.notice
    assert not {"fetch", "push", "pull", "rebase"} & set(commands)
    assert decision_batch.pending(shared) is None
    assert (root / OWNER).read_text() == "owner words\n"


def _rebase_state_fault(scoped, root: Path, state: str, seen: dict[str, str]) -> None:
    """Change the rebase state after ancestry, only inside the Store and Finish proofs, never the publisher's own."""
    armed, unknown = [False], [False]
    real_landed = decision_transaction.landed
    real_in_head = decision_transaction.in_head
    real_rebasing = DataRepo.rebasing

    def landed_from_store_or_finish(shared, head, rows):
        caller = sys._getframe(1).f_globals.get("__name__", "")  # noqa: SLF001
        armed[0] = caller.endswith(("decision_store", "decision_recovery"))
        try:
            return real_landed(shared, head, rows)
        finally:
            armed[0] = unknown[0] = False

    def in_head_then_change(shared, rel, after, commit):
        found = real_in_head(shared, rel, after, commit)
        if armed[0]:
            seen["commit"] = commit
            if state == "active":
                (root / ".git" / "rebase-merge").mkdir()  # a real paused rebase, started during the blob proof
            unknown[0] = state == "unknown"
        return found

    def rebasing_probe(self, until=None):
        if unknown[0]:
            msg = "cannot tell whether a rebase is in progress: injected after ancestry"
            raise DataRepoError(msg)
        return real_rebasing(self, until)

    scoped.setattr(decision_transaction, "landed", landed_from_store_or_finish)
    scoped.setattr(decision_transaction, "in_head", in_head_then_change)
    scoped.setattr(DataRepo, "rebasing", rebasing_probe)


@pytest.mark.parametrize("path", ["store", "finish"])
@pytest.mark.parametrize("state", ["healthy", "active", "unknown"])
def test_a_rebase_state_change_after_ancestry_never_completes_a_committed_batch(
    shared_repo, lost_ack, monkeypatch, path, state
) -> None:
    root, _remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    if path == "finish":
        save(shared, make(), expected_revision=None, message="decisions: notes")  # committed, but the ack was lost
        pending = decision_batch.pending(shared)
        assert pending is not None
    lost_ack[0] = False  # the publish succeeds, so Store reaches its own landed proof
    seen: dict[str, str] = {}
    receipt = done = None
    refused = False
    with monkeypatch.context() as scoped:
        if state != "healthy":
            _rebase_state_fault(scoped, root, state, seen)
        if path == "store":
            receipt = save(shared, make(), expected_revision=None, message="decisions: notes")
        else:
            try:
                done = decision_recovery.finish(shared, pending.generation)
            except DecisionsUnavailable as failure:
                refused = "not proved now" in str(failure)

    assert (root / OWNER).read_text() == "owner words\n"
    if state == "healthy":
        assert decision_batch.pending(shared) is None
        if path == "store":
            assert receipt.saved
        else:
            assert done.done
        return
    assert "commit" in seen  # the rebase state changed after ancestry, so the fault really ran
    assert git(root, "rev-parse", "HEAD") == seen["commit"]
    assert decision_batch.pending(shared) is not None
    if path == "store":
        assert receipt.saved is False
    else:
        assert refused
        assert done is None


def _terminal_head_switch(scoped, seen: dict[str, str]) -> None:
    """Move HEAD to an unrelated parentless commit with the same tree, during the proof's terminal rebase probe only."""
    armed, probes = [False], [0]
    real_landed = decision_transaction.landed
    real_rebasing = DataRepo.rebasing

    def landed_from_store_or_finish(shared, head, rows):
        caller = sys._getframe(1).f_globals.get("__name__", "")  # noqa: SLF001
        armed[0] = caller.endswith(("decision_store", "decision_recovery"))
        probes[0] = 0
        try:
            return real_landed(shared, head, rows)
        finally:
            armed[0] = False

    def rebasing_then_switch(self, until=None):
        state = real_rebasing(self, until)
        if armed[0]:
            probes[0] += 1
            if probes[0] == 2:  # the terminal probe: the blob and worktree proof is already done
                tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
                stray = self.git("commit-tree", tree, "-m", "unrelated").stdout.strip()
                self.git("update-ref", "HEAD", stray)
                seen["switched"] = stray
        return state

    scoped.setattr(decision_transaction, "landed", landed_from_store_or_finish)
    scoped.setattr(DataRepo, "rebasing", rebasing_then_switch)


@pytest.mark.parametrize("path", ["store", "finish"])
def test_a_same_tree_head_switch_during_the_terminal_probe_never_completes(
    shared_repo, lost_ack, monkeypatch, path
) -> None:
    root, _remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    if path == "finish":
        save(shared, make(), expected_revision=None, message="decisions: notes")
        pending = decision_batch.pending(shared)
        assert pending is not None
    lost_ack[0] = False
    seen: dict[str, str] = {}
    receipt = None
    refusal = ""
    with monkeypatch.context() as scoped:
        _terminal_head_switch(scoped, seen)
        if path == "store":
            receipt = save(shared, make(), expected_revision=None, message="decisions: notes")
        else:
            try:
                decision_recovery.finish(shared, pending.generation)
            except DecisionsUnavailable as failure:
                refusal = str(failure)

    assert "switched" in seen  # the switch really ran, during the terminal probe
    assert git(root, "rev-parse", "HEAD") == seen["switched"]
    assert (root / OWNER).read_text() == "owner words\n"
    assert decision_batch.pending(shared) is not None
    if path == "store":
        assert receipt.saved is False
    else:
        assert "not proved now" in refusal


def test_an_owner_edit_during_a_retained_recovery_publish_cannot_complete(shared_repo, lost_before_commit, monkeypatch):
    root, _remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    head = git(root, "rev-parse", "HEAD")
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    assert git(root, "rev-parse", "HEAD") == head  # the first publish committed nothing

    real_publish = decision_sync.publish

    def publish_then_edit(shared_repo_, paths, message, until, head_):
        sent = real_publish(shared_repo_, paths, message, until, head_)
        paths[0].write_bytes(b"owner edit during recovery\n")  # the owner edits while the recovery's publish returns
        return sent

    monkeypatch.setattr(decision_sync, "publish", publish_then_edit)
    try:
        done = decision_recovery.finish(shared, pending.generation)
    except DecisionsUnavailable:
        done = None

    assert done is None or not done.done
    assert decision_batch.pending(shared).generation == pending.generation
    assert (root / lost_before_commit[0][0].relative_to(root)).read_bytes() == b"owner edit during recovery\n"


def recorded_git(monkeypatch) -> list[str]:
    """Every Git subcommand the public writers run from here on."""
    commands: list[str] = []
    real_git = DataRepo.git

    def recording(self, *args, **kwargs):
        commands.append(args[0] if args else "")
        return real_git(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", recording)
    return commands


@pytest.mark.usefixtures("lost_before_commit")
def test_an_archive_refuses_an_interrupted_uncommitted_batch_before_any_remote_work(
    shared_repo, tmp_path, monkeypatch
) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    advance_remote(tmp_path, remote, "elsewhere.txt")
    head, before, remote_head = git(root, "rev-parse", "HEAD"), tree_bytes(root), git(remote, "rev-parse", "main")
    commands = recorded_git(monkeypatch)

    with pytest.raises(DecisionsUnavailable, match="finished or abandoned"):
        decision_archive.archive(root, PROJECT, finished(), STEM, "merged")

    assert not {"fetch", "push", "pull", "rebase"} & set(commands)
    assert git(root, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "main") == remote_head
    assert tree_bytes(root) == before
    assert decision_batch.pending(shared).generation == pending.generation


@pytest.mark.usefixtures("lost_before_commit")
def test_a_record_refuses_an_interrupted_uncommitted_batch_before_any_remote_work(
    shared_repo, tmp_path, monkeypatch
) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    advance_remote(tmp_path, remote, "elsewhere.txt")
    head, before, remote_head = git(root, "rev-parse", "HEAD"), tree_bytes(root), git(remote, "rev-parse", "main")
    commands = recorded_git(monkeypatch)

    notice = change_record.save(Store(root), finished(), MERGED, AT)

    assert "finished or abandoned" in notice
    assert not {"fetch", "push", "pull", "rebase"} & set(commands)
    assert git(root, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "main") == remote_head
    assert tree_bytes(root) == before
    assert decision_batch.pending(shared).generation == pending.generation


@pytest.mark.usefixtures("lost_before_commit")
def test_a_refused_record_with_no_writes_publishes_nothing(shared_repo, tmp_path, monkeypatch) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    advance_remote(tmp_path, remote, "elsewhere.txt")
    head, remote_head = git(root, "rev-parse", "HEAD"), git(remote, "rev-parse", "main")
    commands = recorded_git(monkeypatch)

    notice = change_record.save(Store(root), finished(), MERGED, AT)

    assert "finished or abandoned" in notice
    assert not {"fetch", "push", "pull", "rebase", "commit"} & set(commands)
    assert git(root, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "main") == remote_head
    assert decision_batch.pending(shared).generation == pending.generation


def test_an_interrupted_committed_batch_is_not_pushed_by_a_new_writer_and_the_owner_finishes_it(
    shared_repo, tmp_path, monkeypatch
) -> None:
    root, remote = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    real_publish, origin = decision_sync.publish, git(root, "remote", "get-url", "origin")
    gone = tmp_path / "gone"

    def publish_without_push(shared_, paths, message, until, head):
        git(root, "remote", "set-url", "origin", str(gone))  # the commit lands; its push cannot reach the remote
        try:
            real_publish(shared_, paths, message, until, head)
        finally:
            git(root, "remote", "set-url", "origin", origin)
        return decision_sync.Sent(notice="acknowledgement lost after the commit", ambiguous=True)

    with monkeypatch.context() as hooks:
        hooks.setattr(decision_sync, "publish", publish_without_push)
        save(shared, make(), expected_revision=None, message="decisions: notes")
    pending = decision_batch.pending(shared)
    assert pending is not None
    assert git(root, "rev-parse", "HEAD") != git(remote, "rev-parse", "main")  # committed, not published
    advance_remote(tmp_path, remote, "elsewhere.txt")
    remote_head = git(remote, "rev-parse", "main")

    with monkeypatch.context() as hooks:
        commands = recorded_git(hooks)
        with pytest.raises(DecisionsUnavailable, match="finished or abandoned"):
            decision_archive.archive(root, PROJECT, finished(), STEM, "merged")

    assert "push" not in commands
    assert git(remote, "rev-parse", "main") == remote_head
    # the owner's own Finish, outside the new writer, completes the matching generation
    done = decision_recovery.finish(shared, pending.generation)
    assert done.done
    assert decision_batch.pending(shared) is None
    for rel_path, _, after_image in pending.files:
        assert head_blob(root, rel_path) == after_image


def test_a_flag_batch_that_lands_nothing_but_looks_sent_halts_the_next_round_before_any_remote_work(
    shared_repo, tmp_path, monkeypatch
) -> None:
    root, remote = shared_repo
    shared = DataRepo(root)
    old = make(state=State.REPLACED)
    save(shared, old, expected_revision=None, message="decisions: old")
    first = make(links=(Link(type=LinkType.REPLACES, target=old.id),))
    save(shared, first, expected_revision=None, message="decisions: first")
    real_publish = decision_sync.publish

    def sent_but_nothing_lands(shared_, paths, message, until, head):
        if not message.startswith("decisions: conflict on"):
            return real_publish(shared_, paths, message, until, head)
        advance_remote(tmp_path, remote, "elsewhere.txt")  # the remote moves before the loop's next round
        log.append("flag-returned")
        return decision_sync.Sent()  # success-looking, with no commit and HEAD unmoved

    with monkeypatch.context() as hooks:
        log = recorded_git(hooks)
        hooks.setattr(decision_sync, "publish", sent_but_nothing_lands)
        rival = make(links=(Link(type=LinkType.REPLACES, target=old.id),))
        save(shared, rival, expected_revision=None, message="decisions: rival")

    pending = decision_batch.pending(shared)
    assert pending is not None
    after = log[log.index("flag-returned") + 1 :]
    assert not {"fetch", "push", "pull", "rebase", "ls-remote"} & set(after)
    assert git(root, "rev-parse", "HEAD") == pending.head  # the rival's own commit; the next round moved nothing
    recovered = decision_recovery.finish(shared, pending.generation)
    assert recovered.done
    assert decision_batch.pending(shared) is None
    for rel_path, _, after_image in pending.files:
        assert head_blob(root, rel_path) == after_image


@pytest.mark.usefixtures("lost_before_commit")
def test_a_journal_whose_files_are_not_a_list_is_refused_and_its_bytes_are_kept(shared_repo) -> None:
    root, _ = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    save(shared, make(), expected_revision=None, message="decisions: notes")
    journal = decision_batch.journal_path(shared)
    raw = journal.read_bytes()
    damaged = json.loads(raw)
    damaged["files"] = "not-a-list"
    journal.write_bytes(json.dumps(damaged).encode())
    kept = journal.read_bytes()

    with pytest.raises(decision_batch.JournalError):
        decision_batch.pending(shared)

    assert journal.read_bytes() == kept
    assert kept != raw


def test_an_owned_file_that_is_a_symlink_is_never_followed_while_a_plain_file_still_matches(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    plain = checkout / "real.txt"
    plain.write_bytes(b"after")
    link = checkout / "linked.txt"
    link.symlink_to(plain)

    assert decision_batch.owned(checkout, {plain: (None, b"after")})  # positive control: a plain matching file
    assert not decision_batch.owned(checkout, {link: (None, b"after")})  # refused though its referent matches
    assert link.is_symlink()


def test_a_real_rebase_paused_by_exec_blocks_a_new_save_and_is_never_aborted(shared_repo, monkeypatch) -> None:
    root, _ = shared_repo
    owner_commit(root, "owner words\n")
    paused = subprocess.run(["git", "rebase", "--exec", "false", "HEAD~1"], cwd=root, check=False, capture_output=True)  # noqa: S607
    assert paused.returncode != 0
    assert (root / ".git" / "rebase-merge").is_dir()
    assert DataRepo(root).rebasing() is True
    shared = DataRepo(root)
    head, before = git(root, "rev-parse", "HEAD"), tree_bytes(root)
    commands = recorded_git(monkeypatch)

    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    assert not receipt.saved
    assert "rebase is in progress" in receipt.notice
    assert not {"fetch", "push", "pull", "rebase", "commit", "rebase --abort"} & set(commands)
    assert git(root, "rev-parse", "HEAD") == head
    assert tree_bytes(root) == before
    assert (root / ".git" / "rebase-merge").is_dir()


def test_a_detached_head_with_no_rebase_is_not_mistaken_for_one(shared_repo) -> None:
    root, _ = shared_repo
    owner_commit(root, "owner words\n")
    git(root, "checkout", "-q", "--detach")
    assert not (root / ".git" / "rebase-merge").exists()
    assert DataRepo(root).rebasing() is False


def test_a_rebase_in_progress_refuses_a_new_save_before_writing_anything(shared_repo, monkeypatch) -> None:
    root, _ = shared_repo
    owner_commit(root, "owner words\n")
    (root / ".git" / "rebase-merge").mkdir()
    shared = DataRepo(root)
    head = git(root, "rev-parse", "HEAD")
    commands = recorded_git(monkeypatch)

    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    assert not receipt.saved
    assert "rebase is in progress" in receipt.notice
    assert "nothing was written" in receipt.notice
    assert not {"fetch", "push", "pull", "rebase", "commit"} & set(commands)
    assert git(root, "rev-parse", "HEAD") == head
    assert decision_batch.pending(shared) is None
    assert (root / OWNER).read_text() == "owner words\n"


def test_an_owner_commit_during_a_paused_rebase_is_never_rolled_back_by_the_publisher(shared_repo, monkeypatch) -> None:
    root, _ = shared_repo
    owner_commit(root, "owner words\n")
    shared = DataRepo(root)
    commands = recorded_git(monkeypatch)
    real_publish = decision_sync.publish
    owner: dict[str, object] = {}

    def owner_commits_and_pauses_then_publish(*args, **kwargs):
        git(root, "add", "-A")  # the owner commits the batch while the checkout enters a paused edit
        git(root, "commit", "-q", "-m", "owner: committed during the rebase")
        (root / ".git" / "rebase-merge").mkdir()
        owner["head"] = git(root, "rev-parse", "HEAD")
        owner["index"] = git(root, "ls-files", "-s")
        owner["tree"] = tree_bytes(root)
        owner["mark"] = len(commands)
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", owner_commits_and_pauses_then_publish)
    receipt = save(shared, make(), expected_revision=None, message="decisions: notes")

    assert not receipt.saved
    assert "rebase is in progress" in receipt.notice
    assert git(root, "rev-parse", "HEAD") == owner["head"]
    assert git(root, "ls-files", "-s") == owner["index"]
    assert tree_bytes(root) == owner["tree"]
    assert decision_batch.pending(shared) is not None
    assert not {"fetch", "push", "pull", "rebase", "commit"} & set(commands[owner["mark"] :])
