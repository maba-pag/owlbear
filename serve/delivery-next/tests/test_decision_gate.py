"""The runner's decision gate and step context (TD-419 slice 4): baselines, differences, faults and the budget."""

from __future__ import annotations

import asyncio
import dataclasses
import shutil
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Applicability, Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts.curation_records import Share, TestReview
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, BriefApproval
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    BriefDecision,
    Change,
    Environment,
    ErrorKind,
    Exit,
    Names,
    PersonCheck,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.preparation import Preparation
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import environment
from owlbear_delivery_next.runtimes import sdk_adapter, step_decisions, step_input
from owlbear_delivery_next.state_store import decision_archive
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import check, curation, decisions_gate, prepare

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
K = StepKind


class Started(Exception):  # noqa: N818 - the worker's session would start here
    pass


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Pages are plain HTML", "statement": "The pages are plain HTML with no build step.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.APPROVED, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    repo = DataRepo(shared_repo[0])
    repo.claim(PROJECT, "github.com/acme/shop-site")
    return repo


def put(shared: DataRepo, decision: Decision) -> Decision:
    write(decision, shared.root / PROJECT)
    return decision


def replace(shared: DataRepo, old: Decision, statement: str) -> Decision:
    """A successor in force, and *old* replaced: an accepted wording is never edited (TD-430)."""
    new = put(shared, make(title=old.title, statement=statement, applies_to=old.applies_to,
                           links=(Link(type=LinkType.REPLACES, target=old.id),)))  # fmt: skip
    write(old.model_copy(update={"state": State.REPLACED}), shared.root / PROJECT, old.revision)
    return new


def change(kind: StepKind = K.BUILD, scope: tuple[str, ...] = ("web",), **fields) -> Change:
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Notes", scope=list(scope))
    plan = Plan(tasks=[Task(id="t1", title="Show notes", scope=list(scope), checks=["true"])])
    names = Names(branch="owlbear/c1", target="main")
    return Change(slug="c1", brief=brief, plan=plan, names=names, step=Step(kind=kind, task="t1"), **fields)


def stored(tmp_path: Path, shared: DataRepo | None, c: Change, *, pin: bool = True) -> Store:
    store = Store(tmp_path / "store", shared, PROJECT if shared else "")
    if pin:
        c = c.model_copy(update={"decisions_baseline": decisions_gate.pinned(store, c, AT)[0]})
    store.write(Lock("c1"), c)
    return store


@pytest.fixture
def ran(monkeypatch) -> list[StepKind]:
    """The steps the runner started past the gate."""
    seen: list[StepKind] = []
    monkeypatch.setattr(runner, "_agent", lambda _s, _l, c, _r: seen.append(c.step.kind))
    monkeypatch.setattr(runner, "_engine", lambda _s, _l, c, _r: seen.append(c.step.kind))
    return seen


def step(store: Store, repo: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, loop.next_step(c, AT), repo)  # noqa: SLF001
    return store.read("c1")


def answer(store: Store, option: str) -> Change:
    c = store.read("c1")
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=AT, question=q.id, option=option)], AT)
    store.write(Lock("c1"), c)
    return c


def test_a_decision_an_earlier_change_recorded_reaches_a_later_changes_builder(
    tmp_path, shared, change_repo, monkeypatch
):
    earlier = Change(slug="notes", brief=Brief(version=1, approved_version=1, approved_at=AT, title="Notes", decisions=[
        BriefDecision(id=new_id(), question="Where do notes live?", answer="Notes live in one SQLite table.",
                      origin="decided", scope="project"),
    ]))  # fmt: skip
    files, left = decision_archive.archive(shared.root, PROJECT, earlier, "20261021-090000-notes", "merged")
    assert files
    assert not left
    unresolved = put(shared, make(applies_to=Applicability(paths=("api/**",)), title="API is versioned"))
    other = put(shared, make(applies_to=Applicability(steps=("review",)), title="Reviews read the diff"))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    seen: list[str] = []

    def kept(_store, _lock, _change, path, config):
        seen.append(config(path).message)
        raise Started

    monkeypatch.setattr(runner, "_kept", kept)
    store = stored(tmp_path, shared, change(scope=()))

    with pytest.raises(Started):
        step(store, change_repo)

    message = seen[0]
    assert "## Decisions in force" in message
    assert "Notes live in one SQLite table." in message  # the earlier Change's project decision
    assert f"{unresolved.id} (project, approved): API is versioned" in message
    assert message.count(step_decisions.UNRESOLVED) == 1  # no scope yet: shown, never dropped
    assert other.id not in message  # a review rule: counted, not listed, in a build
    assert "1 other decision(s) in force do not apply to this step" in message


