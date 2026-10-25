"""TD-56: an agent step's result whose usage stayed unread is held; the owner may accept it while the step, brief
version and commit it depends on still match, else only run the step again."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop, moves
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api, pack_routes
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import carried, config
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import held, sessions

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
    payload = tools.BuildResult(summary="Added b.", checks=[])
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


def test_an_accepted_hold_waits_untaken_while_its_role_s_settings_are_unset(gated, clone, monkeypatch):
    store, c = gated
    c = answer(store, c, "accept")
    spans = list(c.plan.tasks[0].spans)
    base = carried.layer()  # the owner cleared the builder's model since
    builder = base.agents["builder"].model_copy(update={"model": None})
    monkeypatch.setattr(config, "BASE", base.model_copy(update={"agents": base.agents | {"builder": builder}}))
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("no session while a setting is unset"))
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    asked = store.read("c1")
    assert loop.open_question(asked).cause == "state:build:settings-unset"
    assert (store.root / "changes" / "c1" / "held.json").exists()  # the result is kept for after the owner fills it
    assert asked.plan.tasks[0].spans == spans  # no build span was opened


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


def test_a_build_held_before_changed_paths_left_the_schema_is_still_accepted(gated, clone, monkeypatch):
    store, c = gated
    c = answer(store, c, "accept")
    path = store.root / "changes" / "c1" / "held.json"
    hold = json.loads(path.read_text())
    del hold["run"]["changed"]  # written by the earlier release: the agent's own paths, none of Delivery's
    hold["run"]["payload"]["args"]["changed_paths"] = ["b.txt"]
    path.write_text(json.dumps(hold))
    with pytest.raises(ValidationError, match="changed_paths"):  # a new call stays strict
        tools.BuildResult.model_validate(hold["run"]["payload"]["args"])
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("an accepted hold starts no session"))
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    done = store.read("c1")
    assert (done.step.kind, done.outcome.exit) == (K.REVIEW, Exit.DONE)
    assert done.plan.tasks[0].earlier == "Added b. Changed: b.txt"
    assert [e["event"] for e in store.events("c1") if e.get("event", "").startswith("held-")] == ["held-accepted"]


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
    monkeypatch.setattr(sessions, "run", lambda *_a, **_k: (_ for _ in ()).throw(sessions.UsageUnreadError(run)))
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN))
    store.write(Lock("c1"), change)
    cfg = runner.sdk_adapter.Session(
        kind=K.PLAN,
        worktree=clone,
        session_id="",
        message="review the plan",
        resume=False,
        policy=Policy(clone),
        observe=tools.Worktree,
        checks=(),
    )
    with pytest.raises(sessions.UsageUnreadError) as caught:
        sessions.review_run(store, Lock("c1"), change, clone, lambda _at: cfg, "plan-challenge")
    assert caught.value.worktree is None  # so the gate offers only to run the step again


def test_an_unread_judge_is_logged_with_its_label_so_its_subagents_count_for_its_role(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.SHAPE))  # a brief challenge runs in shaping
    store.write(Lock("c1"), change)
    ran = [{"agent": "explore", "credits": 0.5, "credits_known": True}]
    run = Run("r1", ending="result", usage_unread=UNREAD, termination=Termination(confirmed=True), subagents=ran)

    async def unread(_cfg):
        return run

    monkeypatch.setattr(sessions.sdk_adapter, "run", unread)
    monkeypatch.setattr(sessions, "in_window", lambda _profile: False)
    cfg = runner.sdk_adapter.Session(
        kind=K.REVIEW, worktree=clone, session_id="", message="challenge the brief", resume=False,
        policy=Policy(clone), observe=tools.Worktree, checks=(),
    )  # fmt: skip
    with pytest.raises(sessions.UsageUnreadError) as caught:
        sessions.review_run(store, Lock("c1"), change, clone, lambda _at: cfg, "brief-challenge")
    assert caught.value.label == "brief-challenge"
    runner._gate_unread(store, Lock("c1"), caught.value)  # noqa: SLF001
    (step,) = [e for e in store.events("c1") if e.get("event") == "step"]
    assert (step["kind"], step["label"], step["subagents"]) == ("shape", "brief-challenge", ran)
    assert [(u["role"], u["runs"]) for u in pack_routes.subagent_use(store)] == [("challenger", 1)]


def test_an_accepted_hold_survives_a_failed_final_write_and_is_applied_once_after_restart(gated, clone, monkeypatch):
    store, c = gated
    session = c.step.session
    c = answer(store, c, "accept")
    held_file = store.root / "changes" / "c1" / "held.json"
    real_apply, failures = runner.loop.apply, []

    def failing_once(change, result, now):
        if not failures:
            failures.append(result)
            msg = "disk full"
            raise OSError(msg)
        return real_apply(change, result, now)

    monkeypatch.setattr(runner.loop, "apply", failing_once)
    with pytest.raises(OSError, match="disk full"):
        runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    assert held_file.exists()
    assert [e for e in store.events("c1") if e.get("event") == "held-accepted"] == []

    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("a restored hold starts no session"))
    runner._step(store, Lock("c1"), store.read("c1"), store.read("c1").step, clone)  # noqa: SLF001

    done = store.read("c1")
    accepted = [e for e in store.events("c1") if e.get("event") == "held-accepted"]
    assert (done.step.kind, done.outcome.exit) == (K.REVIEW, Exit.DONE)
    assert [e["session"] for e in accepted] == [session]
    assert not held_file.exists()


@pytest.mark.parametrize("failure", ["unlink", "log"])
def test_an_accepted_hold_is_not_applied_or_charged_again_when_its_cleanup_fails_after_the_result_is_written(
    gated, clone, monkeypatch, failure
):
    store, c = gated
    session = c.step.session
    c = answer(store, c, "accept")
    held_file = store.root / "changes" / "c1" / "held.json"
    real_unlink, real_log = Path.unlink, Store.log

    def broken_unlink(self, *args, **kwargs):
        if self == held_file:
            msg = "unlink refused"
            raise OSError(msg)
        return real_unlink(self, *args, **kwargs)

    def broken_log(self, lock, slug, event):
        if event.get("event") == "held-accepted":
            msg = "log refused"
            raise OSError(msg)
        return real_log(self, lock, slug, event)

    if failure == "unlink":
        monkeypatch.setattr(Path, "unlink", broken_unlink)
    else:
        monkeypatch.setattr(Store, "log", broken_log)
    with pytest.raises(OSError, match=f"{failure} refused"):
        runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    monkeypatch.setattr(Path, "unlink", real_unlink)
    monkeypatch.setattr(Store, "log", real_log)

    recorded = store.read("c1")
    assert recorded.outcome.exit == Exit.DONE
    assert len(recorded.accepted_holds) == 1
    assert held_file.exists()

    monkeypatch.setattr(runner.loop, "apply", lambda *_a: pytest.fail("a recorded hold is never applied again"))
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("a recorded hold starts no session"))
    runner._step(store, Lock("c1"), store.read("c1"), store.read("c1").step, clone)  # noqa: SLF001

    accepted = [e for e in store.events("c1") if e.get("event") == "held-accepted"]
    assert [e["session"] for e in accepted] == [session]
    assert not held_file.exists()
    assert store.read("c1").outcome.exit == Exit.DONE


def test_a_consumed_fallback_hold_does_not_suppress_the_next_legitimate_step(tmp_path, clone, monkeypatch):
    git(clone, "branch", "main")
    store = Store(tmp_path / "store")
    names = Names(branch="owlbear/c1", target="main", worktree=str(clone))
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["b.txt"])])
    change = Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=K.BUILD, task="t1"), names=names)
    store.write(Lock("c1"), change)

    async def unread(cfg):
        return built(cfg, commit(clone, "b.txt"), unread=True)

    real_write = held.atomic_write

    def disk_full(*_args, **_kwargs):
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(held, "atomic_write", disk_full)
    monkeypatch.setattr(runner.sdk_adapter, "run", unread)
    runner._step(store, Lock("c1"), change, change.step, clone)  # noqa: SLF001
    held_fallback = store.read("c1")
    assert held_fallback.held_fallback is not None
    monkeypatch.setattr(held, "atomic_write", real_write)

    c = answer(store, store.read("c1"), "accept")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    recorded = store.read("c1")
    assert recorded.step.kind == K.REVIEW
    assert recorded.held_fallback is None
    assert len(recorded.accepted_holds) == 1
    accepted = [e for e in store.events("c1") if e.get("event") == "held-accepted"]
    assert len(accepted) == 1

    class BoundaryReachedError(Exception):
        """The next step's session started: the fake worker boundary was reached."""

    starts = []

    async def boundary(cfg):
        starts.append(cfg.session_id)
        raise BoundaryReachedError

    monkeypatch.setattr(runner.sdk_adapter, "run", boundary)
    with pytest.raises(BoundaryReachedError):
        runner._step(store, Lock("c1"), store.read("c1"), store.read("c1").step, clone)  # noqa: SLF001
    after = store.read("c1")
    assert len(starts) == 1
    assert after.step.kind == K.REVIEW
    assert after.accepted_holds == recorded.accepted_holds
    assert [e for e in store.events("c1") if e.get("event") == "held-accepted"] == accepted


