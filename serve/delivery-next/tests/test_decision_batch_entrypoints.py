"""Entry-point regressions for the decision-batch journal, HEAD proof, folder creation and put-back durability.

Each test interrupts a real save in-process (a `RuntimeError` escapes `write_batch` before any put-back), so the journal
stays in flight exactly as the crash would leave it, then drives the public recovery or save entry point.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

from owlbear_decisions import Decision, DecisionError, Link, LinkType, Origin, Scope, State, new_id, storage, write
from owlbear_decisions.storage import serialize
from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import (
    decision_batch,
    decision_recovery,
    decision_store,
    decision_sync,
    decision_transaction,
)
from owlbear_delivery_next.workflow_steps import lookup

PROJECT = "shop-site"
AT = datetime(2026, 10, 21, 9, tzinfo=UTC)


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def _seed(picking) -> None:
    picking.put(make(statement="Notes live in SQLite."))
    picking.shared.git("add", "-A")
    picking.shared.git("commit", "-qm", "seed")
    picking.shared.git("push", "-q")


def _interrupt(picking, monkeypatch, items: list[Decision]) -> None:
    """Save *items* as one batch and stop it before anything lands: the journal stays in flight."""
    calls = {"n": 0}
    real_write = decision_store.write

    def interrupted_write(decision, folder, expected=None, **fence):
        calls["n"] += 1
        if calls["n"] == 1:
            msg = "interrupted before the first write"
            raise RuntimeError(msg)
        return real_write(decision, folder, expected, **fence)

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write", interrupted_write)
        with pytest.raises(RuntimeError, match="interrupted"):
            decision_store.save_all(picking.shared, [(d, None) for d in items], message="decisions: interrupted")


def _rewrite_journal(shared: DataRepo, edit) -> None:
    path = decision_batch.journal_path(shared)
    record = json.loads(path.read_bytes())
    edit(record)
    path.write_bytes(json.dumps(record).encode("utf-8"))


@pytest.mark.parametrize("damage", ["null-after", "corrupt"])
@pytest.mark.parametrize("action", ["pending", "finish", "abandon", "save"])
def test_a_journal_with_a_null_after_or_corrupt_text_refuses_every_action_and_changes_nothing(
    picking, monkeypatch, damage, action
):
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Notes use UTC", statement="All note timestamps use UTC.")])
    pending = decision_batch.pending(shared)
    assert pending is not None
    if damage == "null-after":
        _rewrite_journal(shared, lambda record: record["files"][0].__setitem__("after", None))
    else:
        decision_batch.journal_path(shared).write_text("{not json")
    journal = decision_batch.journal_path(shared).read_bytes()
    files = {
        rel: (shared.root / rel).read_bytes() if (shared.root / rel).exists() else None for rel, _, _ in pending.files
    }
    refused = {
        "pending": (lambda: decision_batch.pending(shared), decision_batch.JournalError),
        "finish": (lambda: decision_recovery.finish(shared, pending.generation), decision_store.DecisionsUnavailable),
        "abandon": (lambda: decision_recovery.abandon(shared, pending.generation), decision_store.DecisionsUnavailable),
        "save": (
            lambda: decision_store.save(
                shared, make(title="Notes use UTC", statement="All UTC."), expected_revision=None, message="x"
            ),
            decision_store.DecisionsUnavailable,
        ),
    }[action]
    call, error = refused
    with pytest.raises(error):
        call()
    assert decision_batch.journal_path(shared).read_bytes() == journal
    for rel, text in files.items():
        assert ((shared.root / rel).read_bytes() if (shared.root / rel).exists() else None) == text


def test_a_null_before_image_for_a_new_file_is_accepted_and_finishes(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    pending = decision_batch.pending(shared)
    assert pending is not None
    assert [before for _, before, _ in pending.files] == [None]

    done = decision_recovery.finish(shared, pending.generation)
    assert done.done
    assert decision_batch.pending(shared) is None
    assert (shared.root / PROJECT / "decisions" / f"{new.id}.md").exists()


@pytest.mark.parametrize(
    "edit",
    [
        lambda record: record["files"][0].__setitem__("path", 7),
        lambda record: record.__setitem__("files", {"path": "decisions/x.md"}),
        lambda record: record.__setitem__("files", ["decisions/x.md"]),
        lambda record: record.__setitem__("files", []),  # ids without the files they name
        lambda record: record.__setitem__("ids", []),  # files without the ids that name them
        lambda record: record.__setitem__("ids", ["another-decision"]),  # an id that is not its file's name
        lambda record: record.__setitem__("files", record["files"] * 2) or record["ids"].append(record["ids"][0]),
        lambda record: record.update(ids=[], files=[]),  # no file and no id: nothing of the batch could be proved
    ],
    ids=[
        "path-not-string",
        "files-not-list",
        "file-entry-not-object",
        "ids-without-files",
        "files-without-ids",
        "id-not-its-file",
        "one-file-twice",
        "no-file-and-no-id",
    ],
)
def test_a_journal_with_a_wrongly_typed_file_list_raises_journal_error_and_keeps_its_bytes(picking, monkeypatch, edit):
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Notes use UTC", statement="All note timestamps use UTC.")])
    assert decision_batch.pending(shared) is not None
    _rewrite_journal(shared, edit)
    journal = decision_batch.journal_path(shared).read_bytes()

    with pytest.raises(decision_batch.JournalError):
        decision_batch.pending(shared)
    with pytest.raises(decision_store.DecisionsUnavailable):
        decision_recovery.finish(shared, "any")
    assert decision_batch.journal_path(shared).read_bytes() == journal


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("<outside>", id="absolute"),
        pytest.param("../outside.txt", id="traversal"),
        pytest.param(".git/config", id="git-folder"),
        pytest.param("shop-site/.git/config", id="nested-git-folder"),
        pytest.param(".GIT/config", id="git-folder-case"),
        pytest.param(".g\u200cit/config", id="git-folder-hfs-ignored-code-point"),
        pytest.param(".Git\ufeff/config", id="git-folder-hfs-byte-order-mark"),
        pytest.param(".git./config", id="git-folder-ntfs-trailing-dot"),
        pytest.param(".git /config", id="git-folder-ntfs-trailing-space"),
        pytest.param("GIT~1/config", id="git-folder-ntfs-short-name"),
        pytest.param("shop-site/decisions/a\0.md", id="nul"),
        pytest.param("shop-site/./decisions/a1.md", id="dot-segment"),
        pytest.param("shop-site//decisions/a1.md", id="double-slash"),
        pytest.param("./shop-site/decisions/a1.md", id="leading-dot"),
        pytest.param("shop-site/decisions/a1.md/", id="trailing-slash"),
        pytest.param("", id="empty"),
        pytest.param(".", id="checkout-root"),
    ],
)
@pytest.mark.parametrize("action", ["pending", "finish", "abandon"])
def test_a_journal_path_outside_the_checkout_or_in_git_is_corruption_and_nothing_is_touched(
    picking, monkeypatch, value, action
):
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Notes use UTC", statement="All note timestamps use UTC.")])
    outside = shared.root.parent / "outside.txt"
    outside.write_text("before\n")
    path = str(outside) if value == "<outside>" else value
    target = shared.root / path
    matching = target.read_bytes() if target.is_file() else None  # the before image matches what is there now
    _rewrite_journal(
        shared,
        lambda record: (
            record["files"][0].update(
                path=path,
                before=None if matching is None else base64.b64encode(matching).decode("ascii"),
                after=base64.b64encode(b"after\n").decode("ascii"),
            ),
            record.__setitem__("ids", [PurePosixPath(path).stem]),  # paired, so only the path itself is refused
        ),
    )
    journal = decision_batch.journal_path(shared).read_bytes()
    head = shared.git("rev-parse", "HEAD").stdout
    index = shared.git("ls-files", "-s").stdout
    writes, reads = [], []
    real_replace, real_held = decision_batch.replace_file, decision_batch._held  # noqa: SLF001

    def recording_replace(file_path, data, *fence):
        writes.append(file_path)
        return real_replace(file_path, data, *fence)

    def recording_held(file_path):
        reads.append(file_path)
        return real_held(file_path)

    monkeypatch.setattr(decision_batch, "replace_file", recording_replace)
    monkeypatch.setattr(decision_batch, "_held", recording_held)
    call = {
        "pending": lambda: decision_batch.pending(shared),
        "finish": lambda: decision_recovery.finish(shared, "any"),
        "abandon": lambda: decision_recovery.abandon(shared, "any"),
    }[action]
    error = decision_batch.JournalError if action == "pending" else decision_store.DecisionsUnavailable
    with pytest.raises(error):
        call()

    assert outside.read_bytes() == b"before\n"
    assert (target.read_bytes() if target.is_file() else None) == matching
    assert decision_batch.journal_path(shared).read_bytes() == journal
    assert shared.git("rev-parse", "HEAD").stdout == head
    assert shared.git("ls-files", "-s").stdout == index
    assert writes == []
    assert reads == []


def test_an_ambiguous_head_after_a_landed_commit_keeps_the_journal_and_the_written_file(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    real_commit = DataRepo.commit
    real_rev = decision_sync._rev  # noqa: SLF001 - wrapped to make HEAD unreadable after the commit lands
    state = {"committed": False}

    def commit_lands_but_reports_failure(self, *args, **kwargs):
        real_commit(self, *args, **kwargs)
        state["committed"] = True
        return "the hook reported a failure after the commit"

    def head_unreadable_after_the_commit(shared_repo, ref, until):
        if state["committed"] and ref == "HEAD":
            return None
        return real_rev(shared_repo, ref, until)

    monkeypatch.setattr(DataRepo, "commit", commit_lands_but_reports_failure)
    monkeypatch.setattr(decision_sync, "_rev", head_unreadable_after_the_commit)
    receipt = decision_store.save(shared, new, expected_revision=None, message="decisions: ambiguous")

    assert not receipt.saved
    pending = decision_batch.pending(shared)
    assert pending is not None
    rel = f"{PROJECT}/decisions/{new.id}.md"
    written = (shared.root / rel).read_bytes()
    assert written
    assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == written


def test_an_empty_initial_head_probe_is_ambiguous_and_commits_nothing(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    real_git = DataRepo.git
    head_before = real_git(shared, "rev-parse", "HEAD").stdout

    def empty_head(self, *args, **kwargs):
        if args == ("rev-parse", "--verify", "-q", "HEAD"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
        return real_git(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", empty_head)
    receipt = decision_store.save(shared, new, expected_revision=None, message="decisions: empty head")

    assert not receipt.published
    assert not receipt.saved
    assert real_git(shared, "rev-parse", "HEAD").stdout == head_before
    assert decision_batch.pending(shared) is None
    assert not (shared.root / f"{PROJECT}/decisions/{new.id}.md").exists()


def test_finish_creates_a_missing_decisions_folder_after_the_whole_batch_is_checked(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(project="new-site", title="Use UTC", statement="All timestamps use UTC.")
    assert not (shared.root / "new-site" / "decisions").exists()

    with monkeypatch.context() as m:

        def refuse(*_args, **_kwargs):
            msg = "interrupted before the folder was created"
            raise RuntimeError(msg)

        m.setattr(storage_io, "make_dirs", refuse)
        with pytest.raises(RuntimeError, match="interrupted"):
            decision_store.save(shared, new, expected_revision=None, message="decisions: new folder")
    assert not (shared.root / "new-site" / "decisions").exists()
    pending = decision_batch.pending(shared)
    assert pending is not None

    done = decision_recovery.finish(shared, pending.generation)
    assert done.done
    assert (shared.root / "new-site" / "decisions" / f"{new.id}.md").exists()
    assert decision_batch.pending(shared) is None


def test_finish_refuses_before_creating_any_folder_when_another_file_of_the_batch_was_edited(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    project = make(title="Use UTC", statement="All timestamps use UTC.")
    global_new = make(project="new-site", title="Use Z", statement="All times end in Z.")
    _interrupt(picking, monkeypatch, [project, global_new])
    pending = decision_batch.pending(shared)
    assert pending is not None
    edited_rel = next(rel for rel, _, _ in pending.files if rel.startswith(f"{PROJECT}/"))
    owner = b"the owner's own decision file\n"
    (shared.root / edited_rel).write_bytes(owner)

    with pytest.raises(decision_store.DecisionsUnavailable, match="edited"):
        decision_recovery.finish(shared, pending.generation)
    assert not (shared.root / "new-site" / "decisions").exists()
    assert decision_batch.pending(shared).generation == pending.generation


def test_a_refused_put_back_unlink_is_fsynced_in_its_parent_before_the_refusal_returns(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    project = make(title="Use UTC", statement="All timestamps use UTC.")
    global_new = make(project="new-site", title="Use Z", statement="All times end in Z.")
    real_write = decision_store.write
    project_folder = shared.root / PROJECT / "decisions"
    seen: list[set[str]] = []
    real_fsync = decision_batch.fsync_dir

    def snapshot_then_fsync(path: Path) -> None:
        if Path(path) == project_folder:
            seen.append({p.name for p in Path(path).iterdir()})
        real_fsync(path)

    def first_lands_second_refuses(decision, folder, expected=None, **fence):
        if decision.project == "new-site":
            msg = "refused by the test"
            raise DecisionError(msg)
        return real_write(decision, folder, expected, **fence)

    monkeypatch.setattr(decision_batch, "fsync_dir", snapshot_then_fsync)
    monkeypatch.setattr(decision_store, "write", first_lands_second_refuses)
    receipts = decision_store.save_all(shared, [(project, None), (global_new, None)], message="decisions: refused")

    assert not any(r.saved for r in receipts)
    assert decision_batch.pending(shared) is None
    assert not (project_folder / f"{project.id}.md").exists()
    assert seen
    assert f"{project.id}.md" not in seen[-1]


def replacing(old: Decision, **changes) -> Decision:
    return make(links=(Link(type=LinkType.REPLACES, target=old.id),), **changes)


def _refuse_conflict_flags(monkeypatch) -> None:
    """Git refuses the conflict-flag commit after staging its paths; every other commit goes through."""
    real_commit = DataRepo.commit

    def refusing(self, paths, message, until=None):
        if message.startswith("decisions: conflict on"):
            batch = [paths] if isinstance(paths, Path) else list(paths)
            self.git("add", "--", *[str(p) for p in batch])
            return "git refused the conflict flags"
        return real_commit(self, paths, message, until)

    monkeypatch.setattr(DataRepo, "commit", refusing)


def _two_rivals_with_refused_flags(shared: DataRepo, monkeypatch) -> tuple[Decision, Decision, Decision, object]:
    old = make()
    a, b = replacing(old, title="Notes in A"), replacing(old, title="Notes in B")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    assert decision_store.save(shared, a, expected_revision=None, message="decisions: a").published
    with monkeypatch.context() as m:
        _refuse_conflict_flags(m)
        decision_store.save(shared, b, expected_revision=None, message="decisions: b")
    pending = decision_batch.pending(shared)
    assert pending is not None
    return old, a, b, pending


def test_a_refused_flag_batch_finishes_once_every_rival_is_flagged_and_publishes_no_picker(
    picking, monkeypatch
) -> None:
    shared = picking.shared
    _, a, b, pending = _two_rivals_with_refused_flags(shared, monkeypatch)
    assert {a.id, b.id} <= set(pending.ids)

    recovery = decision_recovery.finish(shared, pending.generation)

    assert recovery.done
    assert decision_batch.pending(shared) is None
    by_id, findings = decision_store.whole(shared)
    assert all(by_id[i].decision.conflict for i in (a.id, b.id))
    assert {f.rule for f in findings} <= {decision_recovery.CONFLICT}
    seen = decision_store.load(shared, PROJECT).snapshot
    assert all(seen.get(i).decision.conflict for i in (a.id, b.id))


@pytest.mark.parametrize("competitors", [("Notes in C",), ("Notes in C", "Notes in D")])
def test_a_flag_batch_with_an_unflagged_competitor_is_refused_and_keeps_its_generation(
    picking, monkeypatch, competitors
) -> None:
    shared = picking.shared
    old, _, _, pending = _two_rivals_with_refused_flags(shared, monkeypatch)
    for title in competitors:  # unflagged competitors on disk; HEAD and the journal stay as they were
        write(replacing(old, title=title), shared.root / PROJECT)
    head = shared.git("rev-parse", "HEAD").stdout

    with pytest.raises(decision_store.DecisionsUnavailable, match="does not validate"):
        decision_recovery.finish(shared, pending.generation)

    assert shared.git("rev-parse", "HEAD").stdout == head
    assert decision_batch.pending(shared).generation == pending.generation


def _owner_commit(shared: DataRepo, message: str) -> None:
    shared.git("add", "-A")
    shared.git("commit", "-qm", message)


def _committed_but_unproved(picking, monkeypatch, new: Decision) -> str:
    """Land *new*'s commit, then make HEAD unreadable: the batch stays pending with its commit in Git."""
    shared = picking.shared
    real_commit = DataRepo.commit
    real_rev = decision_sync._rev  # noqa: SLF001 - wrapped to make HEAD unreadable after the commit lands
    state = {"committed": False}

    def commit_lands_but_reports_failure(self, *args, **kwargs):
        real_commit(self, *args, **kwargs)
        state["committed"] = True
        return "the hook reported a failure after the commit"

    def head_unreadable_after_the_commit(shared_repo, ref, until):
        if state["committed"] and ref == "HEAD":
            return None
        return real_rev(shared_repo, ref, until)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", commit_lands_but_reports_failure)
        m.setattr(decision_sync, "_rev", head_unreadable_after_the_commit)
        receipt = decision_store.save(shared, new, expected_revision=None, message="decisions: ambiguous")
    assert not receipt.saved
    return decision_batch.pending(shared).generation


