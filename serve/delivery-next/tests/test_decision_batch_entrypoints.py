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
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, DecisionError, Link, LinkType, Origin, Scope, State, new_id, storage, write
from owlbear_decisions.storage import serialize
from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.local_system import batch_journal, data_repo, publication_hold, storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.project_host import decision_recovery_routes
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
    real_fsync = os.fsync

    def snapshot_then_fsync(descriptor: int) -> None:
        if os.path.samestat(os.fstat(descriptor), project_folder.stat()):  # the folder held open for the unlink
            seen.append({p.name for p in project_folder.iterdir()})
        real_fsync(descriptor)

    def first_lands_second_refuses(decision, folder, expected=None, **fence):
        if decision.project == "new-site":
            msg = "refused by the test"
            raise DecisionError(msg)
        return real_write(decision, folder, expected, **fence)

    monkeypatch.setattr(os, "fsync", snapshot_then_fsync)
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
    real_read = storage_io.read_regular

    def recording_read(path: Path) -> bytes | None:
        reads.append(path)
        return real_read(path)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "read_regular", recording_read)
        with pytest.raises(decision_store.DecisionsUnavailable, match="differs"):
            decision_recovery.finish(shared, generation)

    assert not [p for p in reads if str(p).startswith((str(folder), str(outside)))]  # no referent behind the link
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
    real_sync = storage_io._sync_held  # noqa: SLF001 - make_dirs' own sync of the folder it holds open

    def final_fsync_then_owner_commits(fd, path):
        real_sync(fd, path)
        if owned is not None and not seen and Path(path) == folder.parent:  # make_dirs' last fsync, both cases
            seen.append("owner")
            (shared.root / rel).write_bytes(owned)
            _commit_file(shared, rel)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "_sync_held", final_fsync_then_owner_commits)
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

    def stopped_in_the_first_fsync(_fd, _path):
        msg = "interrupted in make_dirs' first fsync"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "_sync_held", stopped_in_the_first_fsync)
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

    def stopped_in_the_first_fsync(_fd, _path):
        msg = "interrupted in make_dirs' first fsync"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(storage_io, "_sync_held", stopped_in_the_first_fsync)
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
    real_read, real_bytes, real_scope = storage_io.read_regular, Path.read_bytes, getattr(module, name)
    inside, calls, fired = [False], [0], {}

    def scoped(*args, **kwargs):
        inside[0] = True
        try:
            return real_scope(*args, **kwargs)
        finally:
            inside[0] = False

    def read_then_owner_swaps(path: Path) -> bytes | None:
        data = real_read(path)
        if inside[0] and not fired and path == target:
            calls[0] += 1
            if calls[0] == call:
                folder.rename(moved)
                shutil.copytree(moved, foreign)  # the same bytes, so only the folder chain can tell them apart
                folder.symlink_to(foreign, target_is_directory=True)
                fired.update(tree=_tree(moved, real_bytes), git=_git_state(shared))
        return data

    with monkeypatch.context() as m:
        m.setattr(module, name, scoped)
        m.setattr(storage_io, "read_regular", read_then_owner_swaps)  # every proof's read of a batch file
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
    real_read = storage_io.read_regular
    real_journal = decision_store._journal  # noqa: SLF001
    inside = [False]

    def journal(*args, **kwargs):
        inside[0] = True
        try:
            return real_journal(*args, **kwargs)
        finally:
            inside[0] = False

    def planning_read(path: Path) -> bytes | None:
        data = real_read(path)
        if moment == "planning-read" and inside[0] and path == target:
            swap()
        return data

    m.setattr(decision_store, "_journal", journal)
    m.setattr(storage_io, "read_regular", planning_read)  # the save's planning read, `decision_store._content`
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


def _write_with(writer: str, tmp_path: Path, fence, root: Path | None = None, layer: Path | None = None) -> Path:
    """Write one new file through *writer* with *fence*, or remove an existing one (`remove`); its path.

    *root*, when given, is the trusted folder the writers check every folder up to.
    """
    decision = make(title="Use UTC", statement="All timestamps use UTC.")
    layer = layer or tmp_path / "layer"
    path = storage.decision_path(decision, layer)
    path.parent.mkdir(parents=True)
    if writer == "remove":
        path.write_bytes(b"the old bytes\n")
        decision_batch.replace_file(path, None, fence, root)
    elif writer == "batch":
        decision_batch.replace_file(path, b"the new bytes\n", fence, root)
    else:
        storage.write(decision, layer, None, fence=fence, root=root)
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


@pytest.mark.parametrize("writer", ["batch", "decisions", "remove"])
def test_a_folder_moved_or_linked_away_during_the_fence_changes_nothing_in_either_folder(tmp_path, monkeypatch, writer):
    """While the fence runs, after its own checks, the owner moves the folder aside and links its path to a foreign
    folder. The folder held open no longer is the one the path names, so nothing is renamed, removed or fsynced in
    either: the owner's moved folder keeps what it held, the foreign one is untouched, and no descriptor stays open."""
    folder = tmp_path / "layer" / "decisions"
    moved, foreign = tmp_path / "moved", tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "marker.txt").write_text("foreign\n")
    synced: list[os.stat_result] = []
    real_fsync = os.fsync
    held: dict[str, bytes] = {}

    def recording_fsync(descriptor: int) -> None:
        found = os.fstat(descriptor)
        if stat.S_ISDIR(found.st_mode):
            synced.append(found)
        real_fsync(descriptor)

    def fence_then_owner_swaps() -> None:
        held.update({p.name: p.read_bytes() for p in folder.iterdir() if not p.name.endswith(".tmp")})
        folder.rename(moved)
        folder.symlink_to(foreign, target_is_directory=True)

    open_before = sum(1 for _ in Path("/dev/fd").iterdir())
    with monkeypatch.context() as m:
        m.setattr(os, "fsync", recording_fsync)
        with pytest.raises(storage.FolderMovedError):
            _write_with(writer, tmp_path, fence_then_owner_swaps)

    assert sum(1 for _ in Path("/dev/fd").iterdir()) == open_before
    assert {p.name: p.read_bytes() for p in moved.iterdir()} == held  # nothing renamed or removed, no temporary left
    assert {p.name: p.read_text() for p in foreign.iterdir()} == {"marker.txt": "foreign\n"}
    assert not any(os.path.samestat(found, foreign.stat()) for found in synced)


@pytest.mark.parametrize("swap", [True, False], ids=["swap-during-head-probe", "healthy"])
@pytest.mark.parametrize("surface", ["abandon", "store-put-back", "generic-put-back"])
def test_a_folder_swapped_during_the_fences_head_probe_never_loses_a_file_to_a_removal(
    picking, monkeypatch, tmp_path, surface, swap
):
    """A put-back removes a file the batch added. While its fence reads HEAD, after every path and image check, the
    owner moves the folder aside and links its path to a foreign copy holding the same after bytes. HEAD is unchanged,
    so the fence passes; the removal must still change nothing: the foreign file and the owner's moved files stay,
    Git is as at the swap, the batch stays pending and no reader gets authority. Without the swap it completes."""
    _seed(picking)
    shared = picking.shared
    target, run, _ = _read_swap_surface(picking, monkeypatch, surface)
    folder, moved, foreign = target.parent, tmp_path / "moved", tmp_path / "foreign"
    real_replace, real_git = decision_batch.replace_file, DataRepo.git
    removing, fired = [False], {}

    def scoped_replace(path, data, *fence):
        removing[0] = data is None and path == target
        try:
            return real_replace(path, data, *fence)
        finally:
            removing[0] = False

    def head_probe_then_owner_swaps(self, *args, **kwargs):
        said = real_git(self, *args, **kwargs)
        if swap and removing[0] and not fired and args[:2] == ("rev-parse", "--verify"):
            folder.rename(moved)
            shutil.copytree(moved, foreign)  # the same after bytes, so only the folder's identity tells them apart
            folder.symlink_to(foreign, target_is_directory=True)
            fired.update(tree=_tree(moved, Path.read_bytes), git=_git_state(shared))
        return said

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "replace_file", scoped_replace)
        m.setattr(DataRepo, "git", head_probe_then_owner_swaps)
        refused = ""
        try:
            run()
        except decision_store.DecisionsUnavailable as exc:
            refused = str(exc)

    assert bool(refused) <= bool(fired), refused  # a refusal is only ever this swap's
    if not swap:
        assert not target.exists()
        assert decision_batch.pending(shared) is None
        return
    assert fired
    assert fired["tree"][target.name]  # the file the removal was for is in the owner's moved folder
    assert _tree(foreign, Path.read_bytes) == fired["tree"]  # nothing removed behind the link
    assert _tree(moved, Path.read_bytes) == fired["tree"]  # nor in the folder the owner moved aside
    assert _git_state(shared) == fired["git"]
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


