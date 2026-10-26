"""Entry-point regressions for the decision-batch journal, HEAD proof, folder creation and put-back durability.

Each test interrupts a real save in-process (a `RuntimeError` escapes `write_batch` before any put-back), so the journal
stays in flight exactly as the crash would leave it, then drives the public recovery or save entry point.
"""

from __future__ import annotations

import base64
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_decisions import Decision, DecisionError, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_recovery, decision_store, decision_sync

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
    ],
    ids=["path-not-string", "files-not-list", "file-entry-not-object", "ids-without-files", "files-without-ids"],
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
        lambda record: record["files"][0].update(
            path=path,
            before=None if matching is None else base64.b64encode(matching).decode("ascii"),
            after=base64.b64encode(b"after\n").decode("ascii"),
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