@pytest.mark.parametrize("kind", [K.BUILD, K.PUBLISH, K.MERGE])
def test_an_applicable_change_after_approval_asks_before_the_next_step_and_continue_repins(tmp_path, shared, ran, kind):
    rule = put(shared, make(applies_to=Applicability(paths=("web/**",))))
    store = stored(tmp_path, shared, change(kind))
    new = replace(shared, rule, "The pages are plain HTML and CSS with no build step.")

    c = step(store, tmp_path)

    assert ran == []
    q = loop.open_question(c)
    assert c.outcome.exit == Exit.ASK
    assert q.cause.startswith(f"decisions:{kind}:")
    assert [o.label for o in q.options] == ["Continue with the current decisions", "Pause"]
    assert f"no longer in force: {rule.id}" in q.text
    assert f"new: {new.id}" in q.text
    assert "plain HTML and CSS" in q.text
    assert (c.brief.approved_version, c.brief.scope) == (1, ["web"])  # the approved brief stays (TD-428)

    c = answer(store, "continue")
    assert set(c.decisions_baseline.revisions) == {new.id}
    assert step(store, tmp_path).outcome is None
    assert ran == [kind]


def test_pause_keeps_the_baseline_and_asks_again_after_resume(tmp_path, shared, ran):
    rule = put(shared, make())
    store = stored(tmp_path, shared, change())
    pinned = store.read("c1").decisions_baseline
    replace(shared, rule, "The pages are plain HTML, served as they are.")
    step(store, tmp_path)

    c = answer(store, "pause")

    assert c.intent.paused_at is not None
    assert c.decisions_baseline == pinned
    assert loop.next_step(c, AT) is None
    c.intent.paused_at = None
    store.write(Lock("c1"), c)
    assert loop.open_question(step(store, tmp_path)) is not None
    assert ran == []


def test_a_change_to_a_decision_that_does_not_apply_does_not_stop_the_change(tmp_path, shared, ran):
    elsewhere = put(shared, make(applies_to=Applicability(paths=("api/**",))))
    store = stored(tmp_path, shared, change())
    replace(shared, elsewhere, "The API is versioned by path.")

    assert step(store, tmp_path).outcome is None
    assert ran == [K.BUILD]


def test_an_unreadable_data_repository_stops_the_step(tmp_path, shared, ran):
    store = stored(tmp_path, shared, change())
    shutil.rmtree(shared.root / PROJECT)

    c = step(store, tmp_path)

    assert ran == []
    assert (c.outcome.exit, c.stop.kind) == (Exit.STOP, ErrorKind.STATE)
    assert "has no folder" in c.stop.reason
    assert "owlbear-next setup" in c.stop.action


def test_without_a_data_repository_only_a_change_with_a_baseline_stops(tmp_path, shared, ran):
    old = stored(tmp_path / "old", None, change(), pin=False)
    assert decisions_gate.pinned(old, change(), AT) == (None, False)  # no baseline is owed
    assert step(old, tmp_path).outcome is None  # a project without one never recorded rules to compare with
    pinned = stored(tmp_path / "pinned", shared, change())
    moved = Store(pinned.root, None, "")

    c = step(moved, tmp_path)

    assert ran == [K.BUILD]
    assert c.stop.kind == ErrorKind.STATE
    assert "no shared data repository" in c.stop.reason