REVIEW_USAGE = [
    pytest.param(
        {"credits": 2.5, "models": {"m": {"credits": 2.5, "tokens": 100}}},
        "the model could not be read",
        2.5,
        [],
        id="known-usage",
    ),
    pytest.param({"error": "RuntimeError"}, UNREAD, 0.0, ["s1"], id="unread-usage"),
]


def review_store(tmp_path, clone, usage: dict, reason: str) -> tuple[Store, Run]:
    """A Review step whose result came back with one finding and its usage stayed as given: nothing applied yet."""
    store = Store(tmp_path / "store")
    git(clone, "branch", "main")  # the review's target: the base the worker's commits sit on
    names = Names(branch="owlbear/c1", target="main", worktree=str(clone))
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["b.txt"])])
    change = Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=K.REVIEW, task="t1"), names=names)
    change.loops["t1"] = RoundLoop(subject="t1", policy=RoundPolicy())
    store.write(Lock("c1"), change)
    finding = tools.Finding(place="b.txt", problem="p", fix="f", tasks=["t1"])
    payload = tools.ReviewResult(verdict="fix", findings=[finding])
    run = Run("s1", "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=Termination(confirmed=True))
    run.usage, run.usage_unread = usage, reason
    run.tool_calls = {"bash": {"calls": 3}}
    return store, run


def review_loop(store: Store) -> tuple[int, int]:
    recorded = store.read("c1")
    found = moves.loop_of(recorded, recorded.plan.tasks[0])
    assert found is not None
    return found.round, len(found.findings)


STAGES = ["hold-write", "accounting-write", "final-write", "log", "unlink"]
RAISES = {"final-write", "log", "unlink"}  # the stages whose failing write ends the accepting step


@pytest.mark.parametrize("stage", STAGES)
@pytest.mark.parametrize(("usage", "reason", "spent", "unread"), REVIEW_USAGE)
def test_a_held_review_counts_once_and_applies_once_whichever_write_fails(  # noqa: C901, PLR0913, PLR0915, PLR0917
    tmp_path, clone, monkeypatch, stage, usage, reason, spent, unread
):
    store, run = review_store(tmp_path, clone, usage, reason)
    exc = sessions.UsageUnreadError(run)
    exc.worktree = clone
    exc.label = "plan-judge"
    held_file = store.root / "changes" / "c1" / "held.json"
    armed = [stage]  # the one write this case fails; it fires once, and the restart runs clean
    real_atomic, real_write, real_log, real_unlink = held.atomic_write, Store.write, Store.log, Path.unlink

    def atomic(path, text):
        if armed and stage == "hold-write" and path == held_file:
            armed.clear()
            msg = "hold-write refused"
            raise OSError(msg)
        return real_atomic(path, text)

    def write(self, lock, change):
        counting = bool(change.counted_holds) and not change.accepted_holds
        if armed and ((stage == "accounting-write" and counting) or (stage == "final-write" and change.accepted_holds)):
            armed.clear()
            msg = f"{stage} refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    def log(self, lock, slug, event):
        if armed and stage == "log" and event.get("event") == "held-accepted":
            armed.clear()
            msg = "log refused"
            raise OSError(msg)
        return real_log(self, lock, slug, event)

    def unlink(self, *args, **kwargs):
        if armed and stage == "unlink" and self == held_file:
            armed.clear()
            msg = "unlink refused"
            raise OSError(msg)
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(held, "atomic_write", atomic)
    monkeypatch.setattr(Store, "write", write)
    monkeypatch.setattr(Store, "log", log)
    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("a held review starts no session"))

    if stage == "accounting-write":
        with pytest.raises(OSError, match="accounting-write refused"):
            runner._gate_unread(store, Lock("c1"), exc)  # noqa: SLF001
    else:
        runner._gate_unread(store, Lock("c1"), exc)  # noqa: SLF001

    restarted = store.read("c1")
    runner._step(store, Lock("c1"), restarted, loop.next_step(restarted, NOW), clone)  # noqa: SLF001
    counted = store.read("c1")
    assert (counted.spend.credits, counted.spend.unread) == (spent, unread)
    assert counted.tool_use.tools["bash"].calls == 3
    assert review_loop(store) == (0, 0)  # nothing is applied before the owner accepts
    assert "plan-judge" in [e.get("label") for e in store.events("c1") if e.get("event") == "step"]

    if stage == "hold-write":  # the held file is not written: the Change keeps the held record and the same gate
        assert "accept" in [o.id for o in loop.open_question(counted).options]
        assert not held_file.exists()
        assert counted.held_fallback is not None

    accepted = answer(store, counted, "accept")
    step = loop.next_step(accepted, NOW)
    if stage in RAISES:
        with pytest.raises(OSError, match=f"{stage} refused"):
            runner._step(store, Lock("c1"), accepted, step, clone)  # noqa: SLF001
        restarted = store.read("c1")
        if stage == "final-write":  # the receipt was never written: the result is applied now, once
            runner._step(store, Lock("c1"), restarted, loop.next_step(restarted, NOW), clone)  # noqa: SLF001
        else:  # the receipt is written: cleanup alone remains, and nothing is applied again
            monkeypatch.setattr(runner.loop, "apply", lambda *_a: pytest.fail("a recorded hold is never applied again"))
            runner._step(store, Lock("c1"), restarted, restarted.step, clone)  # noqa: SLF001
    else:
        runner._step(store, Lock("c1"), accepted, step, clone)  # noqa: SLF001

    final = store.read("c1")
    assert (final.spend.credits, final.spend.unread) == (spent, unread)
    assert final.tool_use.tools["bash"].calls == 3
    assert review_loop(store) == (1, 1)
    assert [e["session"] for e in store.events("c1") if e.get("event") == "held-accepted"] == ["s1"]
    assert not held_file.exists()


