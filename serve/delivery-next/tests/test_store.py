import json
import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next import store as store_mod
from owlbear_delivery_next.loop import StepResult, apply
from owlbear_delivery_next.models import AnswerItem, Change, Exit, Question, Step, StepKind
from owlbear_delivery_next.store import FormatTooNewError, LockHeldError, Store, StoreError

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOLD = """\
import sys
from pathlib import Path
from owlbear_delivery_next.store import Store
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


def test_every_worktree_opens_the_same_store_in_the_common_git_dir(repo, store):
    git(repo, "worktree", "add", "-q", str(repo.parent / "wt"))
    assert Store.open(repo.parent / "wt").root == store.root == (repo / ".git" / "owlbear-delivery").resolve()


def test_newer_store_format_is_refused_with_an_upgrade_stop(repo, store):
    (store.root / "format").write_text("99\n")
    with pytest.raises(FormatTooNewError) as err:
        Store.open(repo)
    assert err.value.stop(NOW).action == "Upgrade OwlBear"


def test_change_records_migrate_forward_or_refuse(store, monkeypatch):
    save(store, Change(slug="c1"))
    monkeypatch.setattr(store_mod, "FORMAT", 2)
    with pytest.raises(StoreError, match="cannot be migrated"):
        store.read("c1")
    monkeypatch.setitem(store_mod.MIGRATIONS, 1, lambda data: data | {"profile_version": 7})
    assert store.read("c1").profile_version == 7
    monkeypatch.setattr(store_mod, "FORMAT", 0)
    with pytest.raises(FormatTooNewError):
        store.read("c1")


def test_write_keeps_prev_and_restore_brings_it_back(store):
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", profile_version=1))
        store.write(lock, Change(slug="c1", profile_version=2))
        (store.root / "changes" / "c1" / "change.json").write_text("{broken")
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
    assert not list((store.root / "changes" / "c1" / "inbox").iterdir())


def test_activity_keeps_only_the_last_events(store, monkeypatch):
    monkeypatch.setattr(store_mod, "ACTIVITY_LIMIT", 3)
    with store.lock("c1") as lock:
        for n in range(5):
            store.log(lock, "c1", {"n": n})
    lines = (store.root / "changes" / "c1" / "activity.jsonl").read_text().splitlines()
    assert [json.loads(line)["n"] for line in lines] == [2, 3, 4]
