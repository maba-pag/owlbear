import errno
import json
import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts.inbox import AnswerItem, BriefApproval
from owlbear_delivery_next.change_contracts.models import (
    FORMAT,
    Brief,
    Change,
    Dispute,
    Exit,
    MergeConsent,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile, ProfileEntry
from owlbear_delivery_next.change_flow import loop, status
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store import store as store_mod
from owlbear_delivery_next.state_store.database import STORE_FORMAT
from owlbear_delivery_next.state_store.store import FormatTooNewError, LockHeldError, Store, StoreError

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOLD = """\
import sys
from pathlib import Path
from owlbear_delivery_next.state_store.store import Store
with Store.open(Path(sys.argv[1])).lock("c1"):
    print("held", flush=True)
    sys.stdin.read()
"""


def git(cwd, *args):
    quiet = [
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
    ]
    subprocess.run(["git", *quiet, *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "commit", "-q", "--allow-empty", "-m", "init")
    return root


@pytest.fixture
def store(repo):
    return Store.open(repo)


def save(store, change):
    with store.lock(change.slug) as lock:
        store.write(lock, change)


def record(store, slug):
    """The Change's stored text, as a damaged or older record would be found."""
    with store.db.read() as db:
        return db.execute("SELECT record FROM changes WHERE slug = ?", (slug,)).fetchone()[0]


def overwrite(store, slug, text):
    with store.db.write() as db:
        db.execute("UPDATE changes SET record = ? WHERE slug = ?", (text, slug))


def test_every_worktree_opens_the_same_store_in_the_projects_folder(repo, store):
    """TD-334: one folder per project in ~/.owlbear; the clone keeps only its id and the format marker."""
    git(repo, "worktree", "add", "-q", str(repo.parent / "wt"))
    folder = repo / ".git" / "owlbear-delivery"
    pid = (folder / "clone-id").read_text().strip()
    assert Store.open(repo.parent / "wt").root == store.root == local_home.root() / "projects" / pid
    assert sorted(p.name for p in folder.iterdir() if p.name != "move.lock") == ["clone-id", "format"]


def test_a_store_in_the_clone_moves_to_its_folder_once_and_older_runtimes_refuse_the_clone(repo):
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text("abc123\n")
    (folder / "format").write_text("6\n")
    assert project_home.current(repo) == folder  # an older host may still run on it: nothing moves
    store = Store.open(repo)
    assert (store.root, project_home.current(repo)) == ((local_home.root() / "projects" / "abc123"),) * 2
    assert (store.root / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert ((store.root / "format").read_text(), (folder / "format").read_text()) == ("6\n", f"{STORE_FORMAT}\n")
    (folder / "late.json").write_text("{}")  # what a move cut short left behind
    assert (Store.open(repo).root / "late.json").exists()
    (folder / "late.json").write_text("{}")
    with pytest.raises(StoreError, match=r"both exist: .*Stop Server\), move one of them away, then start it again"):
        Store.open(repo)


def test_a_move_across_volumes_copies_first_and_old_locks_and_racing_ids_never_split_the_store(repo, monkeypatch):
    """Sol: a stale lock an older process made is dropped; an id another opener created first is the one used."""
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "delivery.db").write_text("db")
    real = os.rename

    def across(src, dst):
        if str(src).startswith(str(folder)):
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        real(src, dst)

    monkeypatch.setattr(project_home.os, "rename", across)
    monkeypatch.setattr(project_home.secrets, "token_hex", lambda _n: "mine")
    (folder / "clone-id").write_text("theirs\n")  # another opener linked its id first
    root = Store.open(repo).root
    assert (root.name, (root / "delivery.db").read_text(), (root / "changes" / "c1" / "runner.log").read_text()) == (
        "theirs", "db", "ran\n"
    )  # fmt: skip
    assert sorted(p.name for p in folder.iterdir() if p.name != "move.lock") == ["clone-id", "format"]
    (root / "migrate.lock").touch()
    (folder / "migrate.lock").write_text("")  # an older chat server's fallback made it again
    assert (Store.open(repo).root, (folder / "migrate.lock").exists()) == (root, False)


@pytest.mark.parametrize(("marker", "action"), [("99\n", "Upgrade OwlBear"), ("x\n", "Restore the previous state")])
def test_unusable_store_format_is_refused_with_its_stop(repo, store, marker, action):
    (store.root / "format").write_text(marker)
    with pytest.raises(StoreError) as err:
        Store.open(repo)
    assert err.value.stop(NOW).action == action


@pytest.mark.parametrize("text", ["{broken", "[]", '{"format": "x"}', '{"format": null}', '{"format": 1, "slug": 3}'])
def test_malformed_state_is_a_store_error_with_a_restore_stop(store, text):
    save(store, Change(slug="c1"))
    overwrite(store, "c1", text)
    with pytest.raises(StoreError) as err:
        store.read("c1")
    assert status.unloadable(err.value.stop(NOW)).action == "Restore the previous state"


@pytest.mark.parametrize(
    ("edit", "said"),
    [
        (lambda d: d | {"surprise": 1}, "unknown field surprise"),
        (lambda d: {k: v for k, v in d.items() if k != "slug"}, "missing field slug"),
        (lambda d: d | {"step": {"kind": "nap"}}, "invalid field step.kind"),
    ],
)
def test_a_current_format_file_that_does_not_validate_was_written_by_another_delivery(store, edit, said):
    save(store, Change(slug="c1"))
    overwrite(store, "c1", json.dumps(edit(json.loads(record(store, "c1")))))
    with pytest.raises(StoreError) as err:
        store.read("c1")
    assert str(err.value) == f"state of c1 was written by a newer or different Delivery ({said})"
    assert err.value.stop(NOW).action == "Restore the previous state"


def test_profile_has_its_own_format_gate(store, monkeypatch):
    assert store.read_profile() is None
    store.write_profile(Profile(version=2, entries={"rules": ProfileEntry(state="unknown", evidence="HTTP 403")}))
    assert store.read_profile().entries["rules"].state == "unknown"
    monkeypatch.setattr(store_mod.profile_share, "PROFILE_FORMAT", PROFILE_FORMAT + 1)
    with pytest.raises(StoreError, match="cannot be migrated"):
        store.read_profile()
    monkeypatch.setattr(store_mod.profile_share, "PROFILE_FORMAT", PROFILE_FORMAT - 1)
    with pytest.raises(FormatTooNewError):
        store.read_profile()


def test_change_records_migrate_forward_or_refuse(store, monkeypatch):
    save(store, Change(slug="c1"))
    monkeypatch.setattr(store_mod, "FORMAT", FORMAT + 1)
    with pytest.raises(StoreError, match="cannot be migrated"):
        store.read("c1")
    monkeypatch.setitem(migrations.CHANGE, FORMAT, lambda data: data | {"profile_version": 7})
    assert store.read("c1").profile_version == 7
    monkeypatch.setattr(store_mod, "FORMAT", 0)
    with pytest.raises(FormatTooNewError):
        store.read("c1")


def test_a_stored_brief_review_becomes_its_challenge(store):
    approved = Brief(version=1, challenged=None)
    save(store, Change(slug="c1", brief=Brief(version=2, challenged=2, approved=[approved])))
    old = json.loads(record(store, "c1"))
    old["format"], old["brief"]["reviewed"] = 1, old["brief"].pop("challenged")
    old["brief"]["approved"][0]["reviewed"] = old["brief"]["approved"][0].pop("challenged")
    overwrite(store, "c1", json.dumps(old))
    brief = store.read("c1").brief
    assert (brief.challenged, brief.approved) == (2, [approved])


def test_a_format_1_consent_drops_the_merge_queue_field(store):
    save(store, Change(slug="c1", consent=MergeConsent(head="a" * 40, at=datetime(2026, 10, 10, tzinfo=UTC))))
    old = json.loads(record(store, "c1"))
    old["format"], old["consent"]["queued_at"] = 1, None
    overwrite(store, "c1", json.dumps(old))
    assert store.read("c1").consent.head == "a" * 40


def test_a_format_3_change_drops_the_td_189_round_fields(store):
    fix = Task(id="t2", title="fix", origin="review", fixes="t1", disputes=[Dispute(key="F1", finding="f", reason="r")])
    save(store, Change(slug="c1", plan=Plan(tasks=[Task(id="t1", title="one"), fix])))
    old = json.loads(record(store, "c1"))
    old["format"], old["plan"]["tasks"][1]["found_in"] = 3, 2
    old["plan"]["tasks"][1]["disputes"][0] |= {"direct": True, "repeat_of": "E1"}
    overwrite(store, "c1", json.dumps(old))
    assert store.read("c1").plan.tasks[1].disputes[0].key == "F1"


def test_write_keeps_prev_and_restore_brings_it_back(store):
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", profile_version=1))
        store.write(lock, Change(slug="c1", profile_version=2))
        overwrite(store, "c1", "{broken")
        with pytest.raises(StoreError, match="unreadable"):
            store.read("c1")
        store.restore(lock, "c1")
    assert store.read("c1").profile_version == 1
    with pytest.raises(RuntimeError, match="not held"):
        store.write(lock, Change(slug="c1"))


def test_lock_excludes_a_second_process_until_it_dies(repo, store):
    child = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", HOLD, str(repo)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout.readline().strip() == "held"
        with pytest.raises(LockHeldError) as err, store.lock("c1"):
            pass
        assert err.value.holder.pid == store.holder("c1").pid == child.pid
    finally:
        child.kill()
        child.wait()
    assert store.holder("c1") is None
    with store.lock("c1"):
        assert store.holder("c1").pid == os.getpid()


def test_inbox_written_without_the_lock_is_folded_by_its_holder(store):
    asked = StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="key?"))
    save(store, apply(Change(slug="c1", step=Step(kind=StepKind.BUILD)), asked, NOW))
    store.put_inbox("c1", AnswerItem(at=NOW, question="q1", text="FOO"))
    with store.lock("c1") as lock:
        change, step = store.fold(lock, "c1", NOW)
    assert (change.questions[0].answer.text, step.kind) == ("FOO", StepKind.BUILD)
    assert store.read("c1") == change
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)


