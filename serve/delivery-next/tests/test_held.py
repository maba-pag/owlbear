"""TD-56: an agent step's result whose usage stayed unread is held; the owner may accept it while the step, brief
version and commit it depends on still match, else only run the step again."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, held, loop, runner, session_result, tools
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 13, 5, tzinfo=UTC)
UNREAD = "the usage at the step's end could not be read (RuntimeError)"
K = StepKind


class Host:
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def clone(tmp_path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "owlbear/c1")
    (work / "a.txt").write_text("a\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    return work


def commit(work: Path, name: str) -> str:
    (work / name).write_text(name)
    git(work, "add", name)
    git(work, "commit", "-qm", name)
    return git(work, "rev-parse", "HEAD")


def built(cfg, head: str, *, unread: bool) -> Run:
    payload = tools.BuildResult(summary="Added b.", changed_paths=["b.txt"], checks=[])
    run = Run(cfg.session_id, "result", payload, head=head, termination=Termination(confirmed=True))
    run.usage, run.usage_unread = ({"error": "RuntimeError"}, UNREAD) if unread else ({"models": {}}, "")
    return run


@pytest.fixture
def gated(tmp_path, clone, monkeypatch) -> tuple[Store, Change]:
    """A Build step whose committed result came back with its usage unread: held and asked about."""
    store = Store(tmp_path / "store")
    names = Names(branch="owlbear/c1", target="main", worktree=str(clone))
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["b.txt"])])
    change = Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=K.BUILD, task="t1"), names=names)
    store.write(Lock("c1"), change)

    async def unread(cfg):
        return built(cfg, commit(clone, "b.txt"), unread=True)

    monkeypatch.setattr(runner.sdk_adapter, "run", unread)
    runner._step(store, Lock("c1"), change, change.step, clone)  # noqa: SLF001
    return store, store.read("c1")


def answer(store: Store, c: Change, option: str) -> Change:
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option=option)], NOW)
    store.write(Lock("c1"), c)
    return c


def test_only_a_held_result_offers_accept() -> None:
    run = Run("s1", ending="result", usage_unread=UNREAD)
    plain = session_result.usage_gate(run, K.REVIEW).question
    offered = session_result.usage_gate(run, K.REVIEW, accept=True).question
    assert [(o.id, o.next) for o in plain.options] == [("retry", "retry")]
    assert [(o.id, o.next) for o in offered.options] == [("accept", "accept"), ("retry", "retry")]
    assert "it is held" in offered.text


def test_an_unread_build_result_is_held_and_accepting_it_processes_it_without_a_session(gated, clone, monkeypatch):
    store, c = gated
    q = loop.open_question(c)
    assert (c.outcome.exit, [o.id for o in q.options]) == (Exit.ASK, ["accept", "retry"])
    assert loop.next_step(c, NOW) is None
    session = c.step.session
    c = answer(store, c, "accept")
    assert (c.step.kind, c.step.task, loop.next_step(c, NOW)) == (K.BUILD, "t1", c.step)
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("an accepted hold starts no session"))
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    done = store.read("c1")
    assert (done.step.kind, done.step.task, done.outcome.exit) == (K.REVIEW, "t1", Exit.DONE)
    accepted = [e for e in store.events("c1") if e.get("event") == "held-accepted"]
    assert [e["session"] for e in accepted] == [session]
    assert not (store.root / "changes" / "c1" / "held.json").exists()


@pytest.mark.parametrize("change_", ["retry", "head", "brief"])
def test_a_declined_or_stale_hold_runs_the_step_again(gated, clone, monkeypatch, change_):
    store, c = gated
    c = answer(store, c, "retry" if change_ == "retry" else "accept")
    if change_ == "head":
        commit(clone, "c.txt")  # the commit the result depends on is no longer HEAD
    if change_ == "brief":
        c.brief.version = 2
        store.write(Lock("c1"), c)
    calls = []

    async def fresh(cfg):
        calls.append(cfg.session_id)
        return built(cfg, git(clone, "rev-parse", "HEAD"), unread=False)

    monkeypatch.setattr(runner.sdk_adapter, "run", fresh)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    events = [e["event"] for e in store.events("c1") if e.get("event", "").startswith("held-")]
    assert len(calls) == 1
    assert events == ([] if change_ == "retry" else ["held-stale"])
    assert not (store.root / "changes" / "c1" / "held.json").exists()


def test_a_damaged_hold_is_never_processed(gated):
    store, c = gated
    c = answer(store, c, "accept")
    path = store.root / "changes" / "c1" / "held.json"
    path.write_text(path.read_text().replace('"BuildResult"', '"PurePosixPath"'))  # a class, but no result model
    assert held.take(store, Lock("c1"), c) is None
    assert not path.exists()


def test_an_accept_takes_only_the_hold_its_question_offered(gated):
    store, c = gated
    c = answer(store, c, "accept")
    path = store.root / "changes" / "c1" / "held.json"
    q = c.questions[-1].id
    path.write_text(path.read_text().replace(f'"question":"{q}"', '"question":"q99"'))  # a later hold
    assert '"q99"' in path.read_text()
    assert held.take(store, Lock("c1"), c) is None


def test_accept_is_offered_and_taken_only_while_the_hold_matches(gated, clone):
    store, c = gated
    q = loop.open_question(c)
    assert [o.id for o in held.offered(store, c, q)] == ["accept", "retry"]
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    shown = client.get("/api/next/changes/c1").json()["question"]
    assert [o["id"] for o in shown["options"]] == ["accept", "retry"]
    commit(clone, "c.txt")  # the commit the result depends on is no longer HEAD
    assert [o.id for o in held.offered(store, c, q)] == ["retry"]
    shown = client.get("/api/next/changes/c1").json()["question"]
    assert [o["id"] for o in shown["options"]] == ["retry"]
    refused = client.post("/api/next/changes/c1/answers", json={"question": q.id, "option": "accept"})
    assert (refused.status_code, "no longer matches" in refused.json()["detail"]) == (409, True)
    assert client.post("/api/next/changes/c1/answers", json={"question": q.id, "option": "retry"}).status_code == 200


def test_a_result_whose_commit_is_no_longer_head_is_not_held(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    names = Names(branch="owlbear/c1", target="main", worktree=str(clone))
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["b.txt"])])
    change = Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=K.BUILD, task="t1"), names=names)
    store.write(Lock("c1"), change)

    async def moved(cfg):
        run = built(cfg, commit(clone, "b.txt"), unread=True)
        commit(clone, "c.txt")  # something moved HEAD after the result was submitted
        return run

    monkeypatch.setattr(runner.sdk_adapter, "run", moved)
    runner._step(store, Lock("c1"), change, change.step, clone)  # noqa: SLF001
    assert [o.id for o in loop.open_question(store.read("c1")).options] == ["retry"]
    assert not (store.root / "changes" / "c1" / "held.json").exists()


def test_a_reviewer_session_inside_a_step_is_not_held(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    run = Run("r1", ending="result", usage_unread=UNREAD, termination=Termination(confirmed=True))
    monkeypatch.setattr(runner, "_session", lambda *_a: (_ for _ in ()).throw(runner.UsageUnreadError(run)))
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN))
    store.write(Lock("c1"), change)
    cfg = runner.sdk_adapter.Session(
        kind=K.PLAN,
        worktree=clone,
        session_id="",
        message="review the plan",
        resume=False,
        policy=Policy(clone, ()),
        observe=tools.Worktree,
        checks=(),
    )
    with pytest.raises(runner.UsageUnreadError) as caught:
        runner._review_run(store, Lock("c1"), change, cfg, "plan-review")  # noqa: SLF001
    assert caught.value.worktree is None  # so the gate offers only to run the step again