def test_a_conflicted_applicable_decision_stops_naming_it(tmp_path, shared, ran):
    store = stored(tmp_path, shared, change())
    flagged = put(shared, make(conflict=True))
    put(shared, make(conflict=True, applies_to=Applicability(paths=("api/**",))))  # does not apply

    c = step(store, tmp_path)

    assert ran == []
    assert c.stop.kind == ErrorKind.STATE
    assert c.stop.reason.count("D-") == 1
    assert flagged.id in c.stop.reason


def test_decisions_that_do_not_fit_stop_instead_of_being_cut(tmp_path, shared, ran):
    for n in range(40):
        put(shared, make(title=f"Rule {n} " + "t" * 100, statement="s" * 239))
    store = stored(tmp_path, shared, change())

    c = step(store, tmp_path)

    assert ran == []
    assert (c.stop.reason, c.stop.action) == (decisions_gate.SPLIT, "Split the Change")


def test_approval_pins_the_baseline_and_an_unreadable_one_asks_before_pinning_the_set_in_force(tmp_path, shared, ran):
    rule = put(shared, make())
    c = change().model_copy(update={"brief": Brief(version=1, challenged=1, scope=["web"])})
    store = Store(tmp_path / "store", shared, PROJECT)

    baseline, owed = decisions_gate.pinned(store, c, AT)
    folded = loop.fold(c, [BriefApproval(at=AT, version=1, baseline=baseline, unpinned=owed)], AT)
    assert (folded.decisions_baseline.revisions, folded.decisions_unpinned_at) == ({rule.id: rule.revision}, None)
    assert set(folded.decisions_baseline.said) == {rule.id}

    away = tmp_path / "away"
    (shared.root / PROJECT).rename(away)
    baseline, owed = decisions_gate.pinned(store, c, AT)
    folded = loop.fold(c, [BriefApproval(at=AT, version=1, baseline=baseline, unpinned=owed)], AT)
    assert (folded.decisions_baseline, folded.decisions_unpinned_at) == (None, AT)
    store.write(Lock("c1"), folded.model_copy(update={"step": Step(kind=K.BUILD, task="t1")}))
    away.rename(shared.root / PROJECT)

    c = step(store, tmp_path)

    q = loop.open_question(c)
    assert ran == []
    assert q.cause.startswith("decisions:build:")
    assert "Decisions in force now (not pinned at approval)" in q.text
    assert f'{rule.id} {rule.title}: "{rule.statement}"' in q.text
    assert c.decisions_baseline is None
    c = answer(store, "pause")
    assert (c.decisions_baseline, c.decisions_unpinned_at) == (None, AT)  # still owed: never pinned silently
    c.intent.paused_at = None
    store.write(Lock("c1"), c)
    assert loop.open_question(step(store, tmp_path)) is not None
    c = answer(store, "continue")
    assert (c.decisions_baseline.revisions, c.decisions_unpinned_at) == ({rule.id: rule.revision}, None)
    assert step(store, tmp_path).outcome is None
    assert ran == [K.BUILD]


def checking(**fields) -> Change:
    env = Environment(check="preview", command="npm run preview", directory=".", ready_url="http://127.0.0.1:4173/")
    c = change(K.CHECK, checks=[PersonCheck(id="preview", steps=["open the preview"])], env=env, **fields)
    return c.model_copy(update={"step": Step(kind=K.CHECK, task="preview")})


NONE = Preparation(id="none", kind="data-only", seed="true", cleanup="true")


def test_a_due_test_copy_waits_for_the_gate_and_a_gone_checks_end_still_runs(tmp_path, shared, ran, monkeypatch):
    rule = put(shared, make())
    store = stored(tmp_path, shared, checking())
    prepare._write(store, "c1", prepare.Prepared(check="preview", option=NONE))  # noqa: SLF001 - not restored yet
    prepare._write(store, "c1", prepare.Prepared(check="old", option=NONE, open=True))  # noqa: SLF001 - its end
    launched: list[str] = []

    def launch(_store, c, _settings, _log):
        launched.append(c.env.check)
        return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.CHECK_START, reason="test copy prepared")

    monkeypatch.setattr(prepare, "launch", launch)
    replace(shared, rule, "The pages are plain HTML, served as they are.")

    c = step(store, tmp_path)

    assert launched == []  # no export, restore or seed before the owner answers
    assert loop.open_question(c).cause.startswith("decisions:check:")
    assert not prepare.read(store, "c1", "old").open  # the gone check's cleanup ran all the same
    answer(store, "continue")
    step(store, tmp_path)
    assert launched == ["preview"]
    assert ran == []