@pytest.mark.parametrize("swap", [True, False], ids=["project-linked-back-during-head-probe", "healthy"])
@pytest.mark.parametrize("surface", ["abandon", "store-put-back", "generic-put-back"])
def test_a_project_folder_linked_back_to_itself_during_the_fences_head_probe_changes_nothing(
    picking, monkeypatch, tmp_path, surface, swap
):
    """While a removal's fence reads HEAD, the owner moves the project folder aside and links its name back to it. The
    file's own folder is still the one held open, but a folder above it is now a link: the removal must change
    nothing. The owner's moved project keeps every byte, Git is as at the swap, the batch stays pending and no reader
    gets authority. Without the swap it completes.
    """
    _seed(picking)
    shared = picking.shared
    target, run, _ = _read_swap_surface(picking, monkeypatch, surface)
    project, moved = shared.root / PROJECT, tmp_path / "moved-project"
    real_replace, real_git = decision_batch.replace_file, DataRepo.git
    removing, fired = [False], {}

    def scoped_replace(path, data, *fence):
        removing[0] = data is None and path == target
        try:
            return real_replace(path, data, *fence)
        finally:
            removing[0] = False

    def head_probe_then_owner_links_back(self, *args, **kwargs):
        said = real_git(self, *args, **kwargs)
        if swap and removing[0] and not fired and args[:2] == ("rev-parse", "--verify"):
            project.rename(moved)
            project.symlink_to(moved, target_is_directory=True)  # back to the owner's own project, same folders below
            fired.update(tree=_files_below(moved), git=_git_state(shared))
        return said

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "replace_file", scoped_replace)
        m.setattr(DataRepo, "git", head_probe_then_owner_links_back)
        refused = ""
        try:
            run()
        except decision_store.DecisionsUnavailable as exc:
            refused = str(exc)

    assert bool(refused) <= bool(fired), refused  # a refusal is only ever this swap's
    if not swap:
        assert not target.exists()
        assert decision_batch.pending(shared) is None
        return
    assert fired
    assert target.relative_to(project).as_posix() in fired["tree"]  # the file the removal was for, in the moved project
    assert _files_below(moved) == fired["tree"]  # the owner's moved project keeps every byte
    assert _git_state(shared) == fired["git"]
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _files_below(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("writer", ["batch", "decisions", "remove"])
def test_a_higher_folder_linked_back_to_itself_during_the_fence_refuses_within_the_root(tmp_path, writer):
    """The trusted root holds `layer/decisions`; during the fence the owner moves `layer` aside and links its name back
    to it. `decisions` is still the folder held open, but `layer` is a link now: nothing is renamed or removed.
    """
    root = tmp_path / "checkout"
    layer, moved = root / "layer", tmp_path / "moved-layer"
    held: dict[str, bytes] = {}

    def fence_then_owner_links_back() -> None:
        held.update({k: v for k, v in _files_below(layer).items() if not k.endswith(".tmp")})
        layer.rename(moved)
        layer.symlink_to(moved, target_is_directory=True)

    with pytest.raises(storage.FolderMovedError):
        _write_with(writer, tmp_path, fence_then_owner_links_back, root, layer)

    assert _files_below(moved) == held  # nothing renamed, removed or left behind in the owner's moved folder


@pytest.mark.parametrize("writer", ["batch", "decisions", "remove"])
def test_a_default_writer_or_a_link_above_the_root_keeps_its_symlink_semantics(tmp_path, writer):
    """Without a root, a writer follows its folder's path through a linked folder as it always has; with one, a link
    above the root, such as an operating system's folder alias, is never checked.
    """
    real, alias = tmp_path / "real", tmp_path / "alias"
    (real / "checkout").mkdir(parents=True)
    alias.symlink_to(real, target_is_directory=True)
    root = alias / "checkout"
    (tmp_path / "linked-real").mkdir()
    (tmp_path / "linked").symlink_to(tmp_path / "linked-real", target_is_directory=True)

    path = _write_with(writer, tmp_path, None, root, root / "layer")
    plain = _write_with(writer, tmp_path / "linked", None, None, tmp_path / "linked" / "layer")

    assert path.exists() == (writer != "remove") == plain.exists()
    assert all(not p.name.endswith(".tmp") for p in tmp_path.rglob("*"))


@pytest.mark.parametrize("lock", ["symlink", "no-permission", "folder"])
def test_a_batch_lock_that_cannot_be_taken_is_an_actionable_refusal_and_changes_nothing(
    picking, monkeypatch, tmp_path, lock
):
    """The interrupted batch's lock is a link to a foreign file, a file nobody may open, or a folder. Every reader
    refuses with the lock named instead of failing: the diagnosis shows it, the store refuses, a lookup gives no
    answer and runs no picker, and the journal, HEAD, index and the foreign file are as they were."""
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Use UTC", statement="All timestamps use UTC.")])
    path = decision_batch.journal_path(shared).parent / decision_batch.LOCK
    journal = decision_batch.journal_path(shared).read_bytes()
    foreign = tmp_path / "foreign.lock"
    foreign.write_bytes(b"foreign\n")
    path.unlink()
    if lock == "symlink":
        path.symlink_to(foreign)
    elif lock == "folder":
        path.mkdir()
    else:
        path.write_bytes(b"")
        path.chmod(0)
    git = _git_state(shared)
    try:
        shown = decision_recovery_routes.diagnosis(shared)
        with pytest.raises(decision_batch.JournalError, match="batch lock"):
            decision_batch.stamp(shared)
        with pytest.raises(decision_store.DecisionsUnavailable, match="batch lock") as refused:
            decision_store.load(shared, PROJECT)
        _no_authority(picking)
    finally:
        if lock == "no-permission":
            path.chmod(0o600)

    assert (shown["interrupted"], shown["corrupt"], shown["generation"]) == (True, True, "")
    assert "batch lock" in shown["diagnosis"]
    assert str(path) in shown["diagnosis"]
    assert refused.value.action == decision_store.RECOVER
    assert decision_batch.journal_path(shared).read_bytes() == journal
    assert foreign.read_bytes() == b"foreign\n"
    assert _git_state(shared) == git


def test_a_healthy_lock_still_reads_and_an_error_of_its_body_is_not_retold(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Use UTC", statement="All timestamps use UTC.")])
    batch = decision_batch.pending(shared)
    assert batch is not None
    with pytest.raises(decision_batch.JournalError, match="in flight"):  # the healthy stamp sees the batch
        decision_batch.stamp(shared)
    assert decision_recovery_routes.diagnosis(shared)["generation"] == batch.generation

    def failing(*_args, **_kwargs):
        msg = "an error of the body, not of taking the lock"
        raise RuntimeError(msg)

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "replace_file", failing)
        with pytest.raises(RuntimeError, match="not of taking the lock"):
            decision_batch.complete(shared, batch.generation)
    assert decision_batch.pending(shared).generation == batch.generation


def _completed_list(shared: DataRepo) -> Path:
    return decision_batch.journal_path(shared).parent / decision_batch.COMPLETED


@pytest.mark.parametrize(
    "listed",
    [b"{not json", b'{"a": 1}', b'["not-a-generation"]', b"[null]", b'["ABCDEF12"]'],
    ids=["not-json", "object", "not-hex", "null", "upper-case"],
)
@pytest.mark.parametrize("writer", ["save", "transaction"])
def test_a_damaged_completed_list_with_no_journal_refuses_every_writer_before_it_changes_anything(
    picking, monkeypatch, writer, listed
):
    _seed(picking)
    shared = picking.shared
    completed = _completed_list(shared)
    completed.write_bytes(listed)
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    target = shared.root / PROJECT / "changes" / "record.json"
    git, seen = _git_state(shared), []
    real_git = DataRepo.git

    def recording_git(self, *args, **kwargs):
        seen.append(args[0] if args else "")
        return real_git(self, *args, **kwargs)

    def step(_head: str, _fence) -> decision_transaction.Step:
        pytest.fail("the step ran")

    def write() -> None:
        if writer == "save":
            decision_store.save(shared, new, expected_revision=None, message="decisions: one")
        else:
            decision_transaction.transaction(shared, PROJECT, "changes: one", [(target, b"{}")], step, git[0])

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", recording_git)
        with pytest.raises(decision_store.DecisionsUnavailable, match="completed decision batches"):
            write()

    assert not {"fetch", "commit", "push", "add", "rebase"} & set(seen)
    assert not decision_batch.journal_path(shared).exists()
    assert not (shared.root / f"{PROJECT}/decisions/{new.id}.md").exists()
    assert not target.exists()
    assert completed.read_bytes() == listed
    assert _git_state(shared) == git
    shown = decision_recovery_routes.diagnosis(shared)
    assert (shown["corrupt"], shown["generation"]) == (True, "")  # diagnosed, and no action offered
    _no_authority(picking)


@pytest.mark.parametrize("listed", [None, b"[]"], ids=["missing", "empty"])
def test_a_missing_or_empty_completed_list_still_lets_a_save_through(picking, listed):
    _seed(picking)
    shared = picking.shared
    completed = _completed_list(shared)
    completed.unlink(missing_ok=True)
    if listed is not None:
        completed.write_bytes(listed)

    assert decision_batch.pending(shared) is None
    receipt = decision_store.save(shared, make(title="Use UTC", statement="UTC."), expected_revision=None, message="m")
    assert receipt.published


@pytest.mark.parametrize("value", [None, "not-a-generation", "ABCDEF12", "a" * 7, "a" * 65, 12345678])
def test_a_journal_whose_generation_cannot_be_named_is_corrupt_and_offers_no_action(picking, monkeypatch, value):
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Use UTC", statement="All timestamps use UTC.")])
    _rewrite_journal(shared, lambda record: record.__setitem__("generation", value))
    journal = decision_batch.journal_path(shared).read_bytes()

    shown = decision_recovery_routes.diagnosis(shared)
    assert (shown["interrupted"], shown["corrupt"], shown["generation"]) == (True, True, "")
    assert "generation" in shown["diagnosis"]
    for action in (decision_recovery.finish, decision_recovery.abandon):
        with pytest.raises(decision_store.DecisionsUnavailable, match="generation"):
            action(shared, "a" * 16)
    assert decision_batch.journal_path(shared).read_bytes() == journal
    _no_authority(picking)


@pytest.mark.parametrize("value", ["a" * 8, "b" * 64], ids=["8", "64"])
def test_a_journal_generation_of_8_to_64_hex_characters_is_recovered_by_it(picking, monkeypatch, value):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")
    _interrupt(picking, monkeypatch, [new])
    assert len(decision_batch.pending(shared).generation) == 32  # a producer's own: a UUID's hex
    _rewrite_journal(shared, lambda record: record.__setitem__("generation", value))

    shown = decision_recovery_routes.diagnosis(shared)
    assert (shown["corrupt"], shown["generation"]) == (False, value)
    assert decision_recovery.abandon(shared, value).done
    assert decision_batch.pending(shared) is None
    assert value in json.loads(_completed_list(shared).read_bytes())


def _successor_and_update(picking, monkeypatch, surface: str) -> tuple[Path, bytes, Path, bytes, object]:
    """A batch adding a successor and updating another file, refused or interrupted, and the call that puts it back:
    the added file and its after image, the updated file and its before image."""
    shared = picking.shared
    if surface == "generic":
        folder = shared.root / PROJECT / "changes"
        folder.mkdir(parents=True)
        updated, added = folder / "kept.json", folder / "added.json"
        updated.write_bytes(b'{"n": 0}\n')
        _commit_file(shared, updated.relative_to(shared.root).as_posix())
        head = shared.git("rev-parse", "HEAD").stdout.strip()
        files = [(added, b'{"new": 1}\n'), (updated, b'{"n": 1}\n')]

        def step(_head: str, _fence) -> decision_transaction.Step:
            for path, data in files:
                path.write_bytes(data)
            return decision_transaction.Step("the commit was refused", refused=True)

        def run() -> None:
            decision_transaction.transaction(shared, PROJECT, "changes: two", files, step, head)

        return added, b'{"new": 1}\n', updated, b'{"n": 0}\n', run
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    successor = make(title="Use UTC", statement="All timestamps use UTC.")
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    folder = shared.root / PROJECT / "decisions"
    added, updated = folder / f"{successor.id}.md", folder / f"{old.id}.md"
    after, before = serialize(successor).encode("utf-8"), updated.read_bytes()
    items = [(successor, None), (update, old.revision)]
    if surface == "store":

        def save() -> None:
            with monkeypatch.context() as m:
                m.setattr(DataRepo, "commit", lambda *_a, **_k: "git refused the commit")
                decision_store.save_all(shared, items, message="decisions: two")

        return added, after, updated, before, save
    generation = _interrupt_at(picking, monkeypatch, items)
    added.write_bytes(after)
    updated.write_bytes(serialize(update).encode("utf-8"))

    def abandon() -> None:
        with pytest.raises(decision_store.DecisionsUnavailable, match="changed while it was put back"):
            decision_recovery.abandon(shared, generation)

    return added, after, updated, before, abandon


@pytest.mark.parametrize("recreate", [True, False], ids=["owner-recreates-during-the-final-probe", "healthy"])
@pytest.mark.parametrize("surface", ["store", "generic", "abandon"])
def test_a_successor_recreated_during_the_final_git_probe_of_a_put_back_keeps_the_batch(
    picking, monkeypatch, surface, recreate
):
    """Every file is put back and proved exactly its before image; then, during the blocking Git probe that follows
    (the staged index for a put-back, the rebase state for Abandon), the owner recreates the removed successor with
    its after image. The batch must stay pending with the owner's file, and no reader gets authority."""
    _seed(picking)
    shared = picking.shared
    added, after, updated, before, run = _successor_and_update(picking, monkeypatch, surface)
    git_state = _git_state(shared)
    proved, fired = [False], []
    real_restored, real_git, real_rebasing = decision_batch.restored, DataRepo.git, DataRepo.rebasing

    def restored(*args, **kwargs):
        proved[0] = real_restored(*args, **kwargs)
        return proved[0]

    def owner_recreates() -> None:
        if recreate and proved[0] and not fired:
            fired.append(True)
            added.write_bytes(after)

    def git(self, *args, **kwargs):
        said = real_git(self, *args, **kwargs)
        if args[:2] == ("diff", "--cached"):
            owner_recreates()
        return said

    def rebasing(self, *args, **kwargs):
        said = real_rebasing(self, *args, **kwargs)
        owner_recreates()
        return said

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "restored", restored)
        m.setattr(DataRepo, "git", git)
        m.setattr(DataRepo, "rebasing", rebasing)
        if surface == "abandon" and not recreate:
            generation = decision_batch.pending(shared).generation
            assert decision_recovery.abandon(shared, generation).done
        else:
            run()

    assert _git_state(shared) == git_state  # nothing committed, staged or undone either way
    assert updated.read_bytes() == before
    if not recreate:
        assert not added.exists()
        assert decision_batch.pending(shared) is None
        return
    assert fired
    assert added.read_bytes() == after  # the owner's file stays
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


