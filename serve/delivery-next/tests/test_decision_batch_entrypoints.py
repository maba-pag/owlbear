"""Entry-point regressions for the decision-batch journal, HEAD proof, folder creation and put-back durability.

Each test interrupts a real save in-process (a `RuntimeError` escapes `write_batch` before any put-back), so the journal
stays in flight exactly as the crash would leave it, then drives the public recovery or save entry point.
"""

from __future__ import annotations

import base64
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

from owlbear_decisions import Decision, DecisionError, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import (
    decision_batch,
    decision_recovery,
    decision_store,
    decision_sync,
    decision_transaction,
)

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

    def interrupted_write(decision, folder, expected=None):
        calls["n"] += 1
        if calls["n"] == 1:
            msg = "interrupted before the first write"
            raise RuntimeError(msg)
        return real_write(decision, folder, expected)

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
    ],
    ids=[
        "path-not-string",
        "files-not-list",
        "file-entry-not-object",
        "ids-without-files",
        "files-without-ids",
        "id-not-its-file",
        "one-file-twice",
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

    def recording_replace(file_path, data):
        writes.append(file_path)
        return real_replace(file_path, data)

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

    def first_lands_second_refuses(decision, folder, expected=None):
        if decision.project == "new-site":
            msg = "refused by the test"
            raise DecisionError(msg)
        return real_write(decision, folder, expected)

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

    def owner_commits_then_second_write_fails(decision, folder, expected=None):
        calls["n"] += 1
        if calls["n"] == 2:
            _owner_commit(shared, "owner commit between writes")
            msg = "disk full on the second file"
            raise DecisionError(msg)
        return real_write(decision, folder, expected)

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

    def second_refused(decision, folder, expected=None):
        if decision.id == second.id:
            msg = "refused by the test"
            raise DecisionError(msg)
        return real_write(decision, folder, expected)

    def put_back_then_owner_commits(path, text):
        real_put_back(path, text)
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

    def replace_then_move(file_path, data):
        writes.append(file_path)
        real_replace(file_path, data)
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

    def owner_commits_part_then_refused(_head: str) -> decision_transaction.Step:
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