def test_the_hosts_launch_of_a_check_environment_waits_for_the_gate(tmp_path, shared, monkeypatch):
    rule = put(shared, make())
    store = stored(tmp_path, shared, checking())
    started: list[str] = []
    monkeypatch.setattr(check, "start", lambda e, *_a, **_k: started.append(e.command))
    host = SimpleNamespace(store=store, env_action=lambda _c: "launch", clear=lambda _c, _e: {}, say=print)
    replace(shared, rule, "The pages are plain HTML, served as they are.")

    c = environment.launch(host, Lock("c1"), store.read("c1"), AT)

    assert started == []
    assert loop.open_question(c).cause.startswith("decisions:check:")
    assert c.env.launched_at is None  # nothing started, so its disposal has nothing left to find
    shutil.rmtree(shared.root / PROJECT)
    stopped = environment.launch(host, Lock("c1"), store.read("c1"), AT)
    assert (started, stopped.stop.kind) == ([], ErrorKind.STATE)
    assert environment.launch(host, Lock("c1"), stopped, AT) is stopped  # one stop, not one per host pass


def test_a_resumed_worker_receives_the_decisions_with_its_answer_and_its_continuation(
    tmp_path, shared, change_repo, monkeypatch
):
    rule = put(shared, make())
    asked = Question(id="q1", step=K.BUILD, text="Which colour?", answer=Answer(at=AT, text="Blue"))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    monkeypatch.setattr(runner.session_choice, "opening", lambda *_a: (asked, None, False, True))
    monkeypatch.setattr(sdk_adapter, "usage_read", lambda *_a: asyncio.sleep(0, {}))
    sent: list[str] = []

    async def send(message, **_k):
        sent.append(message)

    def kept(_store, _lock, _change, path, config):
        cfg = dataclasses.replace(config(path), effort="")
        seen = SimpleNamespace(type=SimpleNamespace(value="user.message"), data=SimpleNamespace(content=cfg.message))
        session = SimpleNamespace(get_events=lambda: asyncio.sleep(0, [seen]), send=send)
        client = SimpleNamespace(get_session_metadata=lambda _s: asyncio.sleep(0, {}))
        client.resume_session = lambda _s, **_o: asyncio.sleep(0, session)
        sent.append(cfg.message)
        loop_ = SimpleNamespace(call_soon_threadsafe=lambda *_: None)
        asyncio.run(sdk_adapter._open(client, sdk_adapter._Step(cfg, loop_)))  # noqa: SLF001
        raise Started

    monkeypatch.setattr(runner, "_kept", kept)
    store = stored(tmp_path, shared, change())

    with pytest.raises(Started):
        step(store, change_repo)

    resumed, continued = sent
    assert resumed.startswith(step_input.answer(asked))
    assert continued.startswith(step_input.CONTINUE)  # the answer reached it before an interruption
    for message in sent:
        assert step_decisions.HEAD in message
        assert rule.statement in message


def test_a_test_reviewer_receives_the_decisions_in_force(tmp_path, shared, change_repo, monkeypatch):
    rule = put(shared, make())
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    shares = [Share(paths=["web/test_notes.py"], lines=20)]
    review = TestReview(commit=worktree.head(change_repo), packages=["web"], shares=shares)
    store = stored(tmp_path, shared, change(K.TESTS, tests=review))
    seen: list[str] = []

    def judges(_store, _lock, _change, path, made, _settings, **_k):
        seen.extend(cfg.message for _, cfg in made(path))
        raise Started

    monkeypatch.setattr(curation.sessions, "judges", judges)

    with pytest.raises(Started):
        step(store, change_repo)

    assert len(seen) == 1
    assert step_decisions.HEAD in seen[0]
    assert f"{rule.id} (project, approved): {rule.title}: {rule.statement}" in seen[0]