THIRD = b"the owner's own third image\n"


def _remote_main(remote: Path) -> str:
    said = subprocess.run(  # noqa: S603 - a fixed git command on the test's own bare repository
        ["git", "--git-dir", str(remote), "rev-parse", "main"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return said.stdout.strip()


def _update_and_successor(picking) -> tuple[list[tuple[Decision, str | None]], Path, bytes]:
    """A save updating a published decision (first) and adding a successor; the updated file and its before image."""
    shared = picking.shared
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
    successor = make(title="Use UTC", statement="All timestamps use UTC.")
    path = shared.root / PROJECT / "decisions" / f"{old.id}.md"
    return [(update, old.revision), (successor, None)], path, path.read_bytes()


@pytest.mark.parametrize("owner", [True, False], ids=["first-file-back-to-before", "healthy"])
def test_a_batch_whose_earlier_file_is_put_back_before_the_commit_is_never_committed(
    picking, shared_repo, monkeypatch, owner
):
    """While the later file is written, the owner puts the earlier one back to its before image: the fence allows
    either image, but nothing incomplete may be committed or pushed, so the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, first, before = _update_and_successor(picking)
    local, published = shared.git("rev-parse", "HEAD").stdout, _remote_main(remote)
    real_write, calls = decision_store.write, []

    def second_write_after_the_owner(decision, folder, expected=None, **kwargs):
        calls.append(decision.id)
        if owner and len(calls) == 2:
            first.write_bytes(before)
        return real_write(decision, folder, expected, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write", second_write_after_the_owner)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    if not owner:
        assert all(r.published for r in receipts)
        assert _remote_main(remote) != published
        assert decision_batch.pending(shared) is None
        return
    assert not any(r.saved for r in receipts)
    assert "journalled image" in receipts[0].notice
    assert (shared.git("rev-parse", "HEAD").stdout, _remote_main(remote)) == (local, published)  # nothing committed
    assert first.read_bytes() == before
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _owner_changes_the_first_path_before_the_commit(m: pytest.MonkeyPatch, fired: list[Path]) -> None:
    """Just before Git stages and commits, the owner writes a third image into the first file to be committed."""
    real_commit = DataRepo.commit

    def commit(self, paths, message, until=None):
        first = [paths] if isinstance(paths, Path) else list(paths)
        if not fired:
            fired.append(first[0])
            first[0].write_bytes(THIRD)
        return real_commit(self, paths, message, until)

    m.setattr(DataRepo, "commit", commit)


@pytest.mark.parametrize("owner", [True, False], ids=["owner-changes-a-file-as-it-is-staged", "healthy"])
@pytest.mark.parametrize("surface", ["store", "finish"])
def test_a_commit_that_does_not_hold_the_batch_is_never_pushed(picking, shared_repo, monkeypatch, surface, owner):
    """The owner changes a file between the check of the worktree and Git staging it, so the commit holds a third
    image. That commit stays local and unpushed, the owner's bytes stay, and the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    if surface == "finish":
        generation = _interrupt_at(picking, monkeypatch, items)
    published, fired = _remote_main(remote), []

    with monkeypatch.context() as m:
        if owner:
            _owner_changes_the_first_path_before_the_commit(m, fired)
        if surface == "store":
            receipts = decision_store.save_all(shared, items, message="decisions: two")
            done = all(r.published for r in receipts)
        else:
            done = decision_recovery.finish(shared, generation).done

    if not owner:
        assert done
        assert _remote_main(remote) != published
        assert decision_batch.pending(shared) is None
        return
    assert not done
    assert _remote_main(remote) == published  # nothing pushed
    assert shared.git("show", f"HEAD:{fired[0].relative_to(shared.root).as_posix()}").stdout.encode() == THIRD
    assert fired[0].read_bytes() == THIRD  # the owner's bytes, committed locally, are kept
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def test_a_commit_rebased_into_one_that_does_not_hold_the_batch_is_never_pushed(picking, shared_repo, monkeypatch):
    """The first push is refused, the commit is rebased on the remote, and the owner then commits a third image over
    it. The rebased head is checked before its push: nothing of it is pushed and the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, first, _ = _update_and_successor(picking)
    other = shared.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True)  # noqa: S603, S607
    real_push, real_rebase, pushes = DataRepo.git, DataRepo.rebase, []

    def first_push_refused(self, *args, **kwargs):
        if args[:1] == ("push",) and not pushes:
            pushes.append(1)  # another clone publishes first, so this push is refused
            (other / "unrelated.txt").write_text("another clone\n")
            for step in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "other"]):
                subprocess.run(["git", *step], cwd=other, check=True)  # noqa: S603, S607
            subprocess.run(["git", "push", "-q"], cwd=other, check=True)  # noqa: S607
        return real_push(self, *args, **kwargs)

    def rebase_then_owner_commits(self, until=None, *guard):
        said = real_rebase(self, until, *guard)
        first.write_bytes(THIRD)
        self.git("commit", "-qam", "the owner's own commit")
        return said

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", first_push_refused)
        m.setattr(DataRepo, "rebase", rebase_then_owner_commits)
        receipts = decision_store.save_all(shared, items, message="decisions: two")
    published = _remote_main(remote)

    assert pushes
    assert not any(r.saved for r in receipts)
    assert "not pushed" in receipts[0].notice
    other_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other, check=True, capture_output=True, text=True)  # noqa: S607
    assert published == other_head.stdout.strip()  # the remote holds only the other clone's commit
    assert first.read_bytes() == THIRD
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def _lock_breaks_at_completion(m: pytest.MonkeyPatch, shared: DataRepo) -> None:
    """The batch lock becomes a link just before the batch would complete, so taking it fails for real."""
    real_complete = decision_batch.complete

    def complete(repo, generation):
        lock = decision_batch.journal_path(shared).parent / decision_batch.LOCK
        lock.unlink(missing_ok=True)
        lock.symlink_to(shared.root.parent / "elsewhere.lock")
        return real_complete(repo, generation)

    m.setattr(decision_batch, "complete", complete)


def test_a_lock_failing_at_completion_is_a_recovery_refusal_not_a_server_error(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    items, _, _ = _update_and_successor(picking)
    generation = _interrupt_at(picking, monkeypatch, items)
    app = FastAPI()
    app.include_router(decision_recovery_routes.router(lambda: shared, []))
    client = TestClient(app)

    with monkeypatch.context() as m:
        _lock_breaks_at_completion(m, shared)
        said = client.post("/decisions/recovery/abandon", json={"generation": generation, "confirmed": True})

    assert said.status_code == 409
    assert "batch lock" in said.json()["detail"]
    assert decision_store.RECOVER in said.json()["detail"]
    assert json.loads(decision_batch.journal_path(shared).read_bytes())["generation"] == generation  # left as it was


def test_a_lock_failing_when_a_published_save_completes_is_a_recovery_refusal(picking, shared_repo, monkeypatch):
    _seed(picking)
    shared = picking.shared
    new = make(title="Use UTC", statement="All timestamps use UTC.")

    with monkeypatch.context() as m:
        _lock_breaks_at_completion(m, shared)
        with pytest.raises(decision_store.DecisionsUnavailable, match="batch lock") as refused:
            decision_store.save(shared, new, expected_revision=None, message="decisions: one")

    assert refused.value.action == decision_store.RECOVER
    assert json.loads(decision_batch.journal_path(shared).read_bytes())["ids"] == [new.id]  # still journalled
    assert _remote_main(shared_repo[1]) == shared.git("rev-parse", "HEAD").stdout.strip()  # published, not completed


def _owner_commits_as_git_pushes(m: pytest.MonkeyPatch, first: Path, at: int, pushes: list, before=None) -> None:
    """At the *at*-th push, after every check and HEAD's last read, the owner commits a third image on top of HEAD;
    only then does Git run the push. Each push's arguments are recorded; *before* runs ahead of the first push."""
    real_git = DataRepo.git

    def git(self, *args, **kwargs):
        if args[:1] == ("push",):
            pushes.append(args)
            if len(pushes) == 1 and before is not None:
                before()
            if len(pushes) == at:
                first.write_bytes(THIRD)
                real_git(self, "commit", "-qam", "the owner's own commit")
        return real_git(self, *args, **kwargs)

    m.setattr(DataRepo, "git", git)


def _owner_commit_kept_unpublished(shared: DataRepo, remote: Path, first: Path, pushes: list) -> str:
    """The pushed commit is HEAD's parent, named by its id in the refspec; the owner's commit stays local only."""
    local = shared.git("rev-parse", "HEAD").stdout.strip()
    sent = _remote_main(remote)
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "the owner's own commit"
    assert sent == shared.git("rev-parse", "HEAD~1").stdout.strip()
    assert pushes[-1][-1] == f"{sent}:refs/heads/main"  # the refspec names the commit checked, not HEAD
    assert shared.git("merge-base", "--is-ancestor", local, sent).returncode  # the owner's commit was not sent
    assert first.read_bytes() == THIRD
    assert shared.git("status", "--porcelain").stdout == ""  # the owner's commit, index and worktree as they were
    return sent


def test_an_owner_commit_made_as_git_pushes_a_batch_is_never_sent(picking, shared_repo, monkeypatch):
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, first, _ = _update_and_successor(picking)
    pushes: list = []

    with monkeypatch.context() as m:
        _owner_commits_as_git_pushes(m, first, 1, pushes)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    sent = _owner_commit_kept_unpublished(shared, remote, first, pushes)
    rel = first.relative_to(shared.root).as_posix()
    assert shared.git("show", f"{sent}:{rel}").stdout.encode() == serialize(items[0][0]).encode()  # the whole batch
    assert not any(r.saved for r in receipts)  # HEAD no longer holds the batch, so it is not proved landed
    assert decision_batch.pending(shared) is not None


def test_an_owner_commit_made_as_git_pushes_a_rebased_batch_is_never_sent(picking, shared_repo, monkeypatch):
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, first, _ = _update_and_successor(picking)
    other = shared.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True)  # noqa: S603, S607
    pushes: list = []

    def another_clone_publishes_first() -> None:  # so the first push is refused and the batch is rebased
        (other / "unrelated.txt").write_text("another clone\n")
        for step in (
            ["add", "-A"],
            ["-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "o"],
            ["push", "-q"],
        ):
            subprocess.run(["git", *step], cwd=other, check=True)  # noqa: S603, S607

    with monkeypatch.context() as m:
        _owner_commits_as_git_pushes(m, first, 2, pushes, another_clone_publishes_first)
        decision_store.save_all(shared, items, message="decisions: two")

    assert len(pushes) == 2  # refused, then the rebased commit
    _owner_commit_kept_unpublished(shared, remote, first, pushes)
    assert (shared.root / "unrelated.txt").exists()  # rebased on the other clone's commit
    assert decision_batch.pending(shared) is not None


def test_proving_a_head_sends_that_head_and_not_an_owner_commit_made_as_git_pushes(picking, shared_repo, monkeypatch):
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    first = shared.root / "notes.txt"
    first.write_text("an unpublished commit\n")
    shared.git("add", "-A")
    shared.git("commit", "-qm", "unpublished")
    head = shared.git("rev-parse", "HEAD").stdout.strip()
    pushes: list = []

    with monkeypatch.context() as m:
        _owner_commits_as_git_pushes(m, first, 1, pushes)
        assert decision_sync.proved(shared, head, time.monotonic() + 60)

    assert _owner_commit_kept_unpublished(shared, remote, first, pushes) == head


def _owner_unrelated_commit(shared: DataRepo) -> str:
    """The owner commits a file of their own, leaving every decision file as it is; that commit."""
    (shared.root / "owner.txt").write_text("the owner's own work\n")
    shared.git("add", "owner.txt")
    shared.git("commit", "-qm", "the owner's own commit")
    return shared.git("rev-parse", "HEAD").stdout.strip()


def _owner_commit_not_sent(shared: DataRepo, remote: Path, published: str, owner: str) -> None:
    assert _remote_main(remote) == published  # nothing of this save or the owner's is pushed
    assert shared.git("rev-parse", "HEAD").stdout.strip() == owner  # the owner's commit stays, as made
    assert shared.git("status", "--porcelain").stdout == ""
    assert decision_batch.pending(shared) is not None


@pytest.mark.parametrize("case", ["owner-commits-after-the-batch", "healthy", "no-op-save"])
def test_only_this_saves_own_commit_or_its_unchanged_head_is_pushed(picking, shared_repo, monkeypatch, case):
    """The owner commits an unrelated file after the batch's commit, before HEAD is read: HEAD keeps every after
    image, but it is not provably this save's commit, so nothing is pushed. A healthy save and a save that changes
    nothing publish as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    old = make(title="Notes stay in one table")
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    decision = old if case == "no-op-save" else old.model_copy(update={"title": "Notes stay in one SQLite table"})
    published, owner = _remote_main(remote), []
    real_commit = DataRepo.commit

    def commit_then_owner_commits(self, *args, **kwargs):
        said = real_commit(self, *args, **kwargs)
        owner.append(_owner_unrelated_commit(self))
        return said

    with monkeypatch.context() as m:
        if case == "owner-commits-after-the-batch":
            m.setattr(DataRepo, "commit", commit_then_owner_commits)
        receipt = decision_store.save(shared, decision, expected_revision=old.revision, message="decisions: one")

    if case != "owner-commits-after-the-batch":
        assert receipt.published
        assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip()
        assert (_remote_main(remote) == published) == (case == "no-op-save")
        assert decision_batch.pending(shared) is None
        return
    assert not receipt.saved
    assert "not provably its own" in receipt.notice
    _owner_commit_not_sent(shared, remote, published, owner[0])
    _no_authority(picking)


@pytest.mark.parametrize("owner", [True, False], ids=["owner-commits-after-the-rebase", "healthy-rebase"])
def test_a_rebased_head_that_is_not_this_saves_own_commit_is_never_pushed(picking, shared_repo, monkeypatch, owner):
    """The first push is refused, the batch's commit is rebased on the remote, and the owner then commits an unrelated
    file: HEAD keeps every after image but is not the rebased commit, so nothing is pushed. Without the owner's
    commit, the rebased batch is published."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    other = shared.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True)  # noqa: S603, S607
    pushes, made = [], []
    real_git, real_rebase = DataRepo.git, DataRepo.rebase

    def first_push_refused(self, *args, **kwargs):
        if args[:1] == ("push",) and not pushes:
            pushes.append(1)
            (other / "unrelated.txt").write_text("another clone\n")
            for step in (
                ["add", "-A"],
                ["-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "o"],
                ["push", "-q"],
            ):
                subprocess.run(["git", *step], cwd=other, check=True)  # noqa: S603, S607
        return real_git(self, *args, **kwargs)

    def rebase_then_owner_commits(self, until=None, *guard):
        said = real_rebase(self, until, *guard)
        if owner:
            made.append(_owner_unrelated_commit(self))
        return said

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", first_push_refused)
        m.setattr(DataRepo, "rebase", rebase_then_owner_commits)
        receipts = decision_store.save_all(shared, items, message="decisions: two")
    other_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other, check=True, capture_output=True, text=True)  # noqa: S607

    if not owner:
        assert all(r.published for r in receipts)
        assert shared.git("rev-parse", "HEAD~1").stdout.strip() == other_head.stdout.strip()
        assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip()
        return
    assert not any(r.saved for r in receipts)
    assert "not provably this save's commit" in receipts[0].notice
    _owner_commit_not_sent(shared, remote, other_head.stdout.strip(), made[0])
    _no_authority(picking)


@pytest.mark.parametrize("state", ["interrupted", "corrupt", "settled"])
def test_ordinary_shared_publication_waits_while_a_decision_batch_is_unsettled(
    picking, shared_repo, monkeypatch, state
):
    """A batch left an incomplete commit local and stays interrupted, or its journal is damaged: a settings save
    commits but neither pushes nor rebases, so no other clone reads that commit as settled. With no batch in flight
    it publishes as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    if state != "settled":
        with monkeypatch.context() as m:
            _owner_changes_the_first_path_before_the_commit(m, [])
            decision_store.save_all(shared, items, message="decisions: two")  # committed, never pushed
        if state == "corrupt":
            decision_batch.journal_path(shared).write_text("{not json")
    published, local = _remote_main(remote), shared.git("rev-parse", "HEAD").stdout.strip()
    settings = shared.root / "settings-note.txt"
    settings.write_text("a setting\n")

    with shared.locked():
        said = shared.publish(settings, "settings: a note")
        pulled = shared.pull()

    if state == "settled":
        assert (said, pulled) == ("", "")
        assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip() != published
        return
    expected = "is interrupted" if state == "interrupted" else "cannot be read"
    assert expected in said
    assert expected in pulled
    assert _remote_main(remote) == published  # neither the incomplete batch nor the setting is sent
    assert shared.git("rev-parse", "HEAD~1").stdout.strip() == local  # the setting is committed on top, locally
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "settings: a note"


def test_a_finish_committed_here_whose_push_fails_says_so(picking, shared_repo, monkeypatch, tmp_path):
    """A fresh Finish commits and proves the batch locally, but its push fails: it completes, and its notice says
    the remote does not have it yet instead of reporting it published."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    generation = _interrupt_at(picking, monkeypatch, items)
    published, away = _remote_main(remote), tmp_path / "remote-away"
    real_publish = decision_sync.publish

    def publish_while_the_remote_is_gone(*args, **kwargs):
        remote.rename(away)
        try:
            return real_publish(*args, **kwargs)
        finally:
            away.rename(remote)

    with monkeypatch.context() as m:
        m.setattr(decision_sync, "publish", publish_while_the_remote_is_gone)
        done = decision_recovery.finish(shared, generation)

    assert done.done
    assert done.notice.startswith("finished here, but not yet on the remote")
    assert "push failed" in done.notice
    assert _remote_main(remote) == published
    assert decision_batch.pending(shared) is None


def test_an_owner_commit_made_while_the_push_is_refused_is_never_rebased(picking, shared_repo, monkeypatch):
    """Another clone publishes first, so the batch commit B's exact push is refused; while that push runs the owner
    commits C on B. Nothing is rebased: C keeps its own id, HEAD, index and bytes, the remote holds only the other
    clone's commit, and the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    other = shared.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True)  # noqa: S603, S607
    owner, rebased, pushes = [], [], []
    real_git, real_rebase = DataRepo.git, DataRepo.rebase

    def push_refused_while_the_owner_commits(self, *args, **kwargs):
        if args[:1] == ("push",) and not pushes:
            pushes.append(args)
            (other / "unrelated.txt").write_text("another clone\n")
            for step in (
                ["add", "-A"],
                ["-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "o"],
                ["push", "-q"],
            ):
                subprocess.run(["git", *step], cwd=other, check=True)  # noqa: S603, S607
            owner.append((real_git(self, "rev-parse", "HEAD").stdout.strip(), _owner_unrelated_commit(self)))
        return real_git(self, *args, **kwargs)

    def recording_rebase(self, until=None, *guard):
        rebased.append(1)
        return real_rebase(self, until, *guard)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", push_refused_while_the_owner_commits)
        m.setattr(DataRepo, "rebase", recording_rebase)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    ((batch_commit, owner_commit),) = owner
    other_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other, check=True, capture_output=True, text=True)  # noqa: S607
    assert pushes[0][-1] == f"{batch_commit}:refs/heads/main"  # B's exact push was the one refused
    assert rebased == []  # nothing was replayed
    assert not any(r.saved for r in receipts)
    assert "nothing is rebased" in receipts[0].notice
    assert shared.git("rev-parse", "HEAD").stdout.strip() == owner_commit  # C keeps its own id
    assert shared.git("rev-parse", "HEAD~1").stdout.strip() == batch_commit
    assert shared.git("status", "--porcelain").stdout == ""
    assert (shared.root / "owner.txt").read_text() == "the owner's own work\n"
    assert _remote_main(remote) == other_head.stdout.strip()
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


@pytest.mark.parametrize("owner", ["unrelated-file", "the-batch-files"])
def test_an_owner_commit_before_publication_is_never_adopted_as_the_batch_base(
    picking, shared_repo, monkeypatch, owner
):
    """After the batch's last write and before its publication reads HEAD, the owner commits: an unrelated file, or
    the batch's own files as written. HEAD then holds every after image or sits on top of them, but it is not the
    batch's journalled head, so nothing is staged, committed or pushed and the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    published, made, committed = _remote_main(remote), [], []
    real_ready, real_commit = decision_sync._ready, DataRepo.commit  # noqa: SLF001

    def owner_commits_then_ready(repo, until):
        if not made:
            if owner == "unrelated-file":
                made.append(_owner_unrelated_commit(repo))
            else:
                repo.git("add", "-A", "--", PROJECT)
                repo.git("commit", "-qm", "the owner commits the batch's files")
                made.append(repo.git("rev-parse", "HEAD").stdout.strip())
        return real_ready(repo, until)

    def recording_commit(self, *args, **kwargs):
        committed.append(args)
        return real_commit(self, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(decision_sync, "_ready", owner_commits_then_ready)
        m.setattr(DataRepo, "commit", recording_commit)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert not any(r.saved for r in receipts)
    assert "moved past the batch's head" in receipts[0].notice
    assert committed == []  # nothing staged or committed by the publisher
    assert _remote_main(remote) == published  # nothing pushed, the owner's commit included
    assert shared.git("rev-parse", "HEAD").stdout.strip() == made[0]  # the owner's commit stays, as made
    assert shared.git("diff", "--cached", "--name-only").stdout == ""  # the index is the owner's
    if owner == "unrelated-file":  # the batch's files stay written, uncommitted
        changed = shared.git("status", "--porcelain").stdout
        assert all(f"{d.id}.md" in changed for d, _ in items)
    else:
        assert shared.git("status", "--porcelain").stdout == ""
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


@pytest.mark.parametrize("name", ["journal", "completed"])
def test_a_dangling_link_at_the_journal_or_its_completed_list_holds_every_writer(
    picking, shared_repo, monkeypatch, tmp_path, name
):
    """A link to nothing at the journal's name, or at its completed list's, is damage, never a missing file: no
    decision is saved, no ordinary publication pushes or rebases, no reader answers, and the link is left as it is."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    journal = decision_batch.journal_path(shared)
    at = journal if name == "journal" else _completed_list(shared)
    at.parent.mkdir(parents=True, exist_ok=True)
    at.unlink(missing_ok=True)
    nowhere = tmp_path / "nowhere"
    at.symlink_to(nowhere)
    published, git, seen = _remote_main(remote), _git_state(shared), []
    real_git = DataRepo.git

    def recording_git(self, *args, **kwargs):
        seen.append(args[0] if args else "")
        return real_git(self, *args, **kwargs)

    new = make(title="Use UTC", statement="All timestamps use UTC.")
    with pytest.raises(decision_batch.JournalError, match="cannot be read"):
        decision_batch.pending(shared)
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", recording_git)
        with pytest.raises(decision_store.DecisionsUnavailable):
            decision_store.save(shared, new, expected_revision=None, message="decisions: one")
    assert not {"fetch", "commit", "push", "add", "rebase"} & set(seen)
    assert not (shared.root / f"{PROJECT}/decisions/{new.id}.md").exists()
    assert _git_state(shared) == git

    settings = shared.root / "settings-note.txt"
    settings.write_text("a setting\n")
    with shared.locked():
        said, pulled = shared.publish(settings, "settings: a note"), shared.pull()
    assert "cannot be read" in said
    assert "cannot be read" in pulled
    assert _remote_main(remote) == published  # the setting is committed here, never pushed
    assert at.is_symlink()
    assert at.readlink() == nowhere
    assert not nowhere.exists()
    _no_authority(picking)


def _git_in(where: Path, *args: str) -> str:
    said = subprocess.run(["git", *args], cwd=where, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return said.stdout.strip()


def _second_remote(shared: DataRepo, tmp_path: Path) -> Path:
    """A second remote, ``elsewhere``, whose branch ``side`` is at HEAD and which a local ``side`` follows."""
    elsewhere = tmp_path / "elsewhere.git"
    _git_in(tmp_path, "init", "-q", "--bare", "-b", "main", str(elsewhere))
    shared.git("remote", "add", "elsewhere", str(elsewhere))
    shared.git("branch", "-q", "side")
    _git_in(shared.root, "push", "-q", "-u", "elsewhere", "side")  # the owner's setup, as the owner runs it
    return elsewhere


def _push_refused_and_owner_branches(m: pytest.MonkeyPatch, remote: Path, other: Path, rebased: list) -> None:
    """As the first push starts, another clone moves the remote on, so it is refused, and the owner checks out a new
    branch at the refused commit, following ``elsewhere/side``; every rebase is recorded."""
    real_git = DataRepo.git

    def push_refused_and_owner_branches(self, *args, **kwargs):
        if args[:1] == ("push",) and not other.exists():
            _git_in(other.parent, "clone", "-q", str(remote), str(other))
            (other / "unrelated.txt").write_text("another clone\n")
            _git_in(other, "add", "-A")
            _git_in(other, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "o")
            _git_in(other, "push", "-q")
            real_git(self, "checkout", "-q", "-b", "side2", "--track", "elsewhere/side")
            real_git(self, "reset", "-q", "--keep", "main")  # the owner's new branch sits at the refused commit
        if args[:1] == ("rebase",):
            rebased.append(args)
        return real_git(self, *args, **kwargs)

    m.setattr(DataRepo, "git", push_refused_and_owner_branches)


@pytest.mark.parametrize("case", ["checked-out-after-the-proof", "branched-before-the-rebase", "side-branch-healthy"])
def test_a_publication_goes_where_it_began_whatever_branch_is_checked_out_later(
    picking, shared_repo, monkeypatch, tmp_path, case
):
    """A save's commit is pushed to the remote branch the checkout followed when its publication began. The owner
    checks out another branch, at the same commit and following another remote's branch a push could fast-forward,
    after the commit is proved, or makes one at the refused commit before the rebase: nothing reaches that other
    remote, and nothing is rebased. A save begun on a branch following another remote publishes there."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    elsewhere = _second_remote(shared, tmp_path)
    if case == "side-branch-healthy":
        shared.git("checkout", "-q", "side")
    published, side = _remote_main(remote), _git_in(tmp_path, "--git-dir", str(elsewhere), "rev-parse", "side")
    other, rebased = tmp_path / "other", []
    real_unproved = decision_sync._unproved  # noqa: SLF001

    def proved_then_owner_checks_out(repo, *args, **kwargs):
        said = real_unproved(repo, *args, **kwargs)
        repo.git("checkout", "-q", "side")
        return said

    with monkeypatch.context() as m:
        if case == "checked-out-after-the-proof":
            m.setattr(decision_sync, "_unproved", proved_then_owner_checks_out)
        if case == "branched-before-the-rebase":
            _push_refused_and_owner_branches(m, remote, other, rebased)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    on_side = _git_in(tmp_path, "--git-dir", str(elsewhere), "rev-parse", "side")
    if case == "side-branch-healthy":
        assert all(r.published for r in receipts)
        assert on_side == shared.git("rev-parse", "HEAD").stdout.strip() != side
        assert _remote_main(remote) == published
        assert decision_batch.pending(shared) is None
        return
    assert on_side == side  # the other remote's branch is never fast-forwarded to this save's commit
    if case == "checked-out-after-the-proof":
        batch = shared.git("rev-parse", "main").stdout.strip()
        assert shared.git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/side"  # the owner's checkout stays
        assert shared.git("rev-parse", "HEAD").stdout.strip() == side
        assert _remote_main(remote) == batch  # the commit proved, sent where the publication began
        assert not any(r.saved for r in receipts)  # the owner's checkout no longer holds the batch: held for Finish
        assert f"published as {batch[:12]}, but HEAD moved past it" in receipts[0].notice
        assert decision_batch.pending(shared) is not None
        return
    assert rebased == []
    assert not any(r.saved for r in receipts)
    assert "left the branch or repository it was published from" in receipts[0].notice
    assert shared.git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/side2"
    assert shared.git("rev-parse", "HEAD").stdout.strip() == shared.git("rev-parse", "main").stdout.strip()
    assert _remote_main(remote) == _git_in(other, "rev-parse", "HEAD")  # only the other clone's commit
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


def test_an_owner_commit_of_the_batch_files_during_its_checks_is_never_pushed_as_a_no_op_save(
    picking, shared_repo, monkeypatch
):
    """After the publication proved HEAD is the batch's head, and while it checks the batch's after images, the owner
    commits the batch's files: the publisher's commit then makes nothing, so HEAD is the owner's commit, not this
    save's and not the head it began on; nothing is pushed, the owner's commit stays and the batch stays interrupted."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    published, made = _remote_main(remote), []
    real_journalled = decision_sync._journalled  # noqa: SLF001

    def checked_while_the_owner_commits(repo, *args, **kwargs):
        said = real_journalled(repo, *args, **kwargs)
        repo.git("add", "-A", "--", PROJECT)
        repo.git("commit", "-qm", "the owner commits the batch's files")
        made.append(repo.git("rev-parse", "HEAD").stdout.strip())
        return said

    with monkeypatch.context() as m:
        m.setattr(decision_sync, "_journalled", checked_while_the_owner_commits)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert not any(r.saved for r in receipts)
    assert "not provably its own" in receipts[0].notice
    _owner_commit_not_sent(shared, remote, published, made[0])
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "the owner commits the batch's files"
    _no_authority(picking)


def _is_commit(args: tuple[str, ...]) -> bool:
    return "commit" in args[:3] and "--amend" not in args


@pytest.mark.parametrize("case", ["owner-amends-the-commit-git-made", "git-names-no-commit", "healthy"])
def test_the_commit_a_save_made_is_the_one_git_named_never_head_read_afterwards(
    picking, shared_repo, monkeypatch, case
):
    """Git makes the batch's commit B; before anything reads HEAD, the owner amends it into C, with the same parent and
    tree but another message. C holds every after image and changes only the batch's files, yet it is not the commit
    this save made, so nothing is pushed. A commit Git does not name is never guessed either; a healthy save
    publishes as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    published, made = _remote_main(remote), []
    real_git = data_repo._git  # noqa: SLF001

    def commit_then_owner_amends(cwd, *args, **kwargs):
        said = real_git(cwd, *args, **kwargs)
        if _is_commit(args) and not made:
            made.append(real_git(cwd, "rev-parse", "HEAD").stdout.strip())
            if case == "git-names-no-commit":
                return subprocess.CompletedProcess(said.args, 0, "", said.stderr)
            real_git(cwd, "commit", "-q", "--amend", "-m", "the owner rewords the batch's commit")
            made.append(real_git(cwd, "rev-parse", "HEAD").stdout.strip())
        return said

    with monkeypatch.context() as m:
        if case != "healthy":
            m.setattr(data_repo, "_git", commit_then_owner_amends)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    if case == "healthy":
        assert all(r.published for r in receipts)
        assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip() != published
        assert decision_batch.pending(shared) is None
        return
    assert not any(r.saved for r in receipts)
    said = "did not name the commit" if case == "git-names-no-commit" else "not provably its own"
    assert said in receipts[0].notice
    _owner_commit_not_sent(shared, remote, published, made[-1])
    if case == "owner-amends-the-commit-git-made":
        assert made[0] != made[1]
        assert shared.git("rev-parse", "HEAD^{tree}").stdout == shared.git("rev-parse", f"{made[0]}^{{tree}}").stdout
        assert shared.git("log", "-1", "--format=%s").stdout.strip() == "the owner rewords the batch's commit"
    _no_authority(picking)


@pytest.mark.parametrize("case", ["owner-commits-the-staged-batch", "commit-refused-head-unchanged"])
def test_a_failed_commit_never_adopts_a_commit_made_meanwhile(picking, shared_repo, monkeypatch, case):
    """The batch's files are staged, then the owner commits exactly them, so the save's own commit fails with nothing
    to commit: HEAD is a child of the batch's head holding every after image, but no commit of this save's, so
    nothing is pushed and the batch stays interrupted. A commit refused while HEAD stays put is still a known refusal
    whose batch stays interrupted for Finish or Abandon."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    published, head, made = _remote_main(remote), shared.git("rev-parse", "HEAD").stdout.strip(), []
    real_stage, real_git = DataRepo._stage, data_repo._git  # noqa: SLF001

    def staged_then_owner_commits(self, rels, until):
        said = real_stage(self, rels, until)
        self.git("commit", "-qm", "the owner commits the staged batch")
        made.append(self.git("rev-parse", "HEAD").stdout.strip())
        return said

    def commit_refused(cwd, *args, **kwargs):
        if _is_commit(args):
            return subprocess.CompletedProcess(["git", *args], 1, "", "refused by a hook")
        return real_git(cwd, *args, **kwargs)

    with monkeypatch.context() as m:
        if case == "owner-commits-the-staged-batch":
            m.setattr(DataRepo, "_stage", staged_then_owner_commits)
        else:
            m.setattr(data_repo, "_git", commit_refused)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert not any(r.saved for r in receipts)
    assert _remote_main(remote) == published
    if case == "commit-refused-head-unchanged":
        assert "refused by a hook" in receipts[0].notice
        assert shared.git("rev-parse", "HEAD").stdout.strip() == head
        assert "HEAD moved" not in receipts[0].notice  # a known refusal, never an index undo: Finish or Abandon it
        assert decision_batch.pending(shared) is not None
        return
    assert "HEAD moved meanwhile" in receipts[0].notice
    _owner_commit_not_sent(shared, remote, published, made[0])
    assert shared.git("rev-parse", "HEAD~1").stdout.strip() == head
    _no_authority(picking)


def test_hook_output_never_names_the_commit_a_save_made(picking, shared_repo):
    """Hooks that print a summary line of their own, naming another commit, do not change which commit Git names:
    the save's commit is published as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    head = shared.git("rev-parse", "HEAD").stdout.strip()
    hooks = Path(shared.git("rev-parse", "--absolute-git-dir").stdout.strip()) / "hooks"
    hooks.mkdir(exist_ok=True)
    for name in ("pre-commit", "commit-msg", "post-commit"):
        (hooks / name).write_text(f'#!/bin/sh\necho "[main {head}] {name} prints a summary of its own"\n')
        (hooks / name).chmod(0o755)

    receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert all(r.published for r in receipts)
    assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip() != head
    assert decision_batch.pending(shared) is None


def _unrelated_commit_of_the_after_images(shared: DataRepo, files) -> str:
    """The batch's after images written and committed with no parent: same tree, unrelated to the journalled head."""
    for rel, _, after in files:
        (shared.root / rel).write_bytes(after)
    shared.git("add", "-A")
    tree = shared.git("write-tree").stdout.strip()
    orphan = shared.git("commit-tree", tree, "-m", "the owner's unrelated commit").stdout.strip()
    shared.git("reset", "-q", "--soft", orphan)  # in the test's throwaway clone: HEAD is the unrelated commit
    return orphan


@pytest.mark.parametrize(
    "value", ["HEAD", "refs/heads/main", "abc1234", "A" * 40, 1234567, None],
    ids=["HEAD", "ref", "short", "upper-case", "number", "null"],
)  # fmt: skip
def test_a_journal_whose_head_is_no_full_commit_id_is_corrupt_and_finishes_nothing(
    picking, shared_repo, monkeypatch, value
):
    """A journal naming its head as a ref, a short or upper-case id, a number or nothing is damage: a Finish on an
    unrelated owner commit with the batch's very tree completes nothing, and neither Abandon, a save nor a reader
    goes on as if the batch were known."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    generation = _interrupt_at(picking, monkeypatch, items)
    files = decision_batch.pending(shared).files
    _rewrite_journal(shared, lambda record: record.__setitem__("head", value))
    orphan = _unrelated_commit_of_the_after_images(shared, files)
    journal, published = decision_batch.journal_path(shared).read_bytes(), _remote_main(remote)

    for action in (decision_recovery.finish, decision_recovery.abandon):  # the generation the owner was shown
        with pytest.raises(decision_store.DecisionsUnavailable, match="head"):
            action(shared, generation)
    with pytest.raises(decision_batch.JournalError, match="head"):
        decision_batch.pending(shared)
    shown = decision_recovery_routes.diagnosis(shared)
    assert (shown["interrupted"], shown["corrupt"], shown["generation"]) == (True, True, "")
    with pytest.raises(decision_store.DecisionsUnavailable):
        decision_store.save(shared, make(title="Use UTC"), expected_revision=None, message="decisions: one")
    assert decision_batch.journal_path(shared).read_bytes() == journal
    assert shared.git("rev-parse", "HEAD").stdout.strip() == orphan
    assert _remote_main(remote) == published
    _no_authority(picking)


@pytest.mark.parametrize("length", [40, 64])
def test_a_journal_head_of_a_full_commit_id_is_read(picking, monkeypatch, length):
    """A producer journals HEAD as `rev-parse` names it, 40 hexadecimal characters, or 64 in a SHA-256 repository."""
    _seed(picking)
    shared = picking.shared
    _interrupt(picking, monkeypatch, [make(title="Use UTC", statement="All timestamps use UTC.")])
    head = decision_batch.pending(shared).head
    assert len(head) == 40  # a producer's own
    value = head if length == 40 else "c" * 64
    _rewrite_journal(shared, lambda record: record.__setitem__("head", value))

    assert decision_batch.pending(shared).head == value
    assert decision_recovery_routes.diagnosis(shared)["corrupt"] is False


def _owner_commits_after_push(m: pytest.MonkeyPatch, at: int, pushes: list[str], made: list[str]) -> None:
    """After Git pushes the *at*-th commit of this save, the owner commits an unrelated file; every push is listed."""
    real_git = data_repo._git  # noqa: SLF001

    def push_then_owner_commits(cwd, *args, **kwargs):
        said = real_git(cwd, *args, **kwargs)
        if args[:1] == ("push",):
            pushes.append(args[-1])
            if len(pushes) == at and not said.returncode:
                (cwd / "owner.txt").write_text("the owner's own work\n")
                real_git(cwd, "add", "owner.txt")
                real_git(cwd, "commit", "-qm", "the owner's own commit")
                made.append(real_git(cwd, "rev-parse", "HEAD").stdout.strip())
        return said

    m.setattr(data_repo, "_git", push_then_owner_commits)


@pytest.mark.parametrize("case", ["after-the-batch-push", "after-the-flag-push", "healthy-flags"])
def test_an_owner_commit_made_as_a_save_publishes_is_never_completed_on_or_pushed_later(
    picking, shared_repo, monkeypatch, case
):
    """The batch's commit B is pushed, then the owner commits C on it: B is reported published but the batch is not
    completed on C, and no later round proves, rebases or pushes C. When the owner commits after the conflict flags'
    commit F is pushed instead, the next round stops there and C stays local. Without the owner's commit, the batch
    and its flags publish as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    old = make()
    assert decision_store.save(shared, old, expected_revision=None, message="decisions: old").published
    a, b = replacing(old, title="Notes in A"), replacing(old, title="Notes in B")
    assert decision_store.save(shared, a, expected_revision=None, message="decisions: a").published
    pushes, made = [], []

    with monkeypatch.context() as m:
        if case != "healthy-flags":
            _owner_commits_after_push(m, 1 if case == "after-the-batch-push" else 2, pushes, made)
        receipts = decision_store.save_all(shared, [(b, None)], message="decisions: b")

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    if case == "healthy-flags":
        assert all(r.published for r in receipts)
        assert _remote_main(remote) == head
        assert shared.git("log", "-1", "--format=%s").stdout.startswith("decisions: conflict on")
        assert decision_batch.pending(shared) is None
        return
    owner = made[0]
    assert head == owner  # the owner's commit stays, as made, and is never sent
    assert len(pushes) == (1 if case == "after-the-batch-push" else 2)
    assert _remote_main(remote) == shared.git("rev-parse", "HEAD~1").stdout.strip() != owner
    assert shared.git("status", "--porcelain").stdout == ""
    if case == "after-the-batch-push":
        assert not any(r.saved for r in receipts)
        assert f"published as {_remote_main(remote)[:12]}, but HEAD moved past it" in receipts[0].notice
        assert decision_batch.pending(shared) is not None
        _no_authority(picking)
        return
    assert shared.git("log", "-1", "--format=%s", "HEAD~1").stdout.startswith("decisions: conflict on")
    assert all(r.saved for r in receipts)  # the batch and its flags landed; only the next round stopped
    assert "HEAD moved past this save's commit" in receipts[0].notice
    assert decision_batch.pending(shared) is None


# Another process takes the batch lock, says so, and lets it go only when told to, then says that too.
HOLDER = """
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("held", flush=True)
sys.stdin.readline()
fcntl.flock(fd, fcntl.LOCK_UN)
print("released", flush=True)
sys.stdin.readline()
"""
SAFETY_SECONDS = 5  # releases a lock code with no deadline would wait on forever, so the old code fails, never hangs


class _Holder:
    def __init__(self, lock: Path) -> None:
        self.process = subprocess.Popen(  # noqa: S603 - this interpreter and a fixed script
            [sys.executable, "-c", HOLDER, str(lock)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        assert self.process.stdout.readline().strip() == "held"  # the lock is taken before the call under test
        self.released = threading.Event()
        self._once = threading.Lock()

    def release(self) -> None:
        with self._once:
            if not self.released.is_set():
                self.process.stdin.write("\n")
                self.process.stdin.flush()
                assert self.process.stdout.readline().strip() == "released"
                self.released.set()

    def stop(self) -> None:
        self.process.kill()
        self.process.wait(timeout=10)


DEADLINE_CASES = ["held-past-the-deadline", "released-within-the-deadline", "freed-only-after-it", "expired-before"]


@pytest.mark.parametrize("case", DEADLINE_CASES)
@pytest.mark.parametrize("op", ["push", "pull"])
def test_an_ordinary_push_or_pull_reads_the_batch_journal_within_its_own_deadline(  # noqa: PLR0915 - one matrix
    picking, shared_repo, monkeypatch, op, case
):
    """Another process holds the batch lock. An ordinary push or pull asks Git for its folder and waits for the lock
    only within its own deadline: when the lock is still held then, or comes free only after it, or the deadline
    passed before the call, it neither pushes, fetches nor rebases and says why; a deadline already passed starts no
    Git at all. When the lock comes free within it, the push or pull goes on as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    (shared.root / "settings-note.txt").write_text("a setting\n")
    shared.git("add", "settings-note.txt")
    shared.git("commit", "-qm", "settings: a note")
    published, calls, launched, tries = _remote_main(remote), [], [], []
    real_git, real_run, real_open_lock = data_repo._git, subprocess.run, batch_journal.open_lock  # noqa: SLF001

    def recording_git(cwd, *args, until=None):
        calls.append((args, until))
        return real_git(cwd, *args, until=until)

    def recording_run(*args, **kwargs):
        launched.append(kwargs["timeout"])
        return real_run(*args, **kwargs)

    def counted_try(*args, **kwargs):
        tries.append(kwargs["blocking"])
        return real_open_lock(*args, **kwargs)

    holder = _Holder(decision_batch.journal_path(shared).parent / decision_batch.LOCK)
    safety = threading.Timer(SAFETY_SECONDS, holder.release)
    safety.start()
    until = time.monotonic() + (-1 if case == "expired-before" else SAFETY_SECONDS * 2)
    clock = [time.monotonic()]

    def past_it(_seconds: float) -> None:
        clock[0] = until + 1  # the wait ends after the deadline; the lock is let go only then, if at all
        if case == "freed-only-after-it":
            holder.release()

    after = SimpleNamespace(monotonic=lambda: clock[0], sleep=past_it)
    waits = {
        "released-within-the-deadline": SimpleNamespace(monotonic=time.monotonic, sleep=lambda _s: holder.release()),
        "held-past-the-deadline": after,
        "freed-only-after-it": after,
    }
    try:
        with monkeypatch.context() as m:
            m.setattr(data_repo, "_git", recording_git)
            m.setattr(subprocess, "run", recording_run)  # every Git process the call starts
            m.setattr(batch_journal, "open_lock", counted_try)
            if case in waits:
                m.setattr(batch_journal, "time", waits[case], raising=False)
            started = time.monotonic()
            said = shared._push(until) if op == "push" else shared.pull(until)  # noqa: SLF001
            took = time.monotonic() - started
    finally:
        safety.cancel()
        holder.stop()

    probes = [u for args, u in calls if args[:2] == ("rev-parse", "--absolute-git-dir")]
    assert probes
    assert all(u == until for u in probes)  # every journal probe runs within this call's own deadline
    assert all(0 < t <= data_repo.GIT_SECONDS for t in launched)
    if case == "released-within-the-deadline":
        assert holder.released.is_set()
        assert said == ""
        if op == "push":
            assert _remote_main(remote) == shared.git("rev-parse", "HEAD").stdout.strip()
        return
    assert took < SAFETY_SECONDS  # the call returned before the safety release
    assert "is not known yet" in said
    if case == "expired-before":
        assert launched == []  # no Git is started once the deadline has passed
        assert tries == []
        assert "deadline passed before the git folder" in said
    else:
        assert "another save still holds the batch lock, so try again" in said
        assert holder.released.is_set() == (case == "freed-only-after-it")
        assert tries == [False]  # one try while it was held; none once the deadline had passed
    remote_work = {"push", "pull", "fetch", "rebase", "ls-remote"}
    assert not [args for args, _ in calls if remote_work & set(args)]  # nothing after the deadline reaches the remote
    assert _remote_main(remote) == published
    assert shared.git("log", "-1", "--format=%s").stdout.strip() == "settings: a note"


def test_git_is_given_only_what_is_left_of_its_deadline(tmp_path, monkeypatch):
    """A Git command with a deadline gets only the time left, however short, and none once it passed; one without a
    deadline gets the usual cap."""
    seen, real_run = [], subprocess.run

    def recording_run(*args, **kwargs):
        seen.append(kwargs["timeout"])
        return real_run(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(subprocess, "run", recording_run)
        deadline = time.monotonic() + 0.2
        data_repo._git(tmp_path, "--version", until=deadline)  # noqa: SLF001
        data_repo._git(tmp_path, "--version")  # noqa: SLF001
        expired = data_repo._git(tmp_path, "--version", until=time.monotonic() - 0.001)  # noqa: SLF001

    assert len(seen) == 2  # the expired command never started
    assert 0 < seen[0] <= 0.2  # less than half a second left: that, and no floor
    assert seen[1] == data_repo.GIT_SECONDS
    assert (expired.returncode, expired.stdout) == (128, "")
    assert "deadline passed" in expired.stderr


@pytest.mark.parametrize("cost", [0.01, 0.03], ids=["partly-used-by-acquisition", "expired-during-acquisition"])
def test_a_busy_batch_lock_waits_only_for_the_budget_left_after_its_acquisition_attempt(monkeypatch, cost):
    clock, attempts, waits, deadline = {"now": 0.0}, [], [], 0.02

    def busy(fd, *, blocking, name):
        assert (fd, blocking, name) == (7, False, batch_journal.LOCK)
        attempts.append(fd)
        clock["now"] += cost
        raise BlockingIOError

    def wait(seconds):
        assert clock["now"] < deadline
        assert 0 < seconds <= deadline - clock["now"]
        waits.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(batch_journal, "open_lock", busy)
    monkeypatch.setattr(batch_journal, "time", SimpleNamespace(monotonic=lambda: clock["now"], sleep=wait))
    with pytest.raises(BlockingIOError):
        batch_journal._take(7, deadline)  # noqa: SLF001 - the actual acquisition loop is the boundary
    assert attempts == [7]
    assert waits == ([] if cost >= deadline else [pytest.approx(deadline - cost)])


def _during_the_continuation_fetch(m: pytest.MonkeyPatch, act, ran: list) -> None:
    """*act* runs once, in the first fetch after the save's own push, the continuation's catch-up fetch, before Git
    fetches; every Git command is listed in *ran*."""
    real_git, pushed = data_repo._git, []  # noqa: SLF001

    def git(cwd, *args, until=None):
        if args[:1] == ("fetch",) and pushed == [True]:
            pushed.append(True)
            act()
        said = real_git(cwd, *args, until=until)
        ran.append(args)
        if args[:1] == ("push",) and not said.returncode and not pushed:
            pushed.append(True)
        return said

    m.setattr(data_repo, "_git", git)


def _another_clone_moves_the_remote_on(remote: Path, other: Path) -> str:
    _git_in(other.parent, "clone", "-q", str(remote), str(other))
    (other / "elsewhere.txt").write_text("another clone\n")
    _git_in(other, "add", "-A")
    _git_in(other, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "another clone's commit")
    _git_in(other, "push", "-q")
    return _git_in(other, "rev-parse", "HEAD")


@pytest.mark.parametrize("case", ["owner-commits-as-the-remote-moves", "owner-switches-branch-at-the-same-commit"])
def test_a_save_continuation_neither_rebases_an_owner_commit_nor_follows_a_branch_switch(
    picking, shared_repo, monkeypatch, tmp_path, case
):
    """The save's commit B is published and landed; its continuation fetches before flagging. Meanwhile the owner
    commits C while another clone moves the remote on, or checks out another branch at B itself that follows another
    remote still behind B. C is never rebased and that other remote never receives B: the continuation stops, B stays
    published, and the owner's commit, branch, index and files stay as the owner left them."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    elsewhere = _second_remote(shared, tmp_path)  # its `side` at H0, the head B will grow from
    behind = _git_in(tmp_path, "--git-dir", str(elsewhere), "rev-parse", "side")
    ran, owner, other = [], [], tmp_path / "other"

    def owner_acts() -> None:
        batch = shared.git("rev-parse", "HEAD").stdout.strip()
        assert _remote_main(remote) == batch  # B is already published when the continuation fetches
        if case == "owner-commits-as-the-remote-moves":
            owner.append(_another_clone_moves_the_remote_on(remote, other))
            owner.append(_owner_unrelated_commit(shared))
        else:
            _git_in(shared.root, "branch", "-q", "-f", "side", batch)  # the other branch, now at B itself
            _git_in(shared.root, "checkout", "-q", "side")
        owner.append(batch)

    with monkeypatch.context() as m:
        _during_the_continuation_fetch(m, owner_acts, ran)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert owner, "the continuation's fetch was never reached"
    batch = owner[-1]
    assert shared.git("rev-parse", f"{batch}~1").stdout.strip() == behind  # `side` was left at B's own parent
    assert all(r.saved for r in receipts)  # B was published and landed; only the continuation stopped
    assert _git_in(tmp_path, "--git-dir", str(elsewhere), "rev-parse", "side") == behind  # never fast-forwarded to B
    assert not [args for args in ran if "rebase" in args]
    assert shared.git("status", "--porcelain").stdout == ""
    assert decision_batch.pending(shared) is None
    if case == "owner-commits-as-the-remote-moves":
        assert "HEAD moved past this save's commit" in receipts[0].notice
        assert shared.git("rev-parse", "HEAD").stdout.strip() == owner[1]  # C itself, never rebased into C'
        assert shared.git("rev-parse", "HEAD~1").stdout.strip() == batch
        assert _remote_main(remote) == owner[0]  # the other clone's commit, on top of B; C is never sent
        return
    assert "left the branch" in receipts[0].notice
    assert shared.git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/side"
    assert shared.git("rev-parse", "HEAD").stdout.strip() == batch
    assert _remote_main(remote) == batch  # B went where its publication began


def test_a_save_continuation_still_catches_up_with_a_remote_that_moved_on(picking, shared_repo, monkeypatch, tmp_path):
    """Only another clone moves the remote on during the continuation's fetch: it catches up as before."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    ran, moved = [], []

    with monkeypatch.context() as m:
        _during_the_continuation_fetch(
            m, lambda: moved.append(_another_clone_moves_the_remote_on(remote, tmp_path / "other")), ran
        )
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert all(r.published for r in receipts)
    assert shared.git("rev-parse", "HEAD").stdout.strip() == moved[0] == _remote_main(remote)
    assert decision_batch.pending(shared) is None


def _owner_commits_in_the_holds_probe(
    m: pytest.MonkeyPatch, shared: DataRepo, remote: Path, path: str, seen: dict
) -> None:
    """Another clone moves the remote on: in the continuation's first fetch after the save's push, or before that push,
    so it is refused. Then, in the publication hold's own Git probe as `DataRepo.rebase` starts, the owner commits C.
    *seen* gets that commit, B as it was then, the remote's commit and every Git command."""
    real_git, other = data_repo._git, remote.parent / "other"  # noqa: SLF001
    seen.update(ran=[], armed=False, fired=False, pushed=False)

    def git(cwd, *args, until=None):
        if path == "continuation" and args[:1] == ("fetch",) and seen["pushed"] and "remote" not in seen:
            seen["remote"], seen["armed"] = _another_clone_moves_the_remote_on(remote, other), True
        if path == "rejected-push" and args[:1] == ("push",) and "remote" not in seen:
            seen["remote"] = _another_clone_moves_the_remote_on(remote, other)
        if seen["armed"] and not seen["fired"] and args[:3] == ("rev-parse", "--git-path", publication_hold.RECORD):
            seen["fired"] = True
            seen["batch"] = real_git(cwd, "rev-parse", "HEAD").stdout.strip()
            seen["owner"] = _owner_unrelated_commit(shared)
        said = real_git(cwd, *args, until=until)
        seen["ran"].append(args)
        if args[:1] == ("push",):
            seen["pushed"] = not said.returncode
            seen["armed"] = seen["armed"] or (path == "rejected-push" and bool(said.returncode))
        return said

    m.setattr(data_repo, "_git", git)


@pytest.mark.parametrize("path", ["continuation", "rejected-push"])
def test_an_owner_commit_made_in_the_holds_probe_as_a_rebase_starts_is_never_rebased(
    picking, shared_repo, monkeypatch, path
):
    """A rebase that may go on, the continuation's catch-up or the retry of a refused push, reaches `DataRepo.rebase`;
    its publication hold probes Git, and in that probe the owner commits C. The ownership check runs again after the
    hold's probes, as Git is about to rebase: C is never rebased, the owner's commit, index and files stay as made,
    and the other clone's commit stays the remote's."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, _, _ = _update_and_successor(picking)
    seen: dict = {}

    with monkeypatch.context() as m:
        _owner_commits_in_the_holds_probe(m, shared, remote, path, seen)
        receipts = decision_store.save_all(shared, items, message="decisions: two")

    assert "remote" in seen, "the other clone never moved the remote on"
    assert seen["fired"], "the publication hold's probe in DataRepo.rebase was never reached"
    assert not publication_hold.recorded(shared, None)  # nothing was held: the real hold check ran and let it through
    assert not [args for args in seen["ran"] if "rebase" in args]
    assert shared.git("rev-parse", "HEAD").stdout.strip() == seen["owner"]  # C itself, never rebased into C'
    assert shared.git("rev-parse", "HEAD~1").stdout.strip() == seen["batch"]
    assert shared.git("status", "--porcelain").stdout == ""
    assert _remote_main(remote) == seen["remote"]  # the other clone's commit; C is never sent
    if path == "continuation":  # B landed before; only the continuation stops
        assert all(r.saved for r in receipts)
        assert "HEAD moved past this save's commit" in receipts[0].notice
        assert decision_batch.pending(shared) is None
        return
    assert not any(r.saved for r in receipts)  # B stays local, unpushed, its batch interrupted
    assert "HEAD moved past the commit whose push was refused" in receipts[0].notice
    assert decision_batch.pending(shared) is not None
    _no_authority(picking)


# One recovery, save, transaction or folder fsync, run against the disposable checkout in a child process: code that
# would wait on a pipe is killed at the child's timeout, its locks go with it, and nothing is ever written into the
# pipe. *when* is the moment the batch's file becomes a pipe; the last line printed is what came of it.
CHILD = r"""
import json, os, sys
from pathlib import Path
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_recovery, decision_store, decision_transaction
spec = json.loads(sys.argv[1])
shared, target, fired, armed = DataRepo(Path(spec["root"])), Path(spec["target"]), [], []

def to_pipe():
    if not fired:
        fired.append(True)
        target.unlink(missing_ok=True)
        os.mkfifo(target)

def after(owner, name, then):
    real = getattr(owner, name)
    def wrapped(*args, **kwargs):
        said = real(*args, **kwargs)
        then()
        return said
    setattr(owner, name, wrapped)

when, action = spec["when"], spec["action"]
if when == "before":
    to_pipe()
elif when == "fsync":  # the put-back proof's folder fsync, before it reads the files again
    after(decision_batch, "fsync_dir", to_pipe)
elif when == "git":  # the rebase probe after every file is put back and proved, before they are read once more
    after(decision_recovery, "_all_before", lambda: armed.append(True))
    after(DataRepo, "rebasing", lambda: to_pipe() if armed else None)
elif when == "put-back":  # the commit is refused, so the save puts its files back, reading each first
    DataRepo.commit = lambda *_args, **_kwargs: (to_pipe(), "git refused the commit")[1]
elif when == "make-dirs":  # past the save's fence and preflight: its folder's fsync, before `write` reads the file
    real_batch = decision_store.write_batch
    def armed_batch(*args, **kwargs):
        armed.append(True)
        return real_batch(*args, **kwargs)
    decision_store.write_batch = armed_batch
    after(storage_io, "_sync_held", lambda: to_pipe() if armed else None)
elif when == "after-replace":  # the temporary is renamed into place; then its folder is moved and a pipe takes its name
    real_replace = Path.replace
    def replace_then_swap(self, dest):
        said = real_replace(self, dest)
        if not fired:
            fired.append(True)
            folder = Path(dest).parent
            folder.rename(folder.with_name(folder.name + "-moved"))
            os.mkfifo(folder)
        return said
    Path.replace = replace_then_swap
try:
    if action in ("finish", "abandon"):
        said = getattr(decision_recovery, action)(shared, spec["generation"]).done
    elif action == "save":
        old = decision_store.load(shared, spec["project"]).snapshot.get(spec["id"]).decision
        update = old.model_copy(update={"title": "Notes stay in one SQLite table"})
        said = [r.saved for r in decision_store.save_all(shared, [(update, old.revision)], message="decisions: one")]
    elif action == "transaction":
        step = lambda *_args: decision_transaction.Step("", refused=True)
        said = decision_transaction.transaction(shared, spec["project"], "m", [(target, b"{}")], step, spec["head"])
    elif action == "atomic-write":
        said = storage_io.atomic_write(target, "the new content\n").st_ino
    else:
        storage_io.fsync_dir(target)
        said = "synced"
    print(json.dumps({"fired": bool(fired), "outcome": "returned", "said": said}))
except Exception as exc:
    print(json.dumps({"fired": bool(fired), "outcome": type(exc).__name__, "said": str(exc)}))
"""
CHILD_SECONDS = 15  # under the suite's own per-test timeout, so a child still waiting is reported here as hung


def _bounded(spec: dict) -> dict:
    """What *spec*'s child reported; "hung" when it was still waiting at its timeout and was killed."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    try:
        done = subprocess.run(  # noqa: S603 - this interpreter and a fixed script
            [sys.executable, "-c", CHILD, json.dumps(spec)],
            capture_output=True, text=True, timeout=CHILD_SECONDS, env=env, check=False,
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return {"outcome": "hung", "fired": True, "said": ""}
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


PIPE_CASES = [
    ("finish", "before"), ("abandon", "before"), ("abandon", "fsync"), ("abandon", "git"),
    ("save", "put-back"), ("transaction", "before"),
]  # fmt: skip


@pytest.mark.parametrize(("action", "when"), PIPE_CASES, ids=[f"{a}-{w}" for a, w in PIPE_CASES])
def test_a_batch_file_that_becomes_a_pipe_is_refused_and_never_waited_on(picking, monkeypatch, action, when):
    """A batch's file is a pipe before Finish or Abandon, or before a transaction plans its batch, or becomes one
    during the put-back proof's folder fsync, during the Git probe after it, or as a refused commit's files are
    put back. Every read opens it without waiting: the call refuses, the batch keeps its journal, Git stays as it was.
    """
    _seed(picking)
    shared = picking.shared
    items, first, _ = _update_and_successor(picking)
    spec = {"root": str(shared.root), "target": str(first), "action": action, "when": when, "project": PROJECT}
    if action in ("finish", "abandon"):
        spec["generation"] = _interrupt_at(picking, monkeypatch, items)
    spec["id"], spec["head"] = items[0][0].id, shared.git("rev-parse", "HEAD").stdout.strip()
    if action == "transaction":
        target = shared.root / PROJECT / "changes" / "record.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        spec["target"] = str(target)
    journal = decision_batch.journal_path(shared)
    kept, git = journal.read_bytes() if journal.exists() else None, _git_state(shared)

    said = _bounded(spec)

    assert said["outcome"] != "hung", said
    assert said["fired"]
    assert stat.S_ISFIFO(os.lstat(spec["target"]).st_mode)  # the pipe is left as it is, never written into
    assert _git_state(shared) == git
    if action in ("finish", "abandon"):
        assert said["outcome"] == "DecisionsUnavailable", said
        assert journal.read_bytes() == kept  # the batch stays interrupted, its journal untouched
        return
    if (action, when) == ("save", "put-back"):
        assert (said["outcome"], said["said"]) == ("returned", [False])
        assert decision_batch.pending(shared) is not None  # nothing proved put back: kept for the owner
        return
    assert said["outcome"] in {"DecisionsUnavailable", "NotRegularError"}, said  # refused before any journal
    assert decision_batch.pending(shared) is None
    assert (journal.read_bytes() if journal.exists() else None) == kept


def test_a_folder_fsync_refuses_a_pipe_or_a_link_at_the_folders_name(tmp_path):
    """A pipe swapped in for a moved folder is refused without waiting, a link is never synced through, and a plain
    folder is synced as before."""
    pipe, link, folder = tmp_path / "pipe", tmp_path / "link", tmp_path / "folder"
    folder.mkdir()
    os.mkfifo(pipe)
    link.symlink_to(folder, target_is_directory=True)

    said = _bounded({"root": str(tmp_path), "target": str(pipe), "action": "fsync-dir", "when": "none"})

    assert said["outcome"] != "hung", said
    assert said["outcome"] in {"NotADirectoryError", "OSError"}, said
    with pytest.raises(OSError, match=r"Errno"):
        storage_io.fsync_dir(link)
    storage_io.fsync_dir(folder)


def test_a_regular_file_is_read_and_a_missing_one_is_none(tmp_path):
    """The checked reader reads a regular file whole and names a missing one None; a link or a pipe raises at once."""
    regular, missing, pipe, link = tmp_path / "regular", tmp_path / "missing", tmp_path / "pipe", tmp_path / "link"
    regular.write_bytes(b"bytes\n" * 20000)
    os.mkfifo(pipe)
    link.symlink_to(regular)

    assert storage_io.read_regular(regular) == b"bytes\n" * 20000
    assert storage_io.read_regular(missing) is None
    assert storage_io.read_regular(tmp_path / "no-folder" / "missing") is None
    with pytest.raises(storage_io.NotRegularError):
        storage_io.read_regular(pipe)
    with pytest.raises(OSError, match=r"Errno"):
        storage_io.read_regular(link)


def test_an_atomic_writes_folder_swapped_for_a_pipe_after_its_rename_is_refused_without_waiting(tmp_path):
    """The writer renames its temporary into place; then the folder is moved aside and a pipe takes its name before
    the folder is synced. The sync refuses without waiting, the pipe is left as it is, and the moved folder holds the
    written file alone, with no temporary left behind."""
    folder = tmp_path / "decisions"
    folder.mkdir()
    (folder / "record.json").write_text("the old content\n")
    spec = {"root": str(tmp_path), "target": str(folder / "record.json"), "action": "atomic-write"}

    said = _bounded({**spec, "when": "after-replace"})

    assert said["outcome"] != "hung", said
    assert said["fired"]
    assert said["outcome"] in {"NotADirectoryError", "OSError"}, said
    assert stat.S_ISFIFO(os.lstat(folder).st_mode)  # the pipe stays, never followed, recreated or written into
    moved = tmp_path / "decisions-moved"
    assert {p.name: p.read_text() for p in moved.iterdir()} == {"record.json": "the new content\n"}


def test_an_atomic_write_returns_the_identity_of_the_file_it_wrote(tmp_path):
    """With nothing swapped, the write lands, its folder is synced and its answer is the written file's own inode."""
    target = tmp_path / "record.json"
    target.write_text("the old content\n")
    old = target.stat().st_ino

    written = storage_io.atomic_write(target, "the new content\n")

    assert target.read_text() == "the new content\n"
    assert (written.st_ino, written.st_dev) == (target.stat().st_ino, target.stat().st_dev)
    assert written.st_ino != old  # a new file, renamed over the old one
    assert [p.name for p in tmp_path.iterdir()] == ["record.json"]  # no temporary left


def test_an_atomic_write_does_not_clean_a_foreign_temporary_after_its_rename(tmp_path, monkeypatch):
    folder, moved, foreign = tmp_path / "folder", tmp_path / "moved", tmp_path / "foreign"
    folder.mkdir()
    foreign.mkdir()
    target, planted, real_replace = folder / "record.json", [], Path.replace

    def replace_then_link(source, destination):
        result = real_replace(source, destination)
        if Path(destination) == target:
            folder.rename(moved)
            other = foreign / source.name
            other.write_text("foreign contents")
            planted.append(other)
            folder.symlink_to(foreign, target_is_directory=True)
        return result

    monkeypatch.setattr(Path, "replace", replace_then_link)
    with pytest.raises(OSError, match=r"Errno"):
        storage_io.atomic_write(target, "new contents")
    assert len(planted) == 1
    assert planted[0].read_text() == "foreign contents"
    assert folder.is_symlink()
    assert (moved / "record.json").read_text() == "new contents"
    assert [p.name for p in moved.iterdir()] == ["record.json"]


def test_an_atomic_write_still_removes_its_temporary_when_the_rename_is_refused(tmp_path, monkeypatch):
    target, real_replace = tmp_path / "record.json", Path.replace
    target.write_text("old contents")

    def refuse(source, destination):
        if Path(destination) == target:
            msg = "simulated rename refusal"
            raise OSError(msg)
        return real_replace(source, destination)

    monkeypatch.setattr(Path, "replace", refuse)
    with pytest.raises(OSError, match="rename refusal"):
        storage_io.atomic_write(target, "new contents")
    assert target.read_text() == "old contents"
    assert [p.name for p in tmp_path.iterdir()] == ["record.json"]


def test_a_decision_file_swapped_for_a_pipe_as_its_folder_is_synced_is_refused_and_never_waited_on(
    picking, shared_repo
):
    """A save passes its fence and preflight; while `make_dirs` syncs the decision's folder, the owner swaps the file
    for a pipe. The standalone writer's read of the current file refuses it at once: the save is not saved, its batch
    stays interrupted, and the pipe, Git and the remote stay as they were."""
    _seed(picking)
    shared, remote = picking.shared, shared_repo[1]
    items, first, _ = _update_and_successor(picking)
    spec = {"root": str(shared.root), "target": str(first), "action": "save", "when": "make-dirs", "project": PROJECT}
    spec["id"] = items[0][0].id
    git, published = _git_state(shared), _remote_main(remote)

    said = _bounded(spec)

    assert said["outcome"] != "hung", said
    assert said["fired"]
    assert (said["outcome"], said["said"]) == ("returned", [False])
    assert stat.S_ISFIFO(os.lstat(first).st_mode)  # the pipe is left as it is, never read, written or replaced
    assert decision_batch.pending(shared) is not None
    assert _git_state(shared) == git
    assert _remote_main(remote) == published


def _entries_below(folder: Path) -> dict[str, bytes | None]:
    """Every entry under *folder*, folders included (None), each file with its bytes; links are listed, not followed."""
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() if p.is_file() and not p.is_symlink() else None
        for p in sorted(folder.rglob("*"))
    }


def test_a_project_folder_linked_away_as_the_root_is_synced_never_gets_a_folder_made_through_it(
    picking, monkeypatch, tmp_path
):
    """A save makes its project's missing `decisions` folder. While the checkout's root is synced first, the owner
    moves the project folder aside and links its name to a foreign folder. Nothing is made in the foreign folder, nor
    in the owner's moved one: the save refuses before it makes any folder, and its batch stays interrupted."""
    shared = picking.shared
    project, foreign, moved = shared.root / PROJECT, tmp_path / "foreign", tmp_path / "moved"
    assert project.is_dir()
    assert not (project / "decisions").exists()
    foreign.mkdir()
    (foreign / "keep.txt").write_text("the foreign folder's own file\n")
    theirs, ours, root = _entries_below(foreign), _entries_below(project), shared.root.stat()
    real_fsync, real_batch, armed, fired = os.fsync, decision_store.write_batch, [], []

    def batch(*args, **kwargs):
        armed.append(True)
        return real_batch(*args, **kwargs)

    def fsync(fd: int) -> None:
        real_fsync(fd)
        if armed and not fired and os.path.samestat(os.fstat(fd), root):  # the real sync of the root itself
            fired.append(True)
            project.rename(moved)
            project.symlink_to(foreign, target_is_directory=True)

    with monkeypatch.context() as m:
        m.setattr(decision_store, "write_batch", batch)
        m.setattr(os, "fsync", fsync)
        with contextlib.suppress(decision_store.DecisionsUnavailable):
            decision_store.save(shared, make(title="Use UTC"), expected_revision=None, message="decisions: one")

    assert fired, "the root was never synced while the save made its folders"
    assert _entries_below(foreign) == theirs  # first: nothing was made or written in the foreign folder
    assert _entries_below(moved) == ours  # nor in the owner's project folder, moved aside
    assert project.is_symlink()
    assert decision_batch.pending(shared) is not None
