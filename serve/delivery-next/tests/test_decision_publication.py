"""A brief's project decisions are published from its approval (TD-453, slice 3); abandonment revokes nothing."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Origin, Scope, State, new_id, read, validate_repo
from owlbear_delivery_next.change_contracts.inbox import BriefApproval
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    BriefDecision,
    Change,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_flow import loop, status
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import change_record
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
WHERE = "Where do notes live?"
MERGED = PullRequest(
    repository="acme/shop-site", number=7, node_id="n", url="https://x/pull/7", head_branch="owlbear/a",
    head_sha="a" * 40, base_branch="main", draft=False, state="closed", merged=True, merge_commit_sha="b" * 40,
)  # fmt: skip


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def store(tmp_path, shared_repo) -> Store:
    shared = DataRepo(shared_repo[0])
    shared.claim(PROJECT, "github.com/acme/shop-site")
    return Store(tmp_path / "store", shared, PROJECT)


@pytest.fixture
def ran(monkeypatch) -> list[str]:
    """The Changes whose step started past the decision gate."""
    seen: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: seen.append(c.slug))
    return seen


def shaped(store: Store) -> Change:
    """Change a, its brief v1 challenged: one project decision and one for the Change alone."""
    lasting = BriefDecision(id=new_id(AT), question=WHERE, answer="Notes live in one SQLite table.", origin="decided",
                            scope="project")  # fmt: skip
    own = BriefDecision(id=new_id(AT), question="Limit the notes?", answer="A note keeps 800 characters at most.",
                        origin="approved")  # fmt: skip
    brief = Brief(version=1, challenged=1, title="Notes", scope=["web"], decisions=[lasting, own])
    c = Change(slug="a", brief=brief, names=Names(branch="owlbear/a", target="main"))
    store.write(Lock("a"), c)
    return c


def approve(store: Store, slug: str, version: int = 1, at: datetime = AT) -> Change:
    """The owner's approval as its route queues it, folded by the store."""
    c = store.read(slug)
    baseline, owed = decisions_gate.pinned(store, c, at, decisions_gate.loaded(store))
    store.put_inbox(slug, BriefApproval(at=at, version=version, baseline=baseline, unpinned=owed))
    return store.fold(Lock(slug), slug, at)[0]


def running(store: Store) -> Change:
    """Change b, approved before a and building, its decisions pinned then."""
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Tags", scope=["web"])
    plan = Plan(tasks=[Task(id="t1", title="Tag notes", scope=["web"], checks=["true"])])
    c = Change(slug="b", brief=brief, plan=plan, names=Names(branch="owlbear/b", target="main"),
               step=Step(kind=StepKind.BUILD, task="t1"))  # fmt: skip
    c.decisions_baseline = decisions_gate.pinned(store, c, AT, decisions_gate.loaded(store))[0]
    store.write(Lock("b"), c)
    return c


def step(store: Store, slug: str, repo: Path) -> Change:
    c = store.read(slug)
    runner._step(store, Lock(slug), c, loop.next_step(c, AT), repo)  # noqa: SLF001
    return store.read(slug)


def rel(c: Change, i: int = 0) -> str:
    return f"{PROJECT}/decisions/{c.brief.decisions[i].id}.md"


def commits(remote: Path, path: str) -> list[str]:
    return git(remote, "log", "--format=%s", "main", "--", path).splitlines()


def test_approval_publishes_the_project_decision_in_force_and_another_change_meets_it_at_its_next_step(
    store, shared_repo, tmp_path, ran
):
    root, remote = shared_repo
    running(store)
    shaped(store)
    a = approve(store, "a")
    assert a.step.kind == StepKind.PLAN
    lasting, own = a.brief.decisions

    a = step(store, "a", tmp_path)

    assert ran == ["a"]  # its own decision asks nothing of it
    rule = read(root / rel(a))
    assert (rule.state, rule.scope, rule.origin, rule.statement) == (
        State.IN_FORCE, Scope.PROJECT, Origin.DECIDED, "Notes live in one SQLite table.",
    )  # fmt: skip
    assert (rule.read_back, rule.created_at) == (AT.date().isoformat(), AT)  # confirmed at the approval
    (p,) = a.decisions_published
    assert (p.id, p.title, p.state, p.revision) == (lasting.id, WHERE, "in_force", rule.revision)
    assert (p.saved, p.committed, p.published, p.notice) == (True, True, True, "")
    assert commits(remote, rel(a)) == ["decisions: shop-site: a brief v1 approved"]
    assert a.decisions_baseline.revisions[lasting.id] == rule.rule_revision
    assert not list(root.rglob(f"{own.id}.md"))  # the Change's own stays with it until its end

    b = step(store, "b", tmp_path)

    assert ran == ["a"]
    assert f"new: {lasting.id} {WHERE}" in loop.open_question(b).text  # the gate asks b's owner, as for any new rule