def test_an_owner_commit_between_two_writes_is_kept_and_the_batch_stays_pending(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    first = make(title="Use UTC", statement="All timestamps use UTC.")
    second = make(title="Use ISO dates", statement="Dates are ISO 8601.")
    real_write = decision_store.write
    calls = {"n": 0}

    def owner_commits_then_second_write_fails(decision, folder, expected=None, **fence):
        calls["n"] += 1
        if calls["n"] == 2:
            _owner_commit(shared, "owner commit between writes")
            msg = "disk full on the second file"
            raise DecisionError(msg)
        return real_write(decision, folder, expected, **fence)

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write", owner_commits_then_second_write_fails)
        receipts = decision_store.save_all(shared, [(first, None), (second, None)], message="decisions: partial")

    assert not any(receipt.saved for receipt in receipts)
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "owner commit between writes"
    rel = f"{PROJECT}/decisions/{first.id}.md"
    assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == (shared.root / rel).read_bytes()
    assert shared.git("diff", "--cached", "--name-only").stdout == ""
    assert decision_batch.pending(shared) is not None


@pytest.mark.parametrize("state", ["active", "unknown"])
@pytest.mark.parametrize("action", [decision_recovery.finish, decision_recovery.abandon])
def test_finish_and_abandon_refuse_an_active_or_unknown_rebase_before_any_restore_or_remote_proof(
    picking, monkeypatch, action, state
):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    generation = decision_batch.pending(shared).generation
    rel = shared.root / f"{PROJECT}/decisions/{new.id}.md"
    write(new, shared.root / PROJECT)
    written = rel.read_bytes()
    head = shared.git("rev-parse", "HEAD").stdout
    seen: list[tuple[str, ...]] = []
    real_git = DataRepo.git

    def recording_git(self, *args, **kwargs):
        seen.append(args)
        return real_git(self, *args, **kwargs)

    if state == "active":
        (shared.root / ".git" / "rebase-merge").mkdir()
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", recording_git)
        if state == "unknown":

            def unreadable(*_args, **_kwargs):
                msg = "the rebase state cannot be read"
                raise DataRepoError(msg)

            m.setattr(DataRepo, "rebasing", unreadable)
        m.setattr(decision_sync, "behind_unproved", lambda *_a, **_k: pytest.fail("remote proof reached"))
        with pytest.raises(decision_store.DecisionsUnavailable):
            action(shared, generation)

    assert not [args for args in seen if args and args[0] in {"fetch", "push", "pull", "rebase"}]
    assert rel.read_bytes() == written
    assert shared.git("rev-parse", "HEAD").stdout == head
    assert decision_batch.pending(shared).generation == generation


@pytest.mark.parametrize("link", ["decisions", "project", "project-with-git-marker"])
def test_a_committed_finish_refuses_a_symlinked_parent_with_matching_images(picking, monkeypatch, tmp_path, link):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    generation = _committed_but_unproved(picking, monkeypatch, new)
    folder = shared.root / PROJECT if link.startswith("project") else shared.root / PROJECT / "decisions"
    outside = tmp_path / "outside"
    folder.rename(outside)
    folder.symlink_to(outside, target_is_directory=True)
    if link == "project-with-git-marker":  # a `.git` inside the linked folder must not end the plain-folder walk
        (outside / "decisions" / ".git").write_text("gitdir: elsewhere\n")
    referent = outside / "decisions" if link.startswith("project") else outside
    held = {p.name: p.read_bytes() for p in referent.iterdir()}
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    journal = decision_batch.journal_path(shared).read_bytes()
    reads: list[Path] = []
    real_read = Path.read_bytes

    def recording_read(path: Path) -> bytes:
        if str(path).startswith((str(folder), str(outside))):
            reads.append(path)
        return real_read(path)

    with monkeypatch.context() as m:
        m.setattr(Path, "read_bytes", recording_read)
        with pytest.raises(decision_store.DecisionsUnavailable, match="differs"):
            decision_recovery.finish(shared, generation)

    assert reads == []  # no referent behind the link is read
    assert folder.is_symlink()
    assert {p.name: p.read_bytes() for p in referent.iterdir()} == held
    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    assert decision_batch.journal_path(shared).read_bytes() == journal


def test_a_healthy_abandon_still_puts_the_files_back(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    generation = decision_batch.pending(shared).generation
    write(new, shared.root / PROJECT)
    rel = shared.root / f"{PROJECT}/decisions/{new.id}.md"
    head = shared.git("rev-parse", "HEAD").stdout

    recovery = decision_recovery.abandon(shared, generation)

    assert recovery.done
    assert not rel.exists()
    assert shared.git("rev-parse", "HEAD").stdout == head
    assert decision_batch.pending(shared) is None


def test_a_healthy_offline_committed_finish_still_completes_without_remote_work(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    generation = _committed_but_unproved(picking, monkeypatch, new)
    head = shared.git("rev-parse", "HEAD").stdout
    seen: list[tuple[str, ...]] = []
    real_git = DataRepo.git

    def recording_git(self, *args, **kwargs):
        seen.append(args)
        return real_git(self, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", recording_git)
        recovery = decision_recovery.finish(shared, generation)

    assert recovery.done
    assert not [args for args in seen if args and args[0] in {"fetch", "push", "pull", "rebase", "ls-remote"}]
    assert shared.git("rev-parse", "HEAD").stdout == head
    assert decision_batch.pending(shared) is None


@pytest.mark.parametrize("owner_commits", [True, False], ids=["owner-commit-first", "unmoved-positive"])
def test_a_refused_publish_after_an_owner_commit_keeps_the_batch_and_the_owner_commit(
    picking, monkeypatch, owner_commits
):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    rel = f"{PROJECT}/decisions/{new.id}.md"
    real_publish = decision_sync.publish

    def owner_commit_then_publish(*args, **kwargs):
        if owner_commits:
            _owner_commit(shared, "owner commits the written file")
        return real_publish(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
        m.setattr(decision_sync, "publish", owner_commit_then_publish)
        receipt = decision_store.save(shared, new, expected_revision=None, message="decisions: refused")

    assert not receipt.saved
    if owner_commits:  # HEAD moved from the journal's head: nothing is put back and the barrier stays
        assert "interrupted batch" in receipt.notice
        assert shared.git("log", "-1", "--format=%s").stdout.strip() == "owner commits the written file"
        assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == (shared.root / rel).read_bytes()
        assert shared.git("diff", "--cached", "--name-only").stdout == ""
        assert decision_batch.pending(shared) is not None
    else:  # the known refusal on the unmoved head still settles
        assert receipt.notice.startswith("not saved, the files are put back")
        assert not (shared.root / rel).exists()
        assert decision_batch.pending(shared) is None


def test_a_head_move_during_the_put_back_keeps_the_batch(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    first = make(title="Use UTC", statement="All timestamps use UTC.")
    second = make(title="Use ISO dates", statement="Dates are ISO 8601.")
    real_write, real_put_back = decision_store.write, decision_store._put_back  # noqa: SLF001

    def second_refused(decision, folder, expected=None, **fence):
        if decision.id == second.id:
            msg = "refused by the test"
            raise DecisionError(msg)
        return real_write(decision, folder, expected, **fence)

    def put_back_then_owner_commits(path, text, *fence):
        real_put_back(path, text, *fence)
        shared.git("commit", "--allow-empty", "-qm", "owner commits during the put-back")

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write", second_refused)
        m.setattr(decision_store, "_put_back", put_back_then_owner_commits)
        receipts = decision_store.save_all(shared, [(first, None), (second, None)], message="decisions: moved")

    assert not any(r.saved for r in receipts)
    assert all("interrupted batch" in r.notice for r in receipts)
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "owner commits during the put-back"
    assert decision_batch.pending(shared) is not None


@pytest.mark.parametrize("change", ["commit", "rebase"])
@pytest.mark.parametrize("action", ["finish", "abandon"])
def test_git_moving_after_the_first_proof_keeps_the_batch_for_the_owner(picking, monkeypatch, action, change):
    """Finish: Git moves during the remote proof, so no file is written. Abandon: it moves during the put-back."""
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    generation = decision_batch.pending(shared).generation
    path = shared.root / f"{PROJECT}/decisions/{new.id}.md"
    if action == "abandon":
        write(new, shared.root / PROJECT)
    writes: list[Path] = []
    real_replace = decision_batch.replace_file

    def move_git() -> None:
        if change == "commit":
            shared.git("commit", "--allow-empty", "-qm", "owner commits meanwhile")
        else:
            (shared.root / ".git" / "rebase-merge").mkdir()

    def replace_then_move(file_path, data, *fence):
        writes.append(file_path)
        real_replace(file_path, data, *fence)
        move_git()

    with monkeypatch.context() as m:
        if action == "finish":
            m.setattr(decision_sync, "behind_unproved", lambda *_a, **_k: move_git() or False)
            m.setattr(decision_batch, "replace_file", replace_then_move)
            with pytest.raises(decision_store.DecisionsUnavailable):
                decision_recovery.finish(shared, generation)
        else:
            m.setattr(decision_batch, "replace_file", replace_then_move)
            with pytest.raises(decision_store.DecisionsUnavailable):
                decision_recovery.abandon(shared, generation)

    if action == "finish":
        assert writes == []
        assert not path.exists()
    assert decision_batch.pending(shared).generation == generation


def test_a_known_refusal_after_an_owner_commit_keeps_the_transaction_batch(picking):
    shared = picking.shared
    first, second = (shared.root / PROJECT / "changes" / f"{name}.json" for name in ("first", "second"))
    first.parent.mkdir(parents=True)

    def owner_commits_part_then_refused(_head: str, _fence) -> decision_transaction.Step:
        first.write_text("{}", encoding="utf-8")
        _owner_commit(shared, "owner commits the first file")
        return decision_transaction.Step("the commit was refused", refused=True)

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    files = [(first, b"{}"), (second, b"{}")]
    notice = decision_transaction.transaction(
        shared, PROJECT, "changes: partial", files, owner_commits_part_then_refused, head
    )

    assert "interrupted batch" in notice
    assert shared.git("show", f"HEAD:{PROJECT}/changes/first.json").stdout == "{}"
    assert first.read_text(encoding="utf-8") == "{}"  # the owner's committed file is not put back
    assert not second.exists()
    assert decision_batch.pending(shared) is not None


@pytest.mark.parametrize(
    "rel",
    [
        f"{PROJECT}/decisions/a1.md",
        f"{PROJECT}/changes/add-notes/decisions/a1.md",
        f"{PROJECT}/changes/20261021-a.json",
    ],
    ids=["project-decision", "change-decision", "change-record"],
)
def test_each_producer_shaped_journal_still_decodes(picking, rel):
    shared = picking.shared
    head = shared.git("rev-parse", "HEAD").stdout.strip()
    stem = PurePosixPath(rel).stem

    generation = decision_batch.begin(shared, PROJECT, head, "decisions: shaped", [stem], [(rel, None, b"after\n")])

    batch = decision_batch.pending(shared)
    assert (batch.generation, batch.ids, batch.files) == (generation, (stem,), ((rel, None, b"after\n"),))


@pytest.mark.parametrize(
    ("ids", "files"),
    [
        ([], []),
        (["a1"], []),
        (["other"], [(f"{PROJECT}/decisions/a1.md", None, b"after\n")]),
        (["config"], [(".git/config", None, b"after\n")]),
        (
            ["a1", "a1"],
            [(f"{PROJECT}/decisions/a1.md", None, b"x\n"), (f"{PROJECT}/./decisions/a1.md", b"x\n", b"y\n")],
        ),
        (
            ["a1", "A1"],
            [(f"{PROJECT}/decisions/a1.md", None, b"x\n"), (f"{PROJECT}/Decisions/A1.md", b"x\n", b"y\n")],
        ),
    ],
    ids=["no-file-and-no-id", "id-without-file", "id-not-its-file", "git-folder", "dot-alias", "case-alias"],
)
def test_a_batch_a_reader_could_not_decode_is_never_journalled(picking, ids, files):
    shared = picking.shared
    head = shared.git("rev-parse", "HEAD").stdout.strip()

    with pytest.raises(decision_batch.JournalError, match="cannot be journalled"):
        decision_batch.begin(shared, PROJECT, head, "decisions: unreadable", ids, files)

    assert not decision_batch.journal_path(shared).exists()
    assert decision_batch.pending(shared) is None


def test_a_save_of_nothing_needs_no_journal_and_no_remote_work(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    head = shared.git("rev-parse", "HEAD").stdout
    seen: list[tuple[str, ...]] = []
    real_git = DataRepo.git

    def recording_git(self, *args, **kwargs):
        seen.append(args)
        return real_git(self, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", recording_git)
        receipts = decision_store.save_all(shared, [], message="decisions: nothing")

    assert receipts == []
    assert not [args for args in seen if args and args[0] in {"fetch", "push", "pull", "rebase", "commit"}]
    assert not decision_batch.journal_path(shared).exists()
    assert shared.git("rev-parse", "HEAD").stdout == head


def test_a_journal_emptied_after_a_partial_write_refuses_every_entry_point_and_changes_nothing(picking, monkeypatch):
    """Two files were journalled and the first written; damage then removed both lists. Nothing may clear it."""
    _seed(picking)
    shared = picking.shared
    first = make(title="Use UTC", statement="All timestamps use UTC.")
    second = make(title="Use ISO dates", statement="Dates are ISO 8601.")
    _interrupt(picking, monkeypatch, [first, second])
    write(first, shared.root / PROJECT)  # the partial batch: one file of two is on disk, not committed
    _rewrite_journal(shared, lambda record: record.update(ids=[], files=[]))
    journal = decision_batch.journal_path(shared).read_bytes()
    generation = json.loads(journal)["generation"]
    folder = shared.root / PROJECT / "decisions"
    held = {p.name: p.read_bytes() for p in folder.iterdir()}
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    picking.picks.clear()
    pickers = len(picking.pickers())

    with pytest.raises(decision_batch.JournalError, match="names no file"):
        decision_batch.pending(shared)
    for action in (decision_recovery.finish, decision_recovery.abandon):
        with pytest.raises(decision_store.DecisionsUnavailable, match="names no file"):
            action(shared, generation)
    with pytest.raises(decision_store.DecisionsUnavailable, match="names no file"):
        decision_store.load(shared, PROJECT)
    answer, done = lookup.chat(shared, PROJECT, "Which timestamps apply?", picking.store.settings)

    assert answer.get("failed"), answer
    assert "decisions" not in answer
    assert done is None
    assert len(picking.pickers()) == pickers  # no governing answer and no picker
    assert decision_batch.journal_path(shared).read_bytes() == journal
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == held
    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)


def _no_authority(picking) -> None:
    """Every reader refuses: no load, and a lookup fails without a governing answer or a picker."""
    shared = picking.shared
    picking.picks.clear()
    pickers = len(picking.pickers())
    with pytest.raises(decision_store.DecisionsUnavailable):
        decision_store.load(shared, PROJECT)
    answer, done = lookup.chat(shared, PROJECT, "Which timestamps apply?", picking.store.settings)
    assert answer.get("failed"), answer
    assert "decisions" not in answer
    assert done is None
    assert len(picking.pickers()) == pickers


def test_a_journal_naming_one_file_twice_by_a_dot_alias_refuses_every_entry_point(picking, monkeypatch):
    """HEAD holds nothing of the batch and the worktree holds its first after image; the alias row would undo it."""
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    write(new, shared.root / PROJECT)
    rel = f"{PROJECT}/decisions/{new.id}.md"
    written = (shared.root / rel).read_bytes()
    alias = {
        "path": f"{PROJECT}/./decisions/{new.id}.md",
        "before": base64.b64encode(written).decode("ascii"),
        "after": base64.b64encode(b"other\n").decode("ascii"),
    }
    _rewrite_journal(shared, lambda record: (record["files"].append(alias), record["ids"].append(new.id)))
    journal = decision_batch.journal_path(shared).read_bytes()
    generation = json.loads(journal)["generation"]
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout

    with pytest.raises(decision_batch.JournalError, match="canonical"):
        decision_batch.pending(shared)
    for action in (decision_recovery.finish, decision_recovery.abandon):
        with pytest.raises(decision_store.DecisionsUnavailable, match="canonical"):
            action(shared, generation)
    _no_authority(picking)

    assert (shared.root / rel).read_bytes() == written
    assert decision_batch.journal_path(shared).read_bytes() == journal
    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)


def test_an_owner_commit_of_every_after_image_is_a_landing_and_completes(picking):
    shared = picking.shared
    target = shared.root / PROJECT / "changes" / "landed.json"
    target.parent.mkdir(parents=True)

    def owner_commits_all_then_refused(_head: str, _fence) -> decision_transaction.Step:
        target.write_text("{}", encoding="utf-8")
        _owner_commit(shared, "owner commits the whole batch")
        return decision_transaction.Step("the commit was refused", refused=True)

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    notice = decision_transaction.transaction(
        shared, PROJECT, "changes: landed", [(target, b"{}")], owner_commits_all_then_refused, head
    )

    assert notice == "the commit was refused"
    assert shared.git("show", f"HEAD:{PROJECT}/changes/landed.json").stdout == "{}"
    assert target.read_text(encoding="utf-8") == "{}"
    assert decision_batch.pending(shared) is None


def _commit_file(shared: DataRepo, rel: str) -> None:
    shared.git("add", "--", rel)
    shared.git("commit", "-qm", f"owner commits {rel}")


def _interrupted_before_folder(picking, monkeypatch, project: str) -> tuple[Decision, str]:
    """A save journalled and then stopped before its decision folder was made: no file of it is on disk."""

    def interrupted(*_args, **_kwargs):
        msg = "interrupted before the folder was created"
        raise RuntimeError(msg)

    new = make(project=project, title="Use UTC", statement="All timestamps use UTC.")
    with monkeypatch.context() as m:
        m.setattr(storage_io, "make_dirs", interrupted)
        with pytest.raises(RuntimeError, match="interrupted"):
            decision_store.save(picking.shared, new, expected_revision=None, message="decisions: before the folder")
    return new, decision_batch.pending(picking.shared).generation


def _record_checkout_writes(m: pytest.MonkeyPatch, shared: DataRepo, seen: list[str]) -> None:
    """Record each write of a checkout file (not the journal in the Git folder) and each Git commit or push."""
    real_replace, real_git = decision_batch.replace_file, DataRepo.git
    admin = shared.root / ".git"

    def recording_replace(path, data, *fence):
        real_replace(path, data, *fence)  # a write refused inside the helper, before its rename, is not a write
        if admin not in Path(path).parents:
            seen.append("replace")

    def recording_git(self, *args, **kwargs):
        if args and args[0] in {"commit", "push"}:
            seen.append(args[0])
        return real_git(self, *args, **kwargs)

    m.setattr(decision_batch, "replace_file", recording_replace)
    m.setattr(DataRepo, "git", recording_git)


@pytest.mark.parametrize("image", ["third", "after", "none"])
@pytest.mark.parametrize("parent", ["missing", "existing"])
def test_an_owner_commit_while_finish_makes_the_folder_is_never_overwritten(picking, monkeypatch, parent, image):
    """The owner writes and commits the file during the folder's final fsync, after Finish's first epoch check.

    `third`: an image of the owner's own stays as committed. `after`: the owner landed the batch exactly; the next
    Finish completes it from that commit without a commit of its own. `none`: the healthy Finish publishes.
    """
    _seed(picking)
    shared = picking.shared
    project = "new-site" if parent == "missing" else PROJECT
    new, generation = _interrupted_before_folder(picking, monkeypatch, project)
    rel = f"{project}/decisions/{new.id}.md"
    folder = shared.root / project / "decisions"
    assert folder.exists() == (parent == "existing")
    owned = {"third": b"the owner's own third image\n", "after": serialize(new).encode("utf-8")}.get(image)
    seen: list[str] = []
    real_fsync = storage_io.fsync_dir

    def final_fsync_then_owner_commits(path):
        real_fsync(path)
        if owned is not None and not seen and Path(path) == folder.parent:  # make_dirs' last fsync, both cases
            seen.append("owner")
            (shared.root / rel).write_bytes(owned)
            _commit_file(shared, rel)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "fsync_dir", final_fsync_then_owner_commits)
        _record_checkout_writes(m, shared, seen)
        if owned is None:
            assert decision_recovery.finish(shared, generation).done
        else:  # the owner's file holds neither image for the batch's head now, or HEAD moved: either refuses
            with pytest.raises(decision_store.DecisionsUnavailable, match=r"moved|edited"):
                decision_recovery.finish(shared, generation)

    if owned is None:
        assert "replace" in seen
        assert decision_batch.pending(shared) is None
        return
    assert seen == ["owner", "commit"]  # the owner's own commit only: no write, commit or push by Finish after it
    owner_head = shared.git("rev-parse", "HEAD").stdout
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == f"owner commits {rel}"
    assert (shared.root / rel).read_bytes() == owned
    assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == owned
    assert shared.git("diff", "--cached", "--name-only").stdout == ""
    assert decision_batch.pending(shared).generation == generation
    _no_authority(picking)
    if image == "after":  # the owner's exact landing completes from its commit, offline and without a new commit
        seen.clear()
        with monkeypatch.context() as m:
            _record_checkout_writes(m, shared, seen)
            assert decision_recovery.finish(shared, generation).done
        assert seen == []
        assert shared.git("rev-parse", "HEAD").stdout == owner_head
        assert (shared.root / rel).read_bytes() == owned
        assert decision_batch.pending(shared) is None


def _two_files(picking, monkeypatch, surface: str) -> tuple[list[str], list[bytes], object]:
    """Two files of one batch written as their after images, and the call that puts them back."""
    shared = picking.shared
    if surface == "generic":
        rels = [f"{PROJECT}/changes/first.json", f"{PROJECT}/changes/second.json"]
        afters = [b'{"n": 1}\n', b'{"n": 2}\n']
        (shared.root / PROJECT / "changes").mkdir(parents=True)

        def step(_head: str, _fence) -> decision_transaction.Step:
            for rel, after in zip(rels, afters, strict=True):
                (shared.root / rel).write_bytes(after)
            return decision_transaction.Step("the commit was refused", refused=True)

        head = shared.git("rev-parse", "HEAD").stdout.strip()
        files = [(shared.root / rel, after) for rel, after in zip(rels, afters, strict=True)]
        return (
            rels,
            afters,
            lambda: decision_transaction.transaction(shared, PROJECT, "changes: two", files, step, head),
        )
    pair = [make(title="Use UTC", statement="All timestamps use UTC."), make(title="Use ISO", statement="ISO dates.")]
    rels = [f"{PROJECT}/decisions/{d.id}.md" for d in pair]
    afters = [serialize(d).encode("utf-8") for d in pair]
    if surface == "store":

        def save() -> None:
            with monkeypatch.context() as m:
                m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
                receipts = decision_store.save_all(shared, [(d, None) for d in pair], message="decisions: two")
            assert not any(r.saved for r in receipts)

        return rels, afters, save
    _interrupt(picking, monkeypatch, pair)
    for decision in pair:
        write(decision, shared.root / PROJECT)
    generation = decision_batch.pending(shared).generation

    def abandon() -> None:
        with pytest.raises(decision_store.DecisionsUnavailable, match="moved"):
            decision_recovery.abandon(shared, generation)

    return rels, afters, abandon


def _owner_commits_at(m: pytest.MonkeyPatch, surface: str, moment: str, owner_commits) -> None:
    """Make the owner commit at *moment* of *surface*'s put-back, through real Git in the disposable checkout."""
    if moment == "between":
        target, name = (decision_batch, "replace_file") if surface == "abandon" else (decision_store, "_put_back")
        real = getattr(target, name)

        def put_back_then_owner_commits(path, data, *fence):
            real(path, data, *fence)
            owner_commits()

        m.setattr(target, name, put_back_then_owner_commits)
    elif surface == "abandon":
        real_preflight, calls = decision_recovery._preflight, []  # noqa: SLF001

        def preflight_then_owner_commits(root, batch):  # its second call is the first put-back's epoch probe
            real_preflight(root, batch)
            calls.append(1)
            if len(calls) == 2:
                owner_commits()

        m.setattr(decision_recovery, "_preflight", preflight_then_owner_commits)
    else:
        real_git = DataRepo.git

        def index_probe_then_owner_commits(self, *args, **kwargs):
            if args[:2] == ("diff", "--cached"):
                owner_commits()
            return real_git(self, *args, **kwargs)

        m.setattr(DataRepo, "git", index_probe_then_owner_commits)


@pytest.mark.parametrize("moment", ["probe", "between"])
@pytest.mark.parametrize("surface", ["store", "generic", "abandon"])
def test_an_owner_commit_during_the_put_back_stops_it_and_keeps_every_owner_file(picking, monkeypatch, surface, moment):
    """`probe`: the owner commits the first file while the epoch is probed before the first put-back.

    `between`: the owner commits the second file after the first is put back. Either way the owner's file, HEAD and
    index stay as the owner left them, the batch stays pending and no reader gets authority.
    """
    _seed(picking)
    shared = picking.shared
    rels, afters, run = _two_files(picking, monkeypatch, surface)
    owner = rels[0] if moment == "probe" else rels[1]
    fired: list[str] = []

    def owner_commits() -> None:
        if not fired:
            fired.append(owner)
            _commit_file(shared, owner)

    with monkeypatch.context() as m:
        _owner_commits_at(m, surface, moment, owner_commits)
        run()

    assert fired == [owner]
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == f"owner commits {owner}"
    assert (shared.root / owner).read_bytes() == afters[rels.index(owner)]
    assert shared.git("show", f"HEAD:{owner}").stdout.encode("utf-8") == afters[rels.index(owner)]
    assert shared.git("diff", "--cached", "--name-only").stdout == ""
    if moment == "probe":  # nothing was put back
        assert [(shared.root / rel).read_bytes() for rel in rels] == afters
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _after_temporary_fsync_in(m: pytest.MonkeyPatch, folder: Path, action) -> None:
    """Run *action* once, right after the fsync of the first temporary file (`*.tmp`) any writer made in *folder*."""
    real_fsync, done = os.fsync, [False]

    def fsync_then_act(descriptor):
        real_fsync(descriptor)
        if done[0] or not folder.is_dir():
            return
        found = os.fstat(descriptor)
        temporaries = [p for p in folder.iterdir() if p.name.endswith(".tmp")]
        if any(os.path.samestat(found, p.stat(follow_symlinks=False)) for p in temporaries):
            done[0] = True
            action()

    m.setattr(os, "fsync", fsync_then_act)


def _after_temporary_fsync(m: pytest.MonkeyPatch, module, folder: Path, action) -> None:
    """Run *action* once, right after the fsync of a temporary file *module*'s writer makes in *folder*.

    Only that writer's own temporary in that folder counts: the journal's, in the Git folder, does not.
    """
    real_own, real_fsync = module.own_temporary, os.fsync
    inside, done = [False], [False]

    @contextlib.contextmanager
    def own(folder_fd, data):
        inside[0] = os.path.samestat(os.fstat(folder_fd), folder.stat())
        try:
            with real_own(folder_fd, data) as temporary:  # its write and fsync run on entering
                inside[0] = False
                yield temporary
        finally:
            inside[0] = False

    def fsync_then_act(descriptor):
        real_fsync(descriptor)
        if inside[0] and not done[0]:
            done[0] = True
            action()

    m.setattr(module, "own_temporary", own)
    m.setattr(os, "fsync", fsync_then_act)


def _interrupt_at(picking, monkeypatch, items: list[tuple[Decision, str | None]]) -> str:
    """Save *items* at their expected revisions as one batch, stopped before its first write; its generation."""

    def interrupted(*_args, **_kwargs):
        msg = "interrupted before the first write"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write", interrupted)
        with pytest.raises(RuntimeError, match="interrupted"):
            decision_store.save_all(picking.shared, items, message="decisions: interrupted")
    return decision_batch.pending(picking.shared).generation


def _one_update(picking, monkeypatch, surface: str) -> tuple[Path, bytes, bytes, object]:
    """One file with a before image, its after image, and the call that writes one of them through a temporary file.

    Finish writes the after image; Abandon, the Store's refused save and a generic refused transaction put the before
    image back.
    """
    shared = picking.shared
    if surface == "generic":
        path = shared.root / PROJECT / "changes" / "record.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"n": 0}\n')
        _commit_file(shared, path.relative_to(shared.root).as_posix())
        head = shared.git("rev-parse", "HEAD").stdout.strip()

        def step(_head: str, _fence) -> decision_transaction.Step:
            path.write_bytes(b'{"n": 1}\n')
            return decision_transaction.Step("the commit was refused", refused=True)

        def transaction() -> None:
            notice = decision_transaction.transaction(
                shared, PROJECT, "changes: one", [(path, b'{"n": 1}\n')], step, head
            )
            assert "interrupted batch" in notice

        return path, b'{"n": 0}\n', b'{"n": 1}\n', transaction
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    path = shared.root / f"{PROJECT}/decisions/{old.id}.md"
    before, after = path.read_bytes(), serialize(update).encode("utf-8")
    if surface == "store":

        def save() -> None:
            with monkeypatch.context() as m:
                m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
                said = decision_store.save(shared, update, expected_revision=old.revision, message="decisions: one")
            assert not said.saved

        return path, before, after, save
    generation = _interrupt_at(picking, monkeypatch, [(update, old.revision)])
    if surface == "finish":
        return path, before, after, lambda: decision_recovery.finish(shared, generation)
    path.write_bytes(after)
    return path, before, after, lambda: decision_recovery.abandon(shared, generation)


@pytest.mark.parametrize("owner", ["edit", "commit", "landing"])
@pytest.mark.parametrize("surface", ["finish", "abandon", "store", "generic"])
def test_an_owner_change_while_the_temporary_file_syncs_is_never_overwritten(picking, monkeypatch, surface, owner):
    """The owner changes the destination while the new bytes' temporary file is fsynced, after every earlier check.

    `edit` writes a third image, `commit` commits one; both stay exactly as the owner left them. `landing` commits the
    batch's exact after image: Finish then completes it from the owner's commit, writing and committing nothing.
    """
    _seed(picking)
    shared = picking.shared
    path, _, after, run = _one_update(picking, monkeypatch, surface)
    rel = path.relative_to(shared.root).as_posix()
    owned = after if owner == "landing" else b"the owner's own third image\n"
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    fired: list[str] = []

    def owner_changes_the_file() -> None:  # the new bytes are durable; the rename has not run
        fired.append(owner)
        path.write_bytes(owned)
        if owner != "edit":
            _commit_file(shared, rel)

    with monkeypatch.context() as m:
        _after_temporary_fsync(m, decision_batch, path.parent, owner_changes_the_file)
        if surface in {"finish", "abandon"}:
            with pytest.raises(decision_store.DecisionsUnavailable, match=r"moved|edited"):
                run()
        else:
            run()

    assert fired == [owner]
    assert path.read_bytes() == owned  # never replaced after the owner's change
    assert not [p for p in path.parent.iterdir() if p.name.endswith(".tmp")]  # only its own temporary is removed
    assert decision_batch.pending(shared) is not None
    if owner == "edit":
        assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    else:
        assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == owned
        assert shared.git("diff", "--cached", "--name-only").stdout == ""
    _no_authority(picking)
    if owner == "landing":
        owner_head, seen = shared.git("rev-parse", "HEAD").stdout, []
        with monkeypatch.context() as m:
            _record_checkout_writes(m, shared, seen)
            assert decision_recovery.finish(shared, decision_batch.pending(shared).generation).done
        assert seen == []
        assert shared.git("rev-parse", "HEAD").stdout == owner_head
        assert decision_batch.pending(shared) is None


@pytest.mark.parametrize("change", ["recreate", "symlink", "none"])
def test_abandon_completes_only_when_every_file_holds_exactly_its_before_image(picking, monkeypatch, tmp_path, change):
    """A successor and the decision it updates: Abandon removes the successor, then restores the other file.

    During that restore's final folder fsync the owner recreates the successor (`recreate`) or swaps the folder for a
    symlink to it (`symlink`): Abandon keeps the batch and touches nothing more. `none` is the healthy Abandon.
    """
    _seed(picking)
    shared = picking.shared
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    successor = make(title="Use UTC", statement="All timestamps use UTC.")
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    generation = _interrupt_at(picking, monkeypatch, [(successor, None), (update, old.revision)])
    folder = shared.root / PROJECT / "decisions"
    added, updated = folder / f"{successor.id}.md", folder / f"{old.id}.md"
    before = updated.read_bytes()
    added.write_bytes(serialize(successor).encode("utf-8"))
    updated.write_bytes(serialize(update).encode("utf-8"))
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    fired: list[str] = []
    real_fsync = decision_batch.fsync_dir

    def restore_fsync_then_owner(path):
        real_fsync(path)
        restored = not added.exists() and updated.read_bytes() == before
        if change != "none" and not fired and Path(path) == folder and restored:  # the last restore's folder fsync
            fired.append(change)
            if change == "recreate":
                added.write_bytes(serialize(successor).encode("utf-8"))
            else:
                folder.rename(tmp_path / "moved")
                folder.symlink_to(tmp_path / "moved", target_is_directory=True)

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "fsync_dir", restore_fsync_then_owner)
        if change == "none":
            assert decision_recovery.abandon(shared, generation).done
        else:
            with pytest.raises(decision_store.DecisionsUnavailable, match="changed while it was put back"):
                decision_recovery.abandon(shared, generation)

    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    if change == "none":
        assert not added.exists()
        assert updated.read_bytes() == before
        assert decision_batch.pending(shared) is None
        return
    assert fired == [change]
    if change == "recreate":
        assert added.read_bytes() == serialize(successor).encode("utf-8")  # the owner's file is never removed again
    else:
        assert folder.is_symlink()
        assert not (tmp_path / "moved" / added.name).exists()
        assert (tmp_path / "moved" / updated.name).read_bytes() == before
    assert updated.read_bytes() == before
    assert decision_batch.pending(shared).generation == generation
    _no_authority(picking)


def test_abandoning_a_save_stopped_before_its_first_folder_completes_and_unblocks_authority(picking, monkeypatch):
    """The save journalled a file under folders that never existed and stopped in make_dirs' first fsync."""
    _seed(picking)
    shared = picking.shared
    new = make(project="new-site", title="Use UTC", statement="All timestamps use UTC.")

    def stopped_in_the_first_fsync(_path):
        msg = "interrupted in make_dirs' first fsync"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "fsync_dir", stopped_in_the_first_fsync)
        with pytest.raises(RuntimeError, match="first fsync"):
            decision_store.save(shared, new, expected_revision=None, message="decisions: before any folder")
    generation = decision_batch.pending(shared).generation
    assert not (shared.root / "new-site").exists()
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    names = sorted(p.name for p in shared.root.iterdir())

    assert decision_recovery.abandon(shared, generation).done

    assert decision_batch.pending(shared) is None
    assert not (shared.root / "new-site").exists()  # nothing is made to prove that nothing was there
    assert sorted(p.name for p in shared.root.iterdir()) == names
    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    assert decision_store.load(shared, PROJECT).snapshot is not None
    picking.picks.clear()
    picking.picks.append(pick_tools.PickResult(picked=[]))
    pickers = len(picking.pickers())
    answer, done = lookup.chat(shared, PROJECT, "Which timestamps apply?", picking.store.settings)
    assert answer == {"decisions": []}
    assert done is not None
    assert len(picking.pickers()) == pickers + 1  # authority is readable again, so the picker runs


def _shape(case: str, site: Path, path: Path, outside: Path) -> None:
    """Lay out the folders above *path* for *case*; `never-existed` leaves them all missing."""
    if case in {"existing-folder", "recreated", "recreated-symlink"}:
        path.parent.mkdir(parents=True)
    if case == "symlink-prefix":
        site.symlink_to(outside, target_is_directory=True)
    elif case == "file-prefix":
        site.write_text("a file where a folder belongs\n")
    elif case == "no-permission":
        site.mkdir()
        site.chmod(0)
    elif case == "recreated":
        path.write_text("the owner's file\n")
    elif case == "recreated-symlink":
        path.symlink_to(outside / "missing.md")


@pytest.mark.parametrize(
    ("case", "absent"),
    [
        ("never-existed", True),
        ("existing-folder", True),
        ("symlink-prefix", False),
        ("file-prefix", False),
        ("no-permission", False),
        ("recreated", False),
        ("recreated-symlink", False),
    ],
)
def test_a_before_absent_file_is_proved_absent_only_under_plain_existing_folders(tmp_path, monkeypatch, case, absent):
    root = tmp_path / "checkout"
    (root / ".git").mkdir(parents=True)
    site = root / "new-site"
    path = site / "decisions" / "a1.md"
    outside = tmp_path / "outside"
    outside.mkdir()
    synced: list[Path] = []
    real_fsync = decision_batch.fsync_dir

    def recording_fsync(folder):
        synced.append(Path(folder))
        real_fsync(folder)

    _shape(case, site, path, outside)
    monkeypatch.setattr(decision_batch, "fsync_dir", recording_fsync)
    try:
        assert decision_batch.restored(root, {path: None}) is absent
    finally:
        if case == "no-permission":
            site.chmod(0o755)

    assert sorted(p.name for p in outside.iterdir()) == []  # nothing is made behind a link
    if case == "never-existed":
        assert not site.exists()  # nothing is made to prove the absence
        assert root in synced  # the folder holding the first missing name is made durable
    if case == "existing-folder":
        assert path.parent in synced


def _abandon_outcome(shared: DataRepo, generation: str) -> tuple[bool, str]:
    """Whether Abandon completed, else its refusal, which must be the final proof's."""
    try:
        return decision_recovery.abandon(shared, generation).done, ""
    except decision_store.DecisionsUnavailable as exc:
        assert "changed while it was put back" in str(exc)  # noqa: PT017 - the refusal is part of the outcome
        return False, str(exc)


def _within_restored(m: pytest.MonkeyPatch) -> list[bool]:
    """A flag that is set only while Abandon's final `restored` proof runs."""
    inside = [False]
    real_restored = decision_batch.restored

    def flagged(root, before):
        inside[0] = True
        try:
            return real_restored(root, before)
        finally:
            inside[0] = False

    m.setattr(decision_batch, "restored", flagged)
    return inside


@pytest.mark.parametrize("call", [1, 2, 3])
@pytest.mark.parametrize("order", ["predecessor-first", "successor-first"])
def test_an_owner_rewrite_during_any_fsync_of_the_final_proof_keeps_the_batch(picking, monkeypatch, order, call):
    """During the *call*-th fsync of Abandon's final proof, the owner writes the updated file's after image back.

    No fsync may follow a row's read, in either row order: a rewrite at any fsync refuses, and a *call* past the last
    fsync never fires and Abandon completes.
    """
    _seed(picking)
    shared = picking.shared
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    successor = make(title="Use UTC", statement="All timestamps use UTC.")
    items = [(update, old.revision), (successor, None)]
    generation = _interrupt_at(picking, monkeypatch, items if order == "predecessor-first" else items[::-1])
    folder = shared.root / PROJECT / "decisions"
    added, updated = folder / f"{successor.id}.md", folder / f"{old.id}.md"
    before, rewritten = updated.read_bytes(), serialize(update).encode("utf-8")
    added.write_bytes(serialize(successor).encode("utf-8"))
    updated.write_bytes(rewritten)
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    calls, fired = [0], []
    real_fsync = decision_batch.fsync_dir

    with monkeypatch.context() as m:
        inside = _within_restored(m)

        def fsync_then_owner_rewrites(path):
            real_fsync(path)
            if inside[0]:
                calls[0] += 1
                if calls[0] == call:
                    fired.append(call)
                    updated.write_bytes(rewritten)

        m.setattr(decision_batch, "fsync_dir", fsync_then_owner_rewrites)
        done, refusal = _abandon_outcome(shared, generation)

    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    assert not added.exists()
    assert fired or call > 1  # the proof fsyncs at least once
    assert done == (not fired), refusal  # any rewrite at an fsync refuses; none fired, Abandon completes
    if not fired:
        assert updated.read_bytes() == before
        assert decision_batch.pending(shared) is None
        return
    assert updated.read_bytes() == rewritten  # the owner's bytes stay
    assert decision_batch.pending(shared).generation == generation
    _no_authority(picking)


@pytest.mark.parametrize("call", [1, 2, 3, 4, 5])
def test_a_folder_swapped_for_a_link_during_the_final_absence_read_keeps_the_batch(
    picking, monkeypatch, tmp_path, call
):
    """The project folder exists; its `decisions` folder never did. During the *call*-th lstat of that missing name in
    Abandon's final proof, the owner swaps the project folder for a link to a foreign folder that lacks it too.

    Every swap refuses, the last one included, since the folder chain is checked after the read; a *call* past the
    last lstat never fires and Abandon completes.
    """
    _seed(picking)
    shared = picking.shared
    site = shared.root / "new-site"
    site.mkdir()
    (site / "notes.txt").write_text("the owner's notes\n")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "marker.txt").write_text("foreign\n")
    new = make(project="new-site", title="Use UTC", statement="All timestamps use UTC.")

    def stopped_in_the_first_fsync(_path):
        msg = "interrupted in make_dirs' first fsync"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "fsync_dir", stopped_in_the_first_fsync)
        with pytest.raises(RuntimeError, match="first fsync"):
            decision_store.save(shared, new, expected_revision=None, message="decisions: before its folder")
    generation = decision_batch.pending(shared).generation
    target = os.fspath(site / "decisions")
    head, index = shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout
    calls, fired = [0], []
    real_lstat = os.lstat

    with monkeypatch.context() as m:
        inside = _within_restored(m)

        def lstat_then_owner_swaps(path, *args, **kwargs):
            try:
                return real_lstat(path, *args, **kwargs)
            finally:
                if inside[0] and not fired and os.fspath(path) == target:
                    calls[0] += 1
                    if calls[0] == call:
                        fired.append(call)
                        site.rename(tmp_path / "moved")
                        site.symlink_to(foreign, target_is_directory=True)

        m.setattr(os, "lstat", lstat_then_owner_swaps)
        done, refusal = _abandon_outcome(shared, generation)

    assert (shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout) == (head, index)
    assert sorted(p.name for p in foreign.iterdir()) == ["marker.txt"]  # nothing is made in the foreign folder
    assert fired or call > 1  # the proof reads the missing name at least once
    assert done == (not fired), refusal  # any swap refuses, at the last read too; none fired, Abandon completes
    if not fired:
        assert not site.is_symlink()
        assert decision_batch.pending(shared) is None
        return
    assert site.is_symlink()
    assert (tmp_path / "moved" / "notes.txt").read_text() == "the owner's notes\n"
    assert decision_batch.pending(shared).generation == generation
    _no_authority(picking)


def _read_swap_surface(picking, monkeypatch, surface: str) -> tuple[Path, object, tuple[object, str]]:
    """The file a proof reads, the public call that runs the proof, and the function whose reads are counted."""
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    target = shared.root / f"{PROJECT}/decisions/{new.id}.md"
    if surface == "generic-put-back":
        target = shared.root / PROJECT / "changes" / "record.json"
        target.parent.mkdir(parents=True)
        head = shared.git("rev-parse", "HEAD").stdout.strip()

        def step(_head: str, _fence) -> decision_transaction.Step:
            target.write_bytes(b'{"n": 1}\n')
            return decision_transaction.Step("the commit was refused", refused=True)

        def run() -> None:
            decision_transaction.transaction(shared, PROJECT, "changes: one", [(target, b'{"n": 1}\n')], step, head)

        return target, run, (decision_transaction, "settle")
    if surface in {"store-put-back", "store-landed"}:

        def save() -> None:
            with monkeypatch.context() as m:
                if surface == "store-put-back":
                    m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
                decision_store.save(shared, new, expected_revision=None, message="decisions: one")

        scope = (decision_transaction, "settle" if surface == "store-put-back" else "landed")
        return target, save, scope
    if surface == "finish-committed":
        generation = _committed_but_unproved(picking, monkeypatch, new)
        return target, lambda: decision_recovery.finish(shared, generation), (decision_recovery, "finish")
    _interrupt(picking, monkeypatch, [new])
    write(new, shared.root / PROJECT)
    generation = decision_batch.pending(shared).generation
    return target, lambda: decision_recovery.abandon(shared, generation), (decision_recovery, "abandon")


def _tree(folder: Path, read) -> dict[str, bytes]:
    return {p.name: read(p) for p in sorted(folder.iterdir())}


@pytest.mark.parametrize("call", [1, 2, 3])
@pytest.mark.parametrize(
    "surface", ["store-put-back", "generic-put-back", "abandon", "store-landed", "finish-committed"]
)
def test_a_folder_swapped_for_a_link_while_a_proof_reads_a_file_is_never_trusted(
    picking, monkeypatch, tmp_path, surface, call
):
    """During the *call*-th read of the file in a proof, after its first path checks, the owner moves the folder aside
    and links it to a foreign copy holding the same bytes. The proof must refuse: the foreign files are never removed
    or written, the owner's files stay where the owner moved them, Git is as the owner left it, the batch stays pending
    and no reader gets authority. A *call* past the proof's last read never fires and the surface completes.
    """
    _seed(picking)
    shared = picking.shared
    target, run, (module, name) = _read_swap_surface(picking, monkeypatch, surface)
    folder, moved, foreign = target.parent, tmp_path / "moved", tmp_path / "foreign"
    real_read, real_scope = Path.read_bytes, getattr(module, name)
    inside, calls, fired = [False], [0], {}

    def scoped(*args, **kwargs):
        inside[0] = True
        try:
            return real_scope(*args, **kwargs)
        finally:
            inside[0] = False

    def read_then_owner_swaps(path: Path) -> bytes:
        data = real_read(path)
        if inside[0] and not fired and path == target:
            calls[0] += 1
            if calls[0] == call:
                folder.rename(moved)
                shutil.copytree(moved, foreign)  # the same bytes, so only the folder chain can tell them apart
                folder.symlink_to(foreign, target_is_directory=True)
                fired.update(tree=_tree(moved, real_read), git=_git_state(shared))
        return data

    with monkeypatch.context() as m:
        m.setattr(module, name, scoped)
        m.setattr(Path, "read_bytes", read_then_owner_swaps)
        try:
            run()
        except decision_store.DecisionsUnavailable:
            assert fired  # a refusal is only ever this swap's
    assert fired or call > 1  # every proof reads the file at least once
    if not fired:
        assert decision_batch.pending(shared) is None
        return
    assert _tree(foreign, Path.read_bytes) == fired["tree"]  # nothing removed or written behind the link
    assert _tree(moved, Path.read_bytes) == fired["tree"]  # the owner's files stay where the owner put them
    assert folder.is_symlink()
    assert _git_state(shared) == fired["git"]
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _git_state(shared: DataRepo) -> tuple[str, str]:
    return shared.git("rev-parse", "HEAD").stdout, shared.git("ls-files", "-s").stdout


def _own_files(folder: Path, read) -> dict[str, bytes]:
    """A folder's files, without a writer's leftover temporary (`.name.tmp`), which is never the owner's."""
    return {name: data for name, data in _tree(folder, read).items() if not name.endswith(".tmp")}


def _swap_while_saving(m: pytest.MonkeyPatch, moment: str, target: Path, swap) -> None:
    """Call *swap* once: after the save's planning read of *target*, or after its temporary file's fsync."""
    real_read = Path.read_bytes
    real_journal = decision_store._journal  # noqa: SLF001
    inside = [False]

    def journal(*args, **kwargs):
        inside[0] = True
        try:
            return real_journal(*args, **kwargs)
        finally:
            inside[0] = False

    def planning_read(path: Path) -> bytes:
        data = real_read(path)
        if moment == "planning-read" and inside[0] and path == target:
            swap()
        return data

    m.setattr(decision_store, "_journal", journal)
    m.setattr(Path, "read_bytes", planning_read)
    if moment == "temporary-fsync":
        _after_temporary_fsync_in(m, target.parent, swap)


@pytest.mark.parametrize("moment", ["planning-read", "temporary-fsync", "none"])
def test_a_folder_swapped_while_a_save_plans_or_writes_never_writes_the_foreign_file(
    picking, monkeypatch, tmp_path, moment
):
    """A save updates a decision and its publication is refused. The owner swaps the `decisions` folder for a link to
    a foreign copy holding the same before bytes, while the save reads the file to plan it or while the new bytes'
    temporary file is fsynced. The foreign file is never written, the owner's files stay where the owner moved them,
    Git is as the owner left it, and no reader gets authority. `none` is the healthy refused save, put back.
    """
    _seed(picking)
    shared = picking.shared
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    target = shared.root / f"{PROJECT}/decisions/{old.id}.md"
    before = target.read_bytes()
    folder, moved, foreign = target.parent, tmp_path / "moved", tmp_path / "foreign"
    real_read, fired = Path.read_bytes, {}

    def swap() -> None:
        if fired:
            return
        folder.rename(moved)
        shutil.copytree(moved, foreign, ignore=shutil.ignore_patterns("*.tmp"))  # the same before bytes
        folder.symlink_to(foreign, target_is_directory=True)
        fired.update(tree=_own_files(moved, real_read), git=_git_state(shared))

    with monkeypatch.context() as m:
        _swap_while_saving(m, moment, target, swap)
        m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
        refusal = ""
        try:
            receipt = decision_store.save(shared, update, expected_revision=old.revision, message="decisions: one")
            assert not receipt.saved
        except decision_store.DecisionsUnavailable as exc:
            refusal = str(exc)

    if moment == "none":
        assert not fired
        assert not refusal
        assert target.read_bytes() == before  # the refused save is put back
        assert decision_batch.pending(shared) is None
        return
    assert fired
    expected = {"planning-read": "changed while the batch was planned", "temporary-fsync": "changed during the write"}
    assert expected[moment] in refusal, refusal  # the fence of that moment refused, not a failure of something else
    assert _tree(foreign, Path.read_bytes) == fired["tree"]  # the foreign file holds its before bytes, nothing more
    assert _tree(moved, Path.read_bytes) == fired["tree"]  # the owner's files, and none of this write's temporary left
    assert fired["tree"][target.name] == before
    assert _git_state(shared) == fired["git"]
    _no_authority(picking)


def test_a_folder_swapped_while_a_transaction_step_writes_never_writes_the_foreign_file(picking, monkeypatch, tmp_path):
    """A transaction's step writes through the fence it was given; the folder is swapped during that write's fsync."""
    _seed(picking)
    shared = picking.shared
    folder = shared.root / PROJECT / "changes"
    folder.mkdir(parents=True)
    target = folder / "record.json"
    target.write_bytes(b'{"n": 0}\n')
    _commit_file(shared, target.relative_to(shared.root).as_posix())
    head = shared.git("rev-parse", "HEAD").stdout.strip()
    moved, foreign = tmp_path / "moved", tmp_path / "foreign"
    fired = {}

    def swap() -> None:
        folder.rename(moved)
        shutil.copytree(moved, foreign, ignore=shutil.ignore_patterns("*.tmp"))
        folder.symlink_to(foreign, target_is_directory=True)
        fired.update(tree=_own_files(moved, Path.read_bytes), git=_git_state(shared))

    def step(_head: str, fence) -> decision_transaction.Step:
        decision_batch.replace_file(target, b'{"n": 1}\n', fence)
        return decision_transaction.Step("written")

    with monkeypatch.context() as m:
        _after_temporary_fsync_in(m, folder, swap)
        with pytest.raises(decision_store.DecisionsUnavailable, match="changed during the write"):
            decision_transaction.transaction(shared, PROJECT, "changes: one", [(target, b'{"n": 1}\n')], step, head)

    assert _tree(foreign, Path.read_bytes) == fired["tree"] == {"record.json": b'{"n": 0}\n'}
    assert _tree(moved, Path.read_bytes) == fired["tree"]  # the owner's files, and none of this write's temporary left
    assert _git_state(shared) == fired["git"]
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _write_with(writer: str, tmp_path: Path, fence) -> Path:
    """Write one new file through *writer* with *fence*; its path."""
    decision = make(title="Use UTC", statement="All timestamps use UTC.")
    layer = tmp_path / "layer"
    path = storage.decision_path(decision, layer)
    path.parent.mkdir(parents=True)
    if writer == "batch":
        decision_batch.replace_file(path, b"the new bytes\n", fence)
    else:
        storage.write(decision, layer, None, fence=fence)
    return path


@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_an_unfenced_write_lands_with_no_temporary_left(tmp_path, writer):
    path = _write_with(writer, tmp_path, None)

    assert path.is_file()
    assert path.stat().st_mode & 0o777 == 0o600  # as the temporary file has always been made
    assert [p.name for p in path.parent.iterdir()] == [path.name]


@pytest.mark.parametrize("case", ["own", "replaced-name", "unknown"])
@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_a_refused_write_removes_only_its_own_temporary(tmp_path, monkeypatch, writer, case):
    """`own`: the refused write's temporary is removed. `replaced-name`: someone else's file now holds that name and is
    left as it is. `unknown`: whether the temporary is still its own cannot be read, so the error is raised.
    """
    folder = tmp_path / "layer" / "decisions"
    owner = b"someone else's file\n"
    seen: list[str] = []
    real_stat = os.stat

    def unreadable(path, *args, **kwargs):
        if kwargs.get("dir_fd") is not None and str(path).endswith(".tmp"):
            raise PermissionError(13, "the folder cannot be read", str(path))
        return real_stat(path, *args, **kwargs)

    def refusing_fence() -> None:
        (temporary,) = [p for p in folder.iterdir() if p.name.endswith(".tmp")]
        seen.append(temporary.name)
        if case == "replaced-name":
            other = folder / "other"
            other.write_bytes(owner)
            other.replace(temporary)  # the same name, now another file
        if case == "unknown":
            scope[0].setattr(os, "stat", unreadable)
        msg = "the fence refused"
        raise RuntimeError(msg)

    error = PermissionError if case == "unknown" else RuntimeError
    scope: list[pytest.MonkeyPatch] = []
    with monkeypatch.context() as m:
        scope.append(m)
        with pytest.raises(error):
            _write_with(writer, tmp_path, refusing_fence)

    left = {p.name: p.read_bytes() for p in folder.iterdir()}
    if case == "own":
        assert left == {}  # neither the destination nor the temporary
    elif case == "replaced-name":
        assert left == {seen[0]: owner}
    else:
        assert list(left) == seen  # not removed while it is unknown whose it is


def _temporaries(folder: Path) -> list[Path]:
    return [p for p in folder.iterdir() if p.name.endswith(".tmp")]


def _substitute(folder: Path, data: bytes) -> str:
    """Put another file, holding *data*, at the name of the one temporary file in *folder*; that name."""
    (temporary,) = _temporaries(folder)
    other = folder / "other"
    other.write_bytes(data)
    other.replace(temporary)
    return temporary.name


@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_a_temporary_name_holding_another_file_when_the_fence_passes_is_never_installed(tmp_path, writer):
    folder = tmp_path / "layer" / "decisions"
    substitute = b"someone else's file\n"
    names: list[str] = []

    def passing_fence_after_a_substitute() -> None:
        names.append(_substitute(folder, substitute))

    with pytest.raises(storage.TemporaryReplacedError):
        _write_with(writer, tmp_path, passing_fence_after_a_substitute)

    assert {p.name: p.read_bytes() for p in folder.iterdir()} == {names[0]: substitute}  # nothing moved or removed


def test_a_save_whose_temporary_name_is_substituted_installs_nothing(picking, monkeypatch):
    """During the save's own write, after its temporary is durable and before its fence, another file takes the name."""
    _seed(picking)
    shared = picking.shared
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    target = shared.root / f"{PROJECT}/decisions/{old.id}.md"
    before, substitute = target.read_bytes(), b"someone else's file\n"
    git, names = _git_state(shared), []

    with monkeypatch.context() as m:
        _after_temporary_fsync(m, storage, target.parent, lambda: names.append(_substitute(target.parent, substitute)))
        with pytest.raises(decision_store.DecisionsUnavailable, match="was replaced"):
            decision_store.save(shared, update, expected_revision=old.revision, message="decisions: one")

    assert target.read_bytes() == before  # the decision is not overwritten by the substitute
    assert (target.parent / names[0]).read_bytes() == substitute  # and the substitute is not removed
    assert _git_state(shared) == git
    assert decision_batch.pending(shared) is None  # nothing of the batch changed, so its put-back settles it
    assert decision_store.load(shared, PROJECT).snapshot.get(old.id).decision.revision == old.revision


@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_a_recreated_temporary_name_is_left_while_the_write_still_holds_its_file_open(tmp_path, monkeypatch, writer):
    """The owner removes the temporary and makes another file at its name; the write's descriptor is still open, so
    that file cannot have the same device and inode, and the cleanup leaves it."""
    folder = tmp_path / "layer" / "decisions"
    recreated = b"the owner's new file\n"
    held: list[tuple[int, tuple[int, int]]] = []
    real_holds = storage.Temporary.holds_name

    def holds_with_a_live_descriptor(self) -> bool:
        found = os.fstat(self.descriptor)  # raises if the descriptor were already closed
        held.append(((found.st_dev, found.st_ino) == self.identity, self.identity))
        return real_holds(self)

    def recreating_fence() -> None:
        (temporary,) = _temporaries(folder)
        temporary.unlink()
        temporary.write_bytes(recreated)
        msg = "the fence refused"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(storage.Temporary, "holds_name", holds_with_a_live_descriptor)
        with pytest.raises(RuntimeError, match="fence refused"):
            _write_with(writer, tmp_path, recreating_fence)

    ((live, identity),) = held
    assert live
    ((name, data),) = [(p, p.read_bytes()) for p in folder.iterdir()]
    assert data == recreated
    found = name.stat()
    assert (found.st_dev, found.st_ino) != identity


@pytest.mark.parametrize("fault", ["first-fstat", "write"])
@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_a_fault_while_the_temporary_is_made_leaks_no_descriptor(tmp_path, monkeypatch, writer, fault):
    """`first-fstat`: the file's identity cannot be read, so its name is left rather than guessed at. `write`: the
    identity is known, so the file is removed. Either way every descriptor is closed and the error is raised."""
    folder = tmp_path / "layer" / "decisions"
    made: list[int] = []
    real_open, real_fstat, real_write = os.open, os.fstat, os.write

    def recording_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is not None and str(path).endswith(".tmp"):
            made.append(descriptor)
        return descriptor

    def failing_fstat(descriptor, *args, **kwargs):
        if fault == "first-fstat" and descriptor in made:
            raise OSError(5, "Input/output error")
        return real_fstat(descriptor, *args, **kwargs)

    def failing_write(descriptor, data):
        if fault == "write" and descriptor in made:
            raise OSError(5, "Input/output error")
        return real_write(descriptor, data)

    open_before = sum(1 for _ in Path("/dev/fd").iterdir())
    with monkeypatch.context() as m:
        m.setattr(os, "open", recording_open)
        m.setattr(os, "fstat", failing_fstat)
        m.setattr(os, "write", failing_write)
        with pytest.raises(OSError, match="Input/output error"):
            _write_with(writer, tmp_path, None)

    assert sum(1 for _ in Path("/dev/fd").iterdir()) == open_before  # every descriptor of the write is closed
    assert made
    left = [p.name for p in folder.iterdir()]
    if fault == "write":
        assert left == []  # its identity was known, so its own file is removed
    else:
        assert len(left) == 1  # whose file the name holds is unknown, so it is left, and the error is raised
        assert left[0].endswith(".tmp")


@pytest.mark.parametrize("writer", ["batch", "decisions"])
def test_a_folder_swapped_after_the_fence_gets_the_rename_and_fsync_in_the_original_folder(
    tmp_path, monkeypatch, writer
):
    """After the fence passes, the owner moves the folder aside and links its path to a foreign folder. The rename and
    its fsync both stay in the folder the temporary was made in; the foreign folder is neither written nor fsynced."""
    folder = tmp_path / "layer" / "decisions"
    moved, foreign = tmp_path / "moved", tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "marker.txt").write_text("foreign\n")
    synced: list[os.stat_result] = []
    real_fsync = os.fsync

    def recording_fsync(descriptor: int) -> None:
        found = os.fstat(descriptor)
        if stat.S_ISDIR(found.st_mode):
            synced.append(found)
        real_fsync(descriptor)

    def fence_then_owner_swaps() -> None:
        folder.rename(moved)
        folder.symlink_to(foreign, target_is_directory=True)

    with monkeypatch.context() as m:
        m.setattr(os, "fsync", recording_fsync)
        path = _write_with(writer, tmp_path, fence_then_owner_swaps)

    assert {p.name for p in moved.iterdir()} == {path.name}  # renamed in the original folder, no temporary left
    assert {p.name: p.read_text() for p in foreign.iterdir()} == {"marker.txt": "foreign\n"}
    assert any(os.path.samestat(found, moved.stat()) for found in synced)
    assert not any(os.path.samestat(found, foreign.stat()) for found in synced)