def test_an_open_consent_question_is_closed_and_logged_once_ask_before_merge_is_off(store):
    asked = StepResult(exit=Exit.ASK, question=Question(step=StepKind.MERGE, text="merge?", cause=loop.CONSENT))
    save(store, apply(Change(slug="c1", step=Step(kind=StepKind.MERGE)), asked, NOW))
    with store.lock("c1") as lock:
        change, step = store.fold(lock, "c1", NOW)
    assert (change.outcome, change.questions[0].answer.option, step.kind) == (None, loop.OBSOLETE, StepKind.MERGE)
    assert [e["question"] for e in store.events("c1") if e["event"] == "consent-obsolete"] == [change.questions[0].id]


def test_interrupted_fold_never_applies_an_item_twice(store, monkeypatch):
    """The Change and the removal of the items it took commit together: a failure keeps both as they were."""
    save(store, Change(slug="c1", brief=Brief(version=1, challenged=1)))
    store.put_inbox("c1", BriefApproval(at=NOW, version=1))
    real = store_mod.put_record

    def killed(*_args, **_kwargs):
        msg = "killed"
        raise OSError(msg)

    monkeypatch.setattr(store_mod, "put_record", killed)
    with store.lock("c1") as lock, pytest.raises(OSError, match="killed"):
        store.fold(lock, "c1", NOW)
    assert store.read("c1").brief.approved == []
    monkeypatch.setattr(store_mod, "put_record", real)
    with store.lock("c1") as lock:
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1
    save(store, apply(store.read("c1"), StepResult(exit=Exit.BACK, back_to=StepKind.SHAPE, cause="scope:plan:"), NOW))
    with store.lock("c1") as lock:
        assert store.fold(lock, "c1", NOW)[1].kind == StepKind.SHAPE  # the approval is not applied again


def test_activity_keeps_only_the_last_events(store, monkeypatch):
    monkeypatch.setattr(store_mod, "ACTIVITY_LIMIT", 3)
    with store.lock("c1") as lock:
        for n in range(5):
            store.log(lock, "c1", {"n": n})
    assert [e["n"] for e in store.events("c1")] == [2, 3, 4]
