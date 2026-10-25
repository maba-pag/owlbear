"""An interrupted decision batch fails closed until the owner finishes or abandons it by its generation (DEC-01)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import decision_routes
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


CRASH_CODE = """
import os
from pathlib import Path
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_actions, decision_store, decision_sync
shared = DataRepo(Path(os.environ["REPRO_DATA"]))
point = os.environ["REPRO_POINT"]
real_write = decision_store.write
def write(*args, **kwargs):
    if point == "before-first":
        os._exit(73)
    real_write(*args, **kwargs)
    if point == "after-first":
        os._exit(73)
decision_store.write = write
real_publish = decision_sync.publish
def publish(*args, **kwargs):
    sent = real_publish(*args, **kwargs)
    if point == "after-publish":
        os._exit(73)
    return sent
decision_sync.publish = publish
decision_actions.replace(
    shared, "shop-site", os.environ["REPRO_ID"], os.environ["REPRO_REV"],
    title="Notes store", statement="Notes live in Postgres.", rationale="",
    reason="SQLite no longer meets the requirement.", redecided=False,
)
"""


def _seed(picking):
    old = picking.put(make(statement="Notes live in SQLite."))
    picking.shared.git("add", "-A")
    picking.shared.git("commit", "-qm", "seed")
    picking.shared.git("push", "-q")
    return old


def _crash(picking, old, point: str) -> None:
    env = os.environ | {
        "REPRO_DATA": str(picking.shared.root),
        "REPRO_ID": old.id,
        "REPRO_REV": old.revision,
        "REPRO_POINT": point,
    }
    process = subprocess.run(  # noqa: S603 - fixed interpreter and code string, no untrusted input
        [sys.executable, "-c", CRASH_CODE], env=env, capture_output=True, text=True, check=False
    )
    assert process.returncode == 73, process.stderr


def _statements(shared) -> set[str]:
    view = decision_store.load(shared, PROJECT).snapshot
    return {e.decision.statement for e in view.entries if view.active(e.decision.id)}


@pytest.mark.parametrize("point", ["before-first", "after-first"])
def test_interrupted_batch_fails_closed_until_abandoned(picking, point):
    old = _seed(picking)
    _crash(picking, old, point)
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    assert pending.project == PROJECT

    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(picking.shared, PROJECT)
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.file_snapshot(picking.shared, PROJECT)
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.save(picking.shared, unrelated, expected_revision=None, message="decisions: unrelated")

    with pytest.raises(decision_store.DecisionsUnavailable, match="generation"):
        decision_recovery.abandon(picking.shared, "not-the-generation")
    notice = decision_recovery.abandon(picking.shared, pending.generation).notice
    assert "abandoned" in notice
    assert _statements(picking.shared) == {"Notes live in SQLite."}
    assert "??" not in picking.shared.git("status", "--porcelain").stdout
    assert decision_batch.pending(picking.shared) is None

    receipt = decision_store.save(picking.shared, unrelated, expected_revision=None, message="decisions: unrelated")
    assert receipt.committed


def test_interrupted_batch_is_finished_by_its_generation(picking):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    pending = decision_batch.pending(picking.shared)
    assert pending is not None

    done = decision_recovery.finish(picking.shared, pending.generation)
    assert done.done
    assert _statements(picking.shared) == {"Notes live in Postgres."}
    assert decision_batch.pending(picking.shared) is None
    assert "??" not in picking.shared.git("status", "--porcelain").stdout


def test_finish_after_publication_only_completes_the_marker(picking):
    old = _seed(picking)
    _crash(picking, old, "after-publish")
    pending = decision_batch.pending(picking.shared)
    assert pending is not None

    done = decision_recovery.finish(picking.shared, pending.generation)
    assert done.done
    assert "committed locally; no push/rebase retried" in done.notice  # the exact after-images were proved first
    assert decision_batch.pending(picking.shared) is None
    assert _statements(picking.shared) == {"Notes live in Postgres."}


def test_completed_generation_cannot_be_replayed(picking):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    stale_copy = decision_batch.journal_path(picking.shared).read_bytes()
    decision_recovery.finish(picking.shared, pending.generation)

    decision_batch.journal_path(picking.shared).write_bytes(stale_copy)
    assert decision_batch.pending(picking.shared) is None
    assert _statements(picking.shared) == {"Notes live in Postgres."}


def test_refused_batch_leaves_no_journal(picking):
    _seed(picking)
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    receipt = decision_store.save(picking.shared, unrelated, expected_revision="stale", message="decisions: refused")
    assert not receipt.saved
    assert decision_batch.pending(picking.shared) is None


@pytest.mark.parametrize("reader", [decision_store.load, decision_store.file_snapshot], ids=["load", "file_only"])
def test_a_batch_that_begins_and_completes_while_the_decisions_are_read_is_refused(picking, monkeypatch, reader):
    _seed(picking)
    real_files = decision_store._files  # noqa: SLF001

    def racing(shared, project):
        seen = real_files(shared, project)
        head = decision_store._head(shared)  # noqa: SLF001
        generation = decision_batch.begin(shared, project, head, "decisions: raced", [], [])
        decision_batch.complete(shared, generation)
        return seen

    monkeypatch.setattr(decision_store, "_files", racing)
    with pytest.raises(decision_store.DecisionsUnavailable, match="changed while they were read"):
        reader(picking.shared, PROJECT)


@pytest.fixture
def owner_api(picking):
    app = FastAPI()
    app.include_router(decision_routes.router(lambda: picking.shared, lambda: PROJECT, list))
    return TestClient(app)


def test_owner_route_shows_and_finishes_by_generation(picking, owner_api):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    shown = owner_api.get("/decisions/recovery").json()
    assert shown["interrupted"]
    assert not shown["corrupt"]
    generation = shown["generation"]

    assert owner_api.post("/decisions/recovery/finish", json={"generation": generation}).status_code == 422
    stale = owner_api.post("/decisions/recovery/finish", json={"generation": "0" * 16, "confirmed": True})
    assert stale.status_code == 409
    done = owner_api.post("/decisions/recovery/finish", json={"generation": generation, "confirmed": True})
    assert done.status_code == 200
    assert done.json()["done"]
    assert _statements(picking.shared) == {"Notes live in Postgres."}
    assert owner_api.get("/decisions/recovery").json()["interrupted"] is False


def test_chat_cannot_finish_or_abandon(picking, owner_api):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    generation = decision_batch.pending(picking.shared).generation
    body = {"generation": generation, "confirmed": True}
    for action in ("finish", "abandon"):
        refused = owner_api.post(f"/decisions/recovery/{action}", json=body, headers={"X-OwlBear-Use": "chat"})
        assert refused.status_code == 403
    assert decision_batch.pending(picking.shared) is not None


def test_corrupt_journal_blocks_and_is_diagnosed_not_cleared(picking, owner_api):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    decision_batch.journal_path(picking.shared).write_text("{not json")
    shown = owner_api.get("/decisions/recovery").json()
    assert shown["corrupt"]
    assert shown["diagnosis"]
    with pytest.raises(decision_store.DecisionsUnavailable):
        decision_store.load(picking.shared, PROJECT)
    refused = owner_api.post("/decisions/recovery/abandon", json={"generation": "a" * 16, "confirmed": True})
    assert refused.status_code == 409
    assert decision_batch.journal_path(picking.shared).exists()


def test_ambiguous_stale_publish_stays_interrupted(picking, monkeypatch):
    _seed(picking)
    ambiguous = decision_sync.Sent(stale=True, ambiguous=True, notice="not provably its own commit")
    monkeypatch.setattr(decision_sync, "publish", lambda *_args, **_kwargs: ambiguous)
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    receipt = decision_store.save(picking.shared, unrelated, expected_revision=None, message="decisions: unrelated")
    assert not receipt.saved
    assert "interrupted batch" in receipt.notice
    assert decision_batch.pending(picking.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(picking.shared, PROJECT)


def test_a_batch_already_pending_at_the_first_stamp_is_refused(picking, monkeypatch):
    _seed(picking)
    real_stamp = decision_store._stamp  # noqa: SLF001
    begun: list[str] = []

    def begun_before_first_stamp(shared):
        if not begun:
            head = decision_store._head(shared)  # noqa: SLF001
            begun.append(decision_batch.begin(shared, PROJECT, head, "decisions: raced", [], []))
        return real_stamp(shared)

    monkeypatch.setattr(decision_store, "_stamp", begun_before_first_stamp)
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(picking.shared, PROJECT)
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.file_snapshot(picking.shared, PROJECT)


@pytest.mark.parametrize("reader", [decision_store.load, decision_store.file_snapshot], ids=["load", "file_only"])
def test_a_batch_begun_and_completed_while_the_decisions_are_read_is_refused(picking, monkeypatch, reader):
    _seed(picking)
    real_files = decision_store._files  # noqa: SLF001

    def begun_and_completed(shared, project):
        seen = real_files(shared, project)
        head = decision_store._head(shared)  # noqa: SLF001
        decision_batch.complete(shared, decision_batch.begin(shared, project, head, "decisions: aba", [], []))
        return seen

    monkeypatch.setattr(decision_store, "_files", begun_and_completed)
    with pytest.raises(decision_store.DecisionsUnavailable, match="changed while they were read"):
        reader(picking.shared, PROJECT)


@pytest.mark.parametrize("action", [decision_recovery.abandon, decision_recovery.finish], ids=["abandon", "finish"])
def test_an_owner_edit_after_the_batch_is_never_overwritten(picking, action):
    old = _seed(picking)
    _crash(picking, old, "after-first")
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    rel = pending.files[0][0]
    path = decision_store.checkout(picking.shared).root / rel
    path.write_bytes(b"owner edit\n")

    with pytest.raises(decision_store.DecisionsUnavailable, match="edited since"):
        action(picking.shared, pending.generation)
    assert path.read_bytes() == b"owner edit\n"
    assert decision_batch.pending(picking.shared) is not None


def test_a_commit_failure_that_moved_head_is_ambiguous_and_stays_interrupted(picking, monkeypatch):
    _seed(picking)

    def moved_then_failed(self, _paths, _message, until):
        self.git("commit", "-q", "--allow-empty", "-m", "someone else", until=until)
        return "hook refused the commit"

    monkeypatch.setattr(DataRepo, "commit", moved_then_failed)
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    receipt = decision_store.save(picking.shared, unrelated, expected_revision=None, message="decisions: unrelated")
    assert not receipt.saved
    assert "interrupted batch" in receipt.notice
    assert decision_batch.pending(picking.shared) is not None


def test_a_refused_publish_never_resets_the_owners_index(picking, monkeypatch):
    _seed(picking)

    def staged_then_refused(self, paths, _message, until):
        rels = [p.relative_to(self.root).as_posix() for p in paths]
        self.git("add", "--", *rels, until=until)
        return "hook refused the commit"

    monkeypatch.setattr(DataRepo, "commit", staged_then_refused)
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    receipt = decision_store.save(picking.shared, unrelated, expected_revision=None, message="decisions: unrelated")
    assert not receipt.saved
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    rel, _, after = pending.files[0]
    assert picking.shared.git("show", f":{rel}").stdout.encode("utf-8") == after


def test_a_stamp_capture_is_not_torn_by_a_batch_that_begins_and_completes(picking, monkeypatch):
    _seed(picking)
    before = decision_batch.stamp(picking.shared)
    real_read = decision_batch._read  # noqa: SLF001
    writers: list[threading.Thread] = []

    def writing_during_the_first_read(path):
        if not writers and path.name == decision_batch.JOURNAL:

            def begin_and_complete():
                head = decision_store._head(picking.shared)  # noqa: SLF001
                generation = decision_batch.begin(picking.shared, PROJECT, head, "decisions: torn", [], [])
                decision_batch.complete(picking.shared, generation)

            writer = threading.Thread(target=begin_and_complete)
            writers.append(writer)
            writer.start()
            time.sleep(0.5)
            assert writer.is_alive(), "the writer must wait for the stamp capture lock"
        return real_read(path)

    monkeypatch.setattr(decision_batch, "_read", writing_during_the_first_read)
    captured = decision_batch.stamp(picking.shared)
    writers[0].join(timeout=10)
    assert not writers[0].is_alive()
    assert captured == before


@pytest.mark.parametrize("wording", ["edited", "before"])
def test_finish_refuses_a_committed_batch_whose_worktree_no_longer_holds_its_after_images(picking, wording):
    old = _seed(picking)
    _crash(picking, old, "after-publish")
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    rel, before, after = next(f for f in pending.files if f[1] is not None) if wording == "before" else pending.files[0]
    path = picking.shared.root / rel
    edited = before if wording == "before" else after.replace(b"Notes live in Postgres.", b"Notes live in Postgres 16.")
    path.write_bytes(edited)

    with pytest.raises(decision_store.DecisionsUnavailable, match="worktree differs"):
        decision_recovery.finish(picking.shared, pending.generation)
    assert path.read_bytes() == edited
    assert decision_batch.pending(picking.shared).generation == pending.generation


def test_a_stale_push_keeps_the_commit_the_index_and_the_journal(picking, monkeypatch):
    _seed(picking)
    shared = picking.shared
    owner = b"the owner's staged image, not a decision\n"
    real_git = DataRepo.git
    kept: dict[str, str] = {}

    def owner_stages_then_push_is_rejected(self, *args, **kwargs):
        if args[0] == "push":
            rel = real_git(self, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.split()[0]
            (self.root / rel).write_bytes(owner)
            real_git(self, "add", "--", rel)
            kept.update(rel=rel, head=real_git(self, "rev-parse", "HEAD").stdout.strip())
            return subprocess.CompletedProcess(args, 1, "", "rejected: the remote changed a decision")
        return real_git(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", owner_stages_then_push_is_rejected)
    monkeypatch.setattr(decision_sync, "_diverged", lambda _shared, _until: (set(), {kept["rel"]}))
    unrelated = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    receipt = decision_store.save(shared, unrelated, expected_revision=None, message="decisions: unrelated")

    assert not receipt.saved
    assert "interrupted batch" in receipt.notice
    assert real_git(shared, "rev-parse", "HEAD").stdout.strip() == kept["head"]
    assert real_git(shared, "show", f":{kept['rel']}").stdout.encode("utf-8") == owner
    assert (shared.root / kept["rel"]).read_bytes() == owner
    assert decision_batch.pending(shared) is not None


def test_an_owner_edit_after_a_publish_that_then_raises_stays_interrupted(picking):
    _seed(picking)
    shared = picking.shared
    path = shared.root / PROJECT / "decisions" / "owner-edit.json"
    rel = path.relative_to(shared.root).as_posix()
    published, owner = b"the published image\n", b"the owner's edit after the publish\n"

    def step(_head: str) -> tuple[str, bool]:

        path.write_bytes(published)
        shared.publish(path, "decisions: owner edit")
        path.write_bytes(owner)
        msg = "crash after publish"
        raise RuntimeError(msg)

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    with shared.locked(), pytest.raises(RuntimeError, match="crash after publish"):
        decision_transaction.transaction(shared, PROJECT, "decisions: owner edit", [(path, published)], step, head)

    pending = decision_batch.pending(shared)
    assert pending is not None
    assert shared.git("show", f"HEAD:{rel}").stdout.encode("utf-8") == published
    assert path.read_bytes() == owner
    with pytest.raises(decision_store.DecisionsUnavailable):
        decision_store.load(shared, PROJECT)
    with pytest.raises(decision_store.DecisionsUnavailable, match="worktree differs"):
        decision_recovery.finish(shared, pending.generation)
    assert path.read_bytes() == owner
    assert decision_batch.pending(shared).generation == pending.generation