def test_a_held_review_whose_file_and_change_writes_both_fail_is_reported_and_leaves_nothing(
    tmp_path, clone, monkeypatch
):
    store, run = review_store(tmp_path, clone, {"credits": 2.5, "models": {}}, "")
    exc = sessions.UsageUnreadError(run)
    exc.worktree = clone
    real_write = Store.write

    def refuse(*_args):
        msg = "held file refused"
        raise OSError(msg)

    def write(self, lock, change):
        if change.counted_holds:
            msg = "change refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    monkeypatch.setattr(held, "atomic_write", refuse)
    monkeypatch.setattr(Store, "write", write)
    with pytest.raises(OSError, match="change refused"):
        runner._gate_unread(store, Lock("c1"), exc)  # noqa: SLF001
    recorded = store.read("c1")
    assert (recorded.spend.credits, recorded.counted_holds, recorded.held_fallback) == (0, [], None)
    assert review_loop(store) == (0, 0)
    assert not (store.root / "changes" / "c1" / "held.json").exists()


@pytest.mark.parametrize(
    ("usage", "reason"),
    [p.values[:2] for p in REVIEW_USAGE],
    ids=["known-usage", "unread-usage"],
)
def test_a_hold_an_older_build_kept_is_unread_once_and_never_zero_or_recharged(
    tmp_path, clone, monkeypatch, usage, reason
):
    store, run = review_store(tmp_path, clone, usage, reason)
    exc = sessions.UsageUnreadError(run)
    exc.worktree = clone
    held_file = store.root / "changes" / "c1" / "held.json"
    real_write = Store.write

    def refuse_counting(self, lock, change):  # the older build's gate and hold were written, its count never was
        if change.counted_holds:
            msg = "counting refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    monkeypatch.setattr(Store, "write", refuse_counting)
    with pytest.raises(OSError, match="counting refused"):
        runner._gate_unread(store, Lock("c1"), exc)  # noqa: SLF001
    monkeypatch.setattr(Store, "write", real_write)
    real = held.Held.model_validate_json(held_file.read_text())
    store.write(Lock("c1"), real.change)
    data = json.loads(held_file.read_text())
    data.pop("change")
    data.pop("label")
    data["run"].pop("counted")
    held_file.write_text(json.dumps(data))
    monkeypatch.setattr(runner.sdk_adapter, "run", lambda _cfg: pytest.fail("a legacy hold starts no session"))

    for _ in range(2):  # a restart counts it once; a second one changes nothing
        restarted = store.read("c1")
        runner._step(store, Lock("c1"), restarted, loop.next_step(restarted, NOW), clone)  # noqa: SLF001
    counted = store.read("c1")
    assert (counted.spend.credits, counted.spend.unread) == (0.0, ["s1"])  # unknown, never zero
    assert "bash" not in counted.tool_use.tools
    assert review_loop(store) == (0, 0)

    accepted = answer(store, counted, "accept")
    runner._step(store, Lock("c1"), accepted, loop.next_step(accepted, NOW), clone)  # noqa: SLF001
    assert review_loop(store) == (1, 1)
    assert (store.read("c1").spend.credits, store.read("c1").spend.unread) == (0.0, ["s1"])