def test_a_failed_push_is_shown_on_the_change_and_the_next_step_publishes_it_once(store, shared_repo, tmp_path, ran):
    root, remote = shared_repo
    shaped(store)
    approve(store, "a")
    away = remote.rename(remote.with_name("away.git"))

    a = step(store, "a", tmp_path)

    assert ran == ["a"]  # the work goes on
    (p,) = a.decisions_published
    assert (p.saved, p.committed, p.published) == (True, True, False)
    assert "push failed" in p.notice
    (line,) = status.card(a, status.Activity(host_up=True), [], AT)["decisions"]
    assert line.startswith(f"Project decisions not yet published: {WHERE}: saved and committed")
    assert line.endswith("Delivery saves them again at the next step")
    written = (root / rel(a)).read_text()

    away.rename(remote)
    a = step(store, "a", tmp_path)

    assert a.decisions_published[0].published
    assert status.card(a, status.Activity(host_up=True), [], AT)["decisions"] == []
    assert (root / rel(a)).read_text() == written
    assert len(commits(remote, rel(a))) == 1
    count = git(remote, "rev-list", "--count", "main")
    step(store, "a", tmp_path)
    assert git(remote, "rev-list", "--count", "main") == count  # settled: nothing is saved again


def test_a_restart_after_the_save_before_its_receipt_was_recorded_publishes_nothing_twice(
    store, shared_repo, tmp_path, ran
):
    root, remote = shared_repo
    shaped(store)
    before = approve(store, "a")
    step(store, "a", tmp_path)
    written, count = (root / rel(before)).read_text(), git(remote, "rev-list", "--count", "main")
    store.write(Lock("a"), before)  # the runner died between the save and writing the Change

    a = step(store, "a", tmp_path)

    assert [(p.saved, p.published) for p in a.decisions_published] == [(True, True)]
    assert (root / rel(a)).read_text() == written
    assert git(remote, "rev-list", "--count", "main") == count
    assert ran == ["a", "a"]  # the pin took it in again: no question


@pytest.mark.usefixtures("ran")
@pytest.mark.parametrize("pr", [None, MERGED], ids=["abandoned", "merged"])
def test_the_changes_end_keeps_a_published_decision_in_force_and_archives_its_own(store, shared_repo, tmp_path, pr):
    root, remote = shared_repo
    shaped(store)
    approve(store, "a")
    a = step(store, "a", tmp_path)
    published = read(root / rel(a))

    assert change_record.save(store, a, pr, AT + timedelta(days=1)) == ""

    rule = read(root / rel(a))
    assert (rule.state, rule.revision) == (State.IN_FORCE, published.revision)  # never demoted to a draft
    assert len(commits(remote, rel(a))) == 1  # never saved again
    (own,) = root.rglob(f"{a.brief.decisions[1].id}.md")
    assert (own.parent.parent.name, read(own).state) == (decisions_gate.stem(a), State.SPENT if pr else State.WITHDRAWN)
    assert validate_repo(root) == []


def test_a_later_approved_version_retires_the_published_decision_its_successor_replaces(
    store, shared_repo, tmp_path, ran
):
    root, _ = shared_repo
    shaped(store)
    approve(store, "a")
    a = step(store, "a", tmp_path)
    first = a.brief.decisions[0]
    later = BriefDecision(id=new_id(AT), question=WHERE, answer="Notes live in Postgres.", origin="decided",
                          scope="project", replaces=first.id)  # fmt: skip
    a.brief = a.brief.model_copy(update={"version": 2, "challenged": 2, "decisions": [later, a.brief.decisions[1]]})
    a.step = Step(kind=StepKind.SHAPE)
    store.write(Lock("a"), a)
    approve(store, "a", 2, AT + timedelta(hours=1))

    a = step(store, "a", tmp_path)

    assert read(root / f"{PROJECT}/decisions/{first.id}.md").state == State.REPLACED
    assert read(root / f"{PROJECT}/decisions/{later.id}.md").state == State.IN_FORCE
    assert {p.id: p.state for p in a.decisions_published} == {first.id: "replaced", later.id: "in_force"}
    assert validate_repo(root) == []
    assert ran == ["a", "a"]  # its own replacement asks nothing of it
