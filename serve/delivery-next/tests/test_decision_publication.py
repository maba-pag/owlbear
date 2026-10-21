"""A brief's project decisions are published by its approval, through the real route (TD-453, slice 3)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, LinkType, Origin, Scope, State, new_id, read, validate_repo
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import Brief, Change, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store import change_record, decision_store
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
WHERE = "Where do notes live?"
LASTING = {"question": WHERE, "answer": "Notes live in one SQLite table.", "origin": "decided", "scope": "project"}
OWN = {"question": "Limit the notes?", "answer": "A note keeps 800 characters at most.", "origin": "approved"}
APPROVED = "decisions: shop-site: add-farewell brief v{} approved"
MERGED = PullRequest(
    repository="acme/shop-site", number=7, node_id="n", url="https://x/pull/7", head_branch="owlbear/a",
    head_sha="a" * 40, base_branch="main", draft=False, state="closed", merged=True, merge_commit_sha="b" * 40,
)  # fmt: skip


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def rel(decision_id: str) -> str:
    return f"{PROJECT}/decisions/{decision_id}.md"


def commits(remote: Path, path: str = "") -> list[str]:
    return git(remote, "log", "--format=%s", "main", "--", *([path] if path else [])).splitlines()


def shape(picking, version: int = 1, *decisions: dict) -> Change:
    """Brief *version* with *decisions*, saved, challenged and picked through the host API: approvable."""
    assert picking.save(decisions=list(decisions))["version"] == version
    assert picking.ask(version).status_code == 200
    picking.picks.append(pick_tools.PickResult(picked=[]))
    picking.verdicts.append(tools.ReviewResult(verdict="pass", findings=[]))
    picking.step()
    picking.picks.clear()  # the list held none but the Change's own: nothing to pick, no session
    return picking.change()


def reshape(picking) -> None:
    """The owner asks for a change after approval: the Change shapes a new version."""
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        c.step = Step(kind=StepKind.SHAPE)
        picking.store.write(lock, c)


def running(store: Store) -> Change:
    """Change tags, approved before the other and building, its decisions pinned then."""
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Tags", scope=["web"])
    plan = Plan(tasks=[Task(id="t1", title="Tag notes", scope=["web"], checks=["true"])])
    c = Change(slug="tags", brief=brief, plan=plan, names=Names(branch="owlbear/tags", target="main"),
               step=Step(kind=StepKind.BUILD, task="t1"))  # fmt: skip
    c.decisions_baseline = decisions_gate.pinned(store, c, AT, decisions_gate.loaded(store))[0]
    store.write(Lock("tags"), c)
    return c


def stepped(picking, slug: str) -> Change:
    c = picking.store.read(slug)
    runner._step(picking.store, Lock(slug), c, loop.next_step(c, AT), picking.repo)  # noqa: SLF001
    return picking.store.read(slug)


def test_approval_publishes_in_force_at_once_and_another_change_meets_it_before_this_ones_runner_runs(
    picking, shared_repo, monkeypatch
):
    root, remote = shared_repo
    lasting, own = shape(picking, 1, LASTING, OWN).brief.decisions
    running(picking.store)
    before = len(commits(remote))

    assert picking.approve(1).status_code == 200

    rule = read(root / rel(lasting.id))
    assert (rule.state, rule.scope, rule.origin, rule.statement) == (
        State.IN_FORCE, Scope.PROJECT, Origin.DECIDED, "Notes live in one SQLite table.",
    )  # fmt: skip
    assert (commits(remote, rel(lasting.id)), len(commits(remote))) == ([APPROVED.format(1)], before + 1)
    assert not list(root.rglob(f"{own.id}.md"))  # the Change's own stays with it until its end
    ran: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: ran.append(c.slug))

    tags = stepped(picking, "tags")  # its approving Change's runner has not run: the approval is still queued

    assert ran == []
    assert f"new: {lasting.id} {WHERE}" in loop.open_question(tags).text  # its gate asks, as for any new rule
    a = picking.approved()
    (p,) = a.decisions_published
    assert (p.id, p.title, p.state, p.revision) == (lasting.id, WHERE, "in_force", rule.revision)
    assert (p.saved, p.committed, p.published, p.notice) == (True, True, True, "")
    assert a.decisions_baseline.revisions[lasting.id] == rule.rule_revision
    stepped(picking, picking.slug)
    assert ran == [picking.slug]  # its own decision asks nothing of it


def test_a_save_that_fails_refuses_the_approval_and_queues_nothing(picking, shared_repo, monkeypatch):
    root, remote = shared_repo
    shape(picking, 1, LASTING)
    before = commits(remote)

    def unavailable(*_args, **_kwargs):
        msg = "the shared data repository is held by another save"
        raise decision_store.DecisionsUnavailable(msg)

    monkeypatch.setattr(decision_store, "save_all", unavailable)
    said = picking.approve(1)

    assert said.status_code == 409
    assert said.json()["detail"].startswith("the brief's project decisions were not saved, so it is not approved")
    assert "held by another save" in said.json()["detail"]
    a = picking.approved()
    assert (a.brief.approved_version, a.step.kind, a.decisions_published) == (None, StepKind.SHAPE, [])
    assert (commits(remote), list((root / PROJECT).rglob("D-*.md"))) == (before, [])


def test_a_failed_push_lets_approval_proceed_shows_on_the_card_and_the_next_save_pushes_it(picking, shared_repo):
    root, remote = shared_repo
    git(root, "add", "-A")
    git(root, "commit", "-qm", "settings: shop-site claimed")  # as setup publishes it
    (lasting,) = shape(picking, 1, LASTING).brief.decisions
    away = remote.rename(remote.with_name("away.git"))

    assert picking.approve(1).status_code == 200

    a = picking.approved()
    assert a.brief.approved_version == 1
    (p,) = a.decisions_published
    assert (p.saved, p.committed, p.published) == (True, True, False)
    assert read(root / rel(lasting.id)).state == State.IN_FORCE  # this machine's other Changes read it at once
    assert "push failed" in p.notice
    (line,) = api.summary(picking.store, picking.slug, Activity(host_up=True), AT)["decisions"]
    assert line.startswith(f"Project decisions not yet pushed: {WHERE}: saved and committed")
    assert line.endswith("the data repository's next save pushes them")

    away.rename(remote)
    other = Decision(id=new_id(), title="Tags are free text", statement="A tag is any text.", scope=Scope.PROJECT,
                     project=PROJECT, origin=Origin.APPROVED, actor="shaper", state=State.IN_FORCE,
                     created_at=AT)  # fmt: skip
    assert decision_store.save(picking.shared, other, expected_revision=None, message="decisions: tags").published

    assert commits(remote, rel(lasting.id)) == [APPROVED.format(1)]
    assert api.summary(picking.store, picking.slug, Activity(host_up=True), AT)["decisions"] == []


def test_approving_the_same_version_again_rewrites_the_same_file_without_a_commit(picking, shared_repo):
    root, remote = shared_repo
    (lasting,) = shape(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    written, before = (root / rel(lasting.id)).read_text(), commits(remote)

    assert picking.approve(1).status_code == 200  # a retried request: the pick still holds

    assert ((root / rel(lasting.id)).read_text(), commits(remote)) == (written, before)
    (p,) = picking.approved().decisions_published
    assert (p.id, p.published, p.revision) == (lasting.id, True, read(root / rel(lasting.id)).revision)


@pytest.mark.parametrize("pr", [None, MERGED], ids=["abandoned", "merged"])
def test_the_changes_end_keeps_a_published_decision_in_force_and_archives_its_own(picking, shared_repo, pr):
    root, remote = shared_repo
    lasting, own = shape(picking, 1, LASTING, OWN).brief.decisions
    picking.approve(1)
    a = picking.approved()
    published = read(root / rel(lasting.id))

    assert change_record.save(picking.store, a, pr, AT + timedelta(days=1)) == ""

    rule = read(root / rel(lasting.id))
    assert (rule.state, rule.revision) == (State.IN_FORCE, published.revision)  # never demoted to a draft
    assert len(commits(remote, rel(lasting.id))) == 1  # never saved again
    (kept,) = root.rglob(f"{own.id}.md")
    assert kept.parent.parent.name == decisions_gate.stem(a)
    assert read(kept).state == (State.SPENT if pr else State.WITHDRAWN)
    assert validate_repo(root) == []


def test_a_later_version_replacing_a_published_decision_retires_it_with_its_successor_in_one_commit(
    picking, shared_repo
):
    root, remote = shared_repo
    (first,) = shape(picking, 1, LASTING).brief.decisions
    picking.approve(1)
    picking.approved()
    reshape(picking)
    (later,) = shape(picking, 2, LASTING | {"answer": "Notes live in Postgres."}).brief.decisions
    assert later.replaces == first.id

    assert picking.approve(2).status_code == 200

    old, new = read(root / rel(first.id)), read(root / rel(later.id))
    assert (old.state, old.statement, new.state) == (State.REPLACED, "Notes live in one SQLite table.", State.IN_FORCE)
    assert old.rationale.endswith("Replaced by brief v2 of Change add-farewell.")
    assert [(x.type, x.target) for x in new.links] == [(LinkType.REPLACES, first.id)]
    assert commits(remote, rel(later.id)) == commits(remote, rel(first.id))[:1] == [APPROVED.format(2)]
    a = picking.approved()
    assert {p.id: p.state for p in a.decisions_published} == {first.id: "replaced", later.id: "in_force"}
    assert (first.id in a.decisions_baseline.revisions, later.id in a.decisions_baseline.revisions) == (False, True)
    assert validate_repo(root) == []


def test_a_published_decision_a_later_version_moves_into_the_change_is_withdrawn_and_archived_at_the_end(
    picking, shared_repo
):
    root, _ = shared_repo
    (first,) = shape(picking, 1, LASTING).brief.decisions
    picking.approve(1)
    picking.approved()
    reshape(picking)
    (later,) = shape(picking, 2, LASTING | {"scope": "change"}).brief.decisions
    assert (later.id != first.id, later.replaces) == (True, first.id)  # a changed scope is a successor

    assert picking.approve(2).status_code == 200

    old = read(root / rel(first.id))
    assert (old.state, old.scope, old.statement) == (State.WITHDRAWN, Scope.PROJECT, "Notes live in one SQLite table.")
    assert old.rationale.endswith("Withdrawn by brief v2 of Change add-farewell: it moved into that Change's own "
                                  "decisions.")  # fmt: skip
    assert not list(root.rglob(f"{later.id}.md"))  # the Change's own waits for its end
    a = picking.approved()
    assert first.id not in a.decisions_baseline.revisions

    assert change_record.save(picking.store, a, MERGED, AT + timedelta(days=1)) == ""

    (kept,) = root.rglob(f"{later.id}.md")
    moved = read(kept)
    assert (moved.scope, moved.state, kept.parent.parent.name) == (Scope.CHANGE, State.SPENT, decisions_gate.stem(a))
    assert [(x.type, x.target) for x in moved.links] == [(LinkType.RELATED_TO, first.id)]
    assert read(root / rel(first.id)) == old  # its end never writes over it
    assert validate_repo(root) == []


def test_a_project_successor_of_the_changes_own_decision_is_published_without_a_dangling_link(picking, shared_repo):
    root, _ = shared_repo
    (first,) = shape(picking, 1, OWN).brief.decisions
    picking.approve(1)
    picking.approved()
    assert not list(root.rglob(f"{first.id}.md"))  # nothing of v1 is for the project
    reshape(picking)
    (later,) = shape(picking, 2, OWN | {"scope": "project"}).brief.decisions
    assert later.replaces == first.id

    assert picking.approve(2).status_code == 200

    rule = read(root / rel(later.id))
    assert (rule.state, rule.links) == (State.IN_FORCE, ())
    assert f"It replaces {first.id}, a decision for this Change alone in an earlier version." in rule.rationale
    assert validate_repo(root) == []

    assert change_record.save(picking.store, picking.approved(), MERGED, AT + timedelta(days=1)) == ""

    (kept,) = root.rglob(f"{first.id}.md")
    assert (read(kept).scope, read(kept).state) == (Scope.CHANGE, State.WITHDRAWN)
    assert read(root / rel(later.id)) == rule
    assert validate_repo(root) == []
