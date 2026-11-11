"""A brief's project decisions are published by its approval, through the real route (TD-453, slice 3)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import (
    Decision,
    Link,
    LinkType,
    Origin,
    ReadBackKind,
    Scope,
    State,
    new_id,
    read,
    validate_repo,
    write,
)
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.inbox import BriefApproval
from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow import loop, status
from owlbear_delivery_next.change_flow.budgets import EPISODE_ASK
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.commands.runner import _run
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.state_store import change_record, decision_archive, decision_batch, decision_store
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import decision_publication, decisions_gate

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
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
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


def approvable(picking, version: int, *decisions: dict) -> Change:
    """Seed a reviewed, empty-pick brief for approval adapters; shape owns the full workflow witness."""
    assert picking.save(decisions=list(decisions))["version"] == version
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        c.brief.challenged = version
        c.brief.picked = Pick(version=version, status="ok")
        picking.store.write(lock, c)
    return c


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


def approved_binding(c, root, choice, answer):
    """Reopen the exact binding and its actual approval receipt and pin."""
    rule = read(root / rel(choice.id))
    assert (rule.state, rule.scope, rule.origin) == (State.IN_FORCE, Scope.PROJECT, Origin.DECIDED)
    assert rule.statement != answer
    assert decision_archive.whole(rule) == answer
    assert len(c.decisions_published) == (2 if choice.replaces else 1)
    p = next(p for p in c.decisions_published if p.id == choice.id)
    assert (p.id, p.title, p.state, p.revision) == (choice.id, WHERE, "in_force", rule.revision)
    assert (p.saved, p.committed, p.published, p.notice) == (True, True, True, "")
    assert c.decisions_baseline.revisions[choice.id] == rule.rule_revision
    assert c.decisions_baseline.said[choice.id].statement == answer
    return rule


@pytest.mark.parametrize("ending", ["merged", "unchanged", "abandoned"])
def test_approved_rule_is_visible_replaced_and_retained_at_end(
    picking, shared_repo, monkeypatch, ending
):
    root, remote = shared_repo
    answer = (
        "Notes live in one SQLite table. " * 6
        + "\n\n## Whole wording\nKeep this literal heading inside the rule."
        + "\n\n## Reason\nThis is binding text, including the important final suffix: keep backups readable."
    )
    lasting, own = shape(picking, 1, LASTING | {"answer": answer}, OWN).brief.decisions
    running(picking.store)
    before, owner_status = len(commits(remote)), git(root, "status", "--porcelain", "--untracked-files=all")

    assert picking.approve(1).status_code == 200

    rule = approved_binding(picking.approved(), root, lasting, answer)
    assert (commits(remote, rel(lasting.id)), len(commits(remote))) == ([APPROVED.format(1)], before + 1)
    assert not list(root.rglob(f"{own.id}.md"))  # the Change's own stays with it until its end
    ran: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: ran.append(c.slug))

    tags = stepped(picking, "tags")  # its approving Change's runner has not run yet

    assert ran == []
    assert f"new: {lasting.id} {WHERE}" in loop.open_question(tags).text  # its gate asks, as for any new rule
    written, before = (root / rel(lasting.id)).read_bytes(), commits(remote)
    assert picking.approve(1).status_code == 200
    assert ((root / rel(lasting.id)).read_bytes(), commits(remote)) == (written, before)
    (again,) = picking.approved().decisions_published
    assert (again.id, again.published, again.revision) == (lasting.id, True, rule.revision)
    stepped(picking, picking.slug)
    assert ran == [picking.slug]  # its own decision asks nothing of it
    monkeypatch.setattr(runner, "_run", _run)
    reshape(picking)
    successor_answer = answer + "\nThe successor also keeps restore instructions."
    later, kept_own = shape(picking, 2, LASTING | {"answer": successor_answer}, OWN).brief.decisions
    assert (later.replaces, kept_own.id) == (lasting.id, own.id)
    assert (accepted := picking.approve(2)).status_code == 200, accepted.json()
    a = picking.approved()
    old, new = read(root / rel(lasting.id)), approved_binding(a, root, later, successor_answer)
    assert (old.state, new.state) == (State.REPLACED, State.IN_FORCE)
    assert decision_archive.whole(old) == answer
    assert old.rationale.endswith("Replaced by brief v2 of Change add-farewell.")
    assert [(x.type, x.target) for x in new.links] == [(LinkType.REPLACES, lasting.id)]
    assert commits(remote, rel(later.id)) == commits(remote, rel(lasting.id))[:1] == [APPROVED.format(2)]
    assert git(remote, "log", "-1", "--format=%H", "main", "--", rel(later.id)) == git(
        remote, "log", "-1", "--format=%H", "main", "--", rel(lasting.id)
    )
    assert {p.id: p.state for p in a.decisions_published} == {lasting.id: "replaced", later.id: "in_force"}
    assert lasting.id not in a.decisions_baseline.revisions
    published = (root / rel(later.id)).read_bytes()
    if ending == "unchanged":
        a.tests = TestReview(commit="c" * 40, packages=[], shares=[], unchanged=True)
    assert change_record.save(picking.store, a, MERGED if ending == "merged" else None, AT + timedelta(days=1)) == ""
    assert ((root / rel(later.id)).read_bytes(), read(root / rel(later.id))) == (published, new)
    assert len(commits(remote, rel(later.id))) == 1
    (kept,) = root.rglob(f"{own.id}.md")
    stem = decisions_gate.stem(a)
    assert (kept.parent.parent.name, read(kept).state) == (
        stem, State.WITHDRAWN if ending == "abandoned" else State.SPENT
    )
    record = f"{PROJECT}/changes/{stem}.json"
    assert git(remote, "log", "-1", "--format=%H", "main", "--", record) == git(
        remote, "log", "-1", "--format=%H", "main", "--", kept.relative_to(root).as_posix()
    )
    assert validate_repo(root) == []
    assert git(root, "status", "--porcelain", "--untracked-files=all") == owner_status


def test_failed_approval_preserves_shape_and_reports_its_whole_reason(picking, shared_repo, monkeypatch, whole_error):
    root, remote = shared_repo
    approvable(picking, 1, LASTING)
    before = commits(remote)

    monkeypatch.setattr(decision_store, "save_all", _unavailable(whole_error))
    said = picking.approve(1)

    assert said.status_code == 409
    reason = f"{decision_publication.REFUSED}: DecisionsUnavailable: {whole_error}\nNOTE-MARK"
    assert said.json()["detail"] == reason
    (event,) = [e for e in picking.store.events(picking.slug) if e.get("event") == "approval-refused"]
    assert event["reason"] == reason
    a = picking.approved()
    assert (a.brief.approved_version, a.step.kind, a.decisions_published) == (None, StepKind.SHAPE, [])
    assert (commits(remote), list((root / PROJECT).rglob("D-*.md"))) == (before, [])


def test_a_failed_push_lets_approval_proceed_shows_on_the_card_and_the_next_save_pushes_it(picking, shared_repo):
    root, remote = shared_repo
    git(root, "add", "-A")
    git(root, "commit", "-qm", "settings: shop-site claimed")  # as setup publishes it
    (lasting,) = approvable(picking, 1, LASTING).brief.decisions
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
    with picking.store.lock(picking.slug) as lock:
        done = picking.store.read(picking.slug)
        done.finished_at = AT  # its cleanup never pushes them: the line stays
        picking.store.write(lock, done)
    assert api.summary(picking.store, picking.slug, Activity(host_up=True), AT)["decisions"] == [line]

    away.rename(remote)
    other = Decision(id=new_id(), title="Tags are free text", statement="A tag is any text.", scope=Scope.PROJECT,
                     project=PROJECT, origin=Origin.APPROVED, actor="shaper", state=State.IN_FORCE,
                     created_at=AT)  # fmt: skip
    assert decision_store.save(picking.shared, other, expected_revision=None, message="decisions: tags").published

    assert commits(remote, rel(lasting.id)) == [APPROVED.format(1)]
    assert api.summary(picking.store, picking.slug, Activity(host_up=True), AT)["decisions"] == []


def test_approve_on_a_version_saved_after_its_loop_ended_challenges_it_then_the_host_approves_it(picking, monkeypatch):
    """#986: Approve starts the round of a version saved after its loop ended, its decisions picked first; once the
    round raised nothing, the host's next pass approves it as the owner's Approve would, even while paused."""
    shape(picking, 1)
    assert picking.save(decisions=[LASTING])["version"] == 2  # the loop ended on v1: v2 waits for one more round
    (lasting,) = picking.change().brief.decisions
    assert picking.approve(2).json() == {"accepted": "brief-challenge"}
    c = picking.change()
    assert (c.brief.approve_if_clean, c.brief.approved_version, c.brief.picked.status) == (2, None, "owed")
    picking.verdicts.append(tools.ReviewResult(verdict="pass", findings=[]))
    assert picking.step().brief.challenged == 2
    spawned: list[str] = []
    monkeypatch.setattr(data_repo, "folder", lambda *_a: picking.PROJECT)  # the test clone has no claimed remote
    host = Host(picking.store, picking.repo, spawn=lambda slug: spawned.append(slug) or RunnerRecord(
        pid=9, created=1.0, started_at=AT), members=lambda _ids: {})  # fmt: skip
    host.paused = lambda: True
    assert host.tick(datetime.now(UTC)) == []
    a = picking.store.read(picking.slug)
    assert (a.brief.approved_version, a.brief.approve_if_clean, a.step.kind, spawned) == (2, None, StepKind.PLAN, [])
    assert (a.decisions_baseline is not None, a.decisions_unpinned_at) == (True, None)  # pinned as the owner's
    (p,) = a.decisions_published
    assert (p.id, p.published) == (lasting.id, True)
    assert loop.next_step(a, datetime.now(UTC)).kind == StepKind.PLAN  # planning waits only for Resume


def test_a_commit_a_hook_refuses_puts_the_files_back_and_refuses_the_approval(picking, shared_repo):
    root, _ = shared_repo
    approvable(picking, 1, LASTING)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\necho refused by policy >&2\nexit 1\n")
    hook.chmod(0o755)
    state = (git(root, "rev-parse", "HEAD"), git(root, "status", "--porcelain"), git(root, "diff", "--cached"))

    said = picking.approve(1)

    assert said.status_code == 409
    assert "refused by policy" in said.json()["detail"]
    assert git(root, "rev-parse", "HEAD") == state[0]  # the refused commit is not made
    assert decision_batch.pending(picking.shared) is not None  # interrupted: the staged rules are not settled
    with pytest.raises(decision_store.DecisionsUnavailable):  # no rule the refused commit held is read by other Changes
        decision_store.load(picking.shared, PROJECT)
    a = picking.approved()
    assert (a.brief.approved_version, a.step.kind, a.decisions_published) == (None, StepKind.SHAPE, [])


def test_the_brief_cannot_change_while_its_approval_publishes(picking, monkeypatch):
    approvable(picking, 1, LASTING)
    real, said = decision_store.save_all, []

    def saving(*args, **kwargs):
        said.append(picking.save(title="Add a farewell page"))  # the shaper saves v2 during the Git work
        return real(*args, **kwargs)

    monkeypatch.setattr(decision_store, "save_all", saving)

    assert picking.approve(1).status_code == 200

    assert "try again" in said[0]["errors"][0]
    a = picking.approved()
    assert (a.brief.version, a.brief.approved_version, a.step.kind) == (1, 1, StepKind.PLAN)


class Crash(Exception):  # noqa: N818 - the host process dies
    pass


def test_an_approval_interrupted_after_its_commit_stays_and_its_next_step_saves(picking, shared_repo, monkeypatch):
    root, remote = shared_repo
    (lasting,) = approvable(picking, 1, LASTING).brief.decisions
    real = decision_store.save_all

    def crashed(*args, **kwargs):
        real(*args, **kwargs)
        raise Crash

    monkeypatch.setattr(decision_store, "save_all", crashed)
    with pytest.raises(Crash):
        picking.approve(1)
    monkeypatch.setattr(decision_store, "save_all", real)

    a = picking.approved()
    (p,) = a.decisions_published
    assert (a.brief.approved_version, p.id, p.committed) == (1, lasting.id, False)  # recorded before Git, planned
    assert picking.save(title="Add a farewell page")["errors"]  # an approved answer is never reused for another
    ran: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: ran.append(c.slug))

    c = stepped(picking, picking.slug)

    rule = read(root / rel(lasting.id))
    (p,) = c.decisions_published
    assert (p.committed, p.published, p.revision, ran) == (True, True, rule.revision, [picking.slug])
    assert commits(remote, rel(lasting.id)) == [APPROVED.format(1)]  # saved again without another commit
    assert c.decisions_baseline.revisions[lasting.id] == rule.rule_revision


def test_an_interrupted_later_approval_keeps_the_receipt_of_an_unchanged_own_decision(
    picking, shared_repo, monkeypatch
):
    root, _ = shared_repo
    (lasting,) = approvable(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    (v1,) = picking.approved().decisions_published
    reshape(picking)
    more = {"question": "How long is a note?", "answer": "A note is one paragraph.", "origin": "decided",
            "scope": "project"}  # fmt: skip
    added = approvable(picking, 2, LASTING, more).brief.decisions[1]
    real = decision_store.save_all

    def crashed(*args, **kwargs):
        real(*args, **kwargs)
        raise Crash

    monkeypatch.setattr(decision_store, "save_all", crashed)
    with pytest.raises(Crash):
        picking.approve(2)
    monkeypatch.setattr(decision_store, "save_all", real)
    picking.approved()
    rule = read(root / rel(lasting.id))
    write(rule.model_copy(update={"title": "Where notes are kept"}), root / PROJECT, rule.revision)  # Decisions page
    ran: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: ran.append(c.slug))

    c = stepped(picking, picking.slug)

    kept = {p.id: p for p in c.decisions_published}
    assert (kept[lasting.id].revision, kept[lasting.id].committed) == (v1.revision, True)
    assert (kept[added.id].committed, kept[added.id].revision) == (True, read(root / rel(added.id)).revision)
    assert f"changed: {lasting.id}" in loop.open_question(c).text
    assert ran == []


def test_a_recovery_that_fails_waits_with_its_reason_and_the_next_step_saves_before_work(
    picking, shared_repo, monkeypatch
):
    root, remote = shared_repo
    (lasting,) = approvable(picking, 1, LASTING).brief.decisions
    real, tries = decision_store.save_all, []

    def crashed(*_args, **_kwargs):
        raise Crash

    def held_once(*args, **kwargs):
        tries.append(args)
        if len(tries) == 1:
            msg = "the shared data repository is held by another save"
            raise decision_store.DecisionsUnavailable(msg)
        return real(*args, **kwargs)

    monkeypatch.setattr(decision_store, "save_all", crashed)
    with pytest.raises(Crash):
        picking.approve(1)  # recorded with its saves planned, then the host dies before Git
    monkeypatch.setattr(decision_store, "save_all", held_once)
    ran: list[str] = []
    monkeypatch.setattr(runner, "_run", lambda _s, _l, c, _st, _r: ran.append(c.slug))

    waiting = stepped(picking, picking.slug)

    assert (ran, waiting.stop, waiting.outcome.exit) == ([], None, Exit.PENDING)  # no worker, and never stopped
    assert list((root / PROJECT).rglob("D-*.md")) == []
    line = status.status(waiting, Activity(host_up=True), waiting.outcome.at).line
    assert decision_publication.UNSAVED in line
    assert "held by another save" in line
    assert loop.next_step(waiting, waiting.outcome.at) is None

    woken = waiting.outcome.wake_at
    runner._step(picking.store, Lock(picking.slug), waiting, loop.next_step(waiting, woken), picking.repo)  # noqa: SLF001

    (p,) = picking.store.read(picking.slug).decisions_published
    assert (p.committed, p.published, len(tries), ran) == (True, True, 2, [picking.slug])
    assert commits(remote, rel(lasting.id)) == [APPROVED.format(1)]


def test_a_refused_conflict_flag_commit_after_the_approvals_commit_keeps_the_approval(picking, shared_repo):
    root, _ = shared_repo
    (first,) = approvable(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    picking.approved()
    reshape(picking)
    rival = Decision(id=new_id(), title="Notes live in files", statement="A note is a file.", scope=Scope.PROJECT,
                     project=PROJECT, origin=Origin.APPROVED, actor="shaper", state=State.IN_FORCE, created_at=AT,
                     links=(Link(type=LinkType.REPLACES, target=first.id),))  # fmt: skip
    assert decision_store.save(picking.shared, rival, expected_revision=None, message="decisions: rival").published
    (later,) = approvable(picking, 2, LASTING | {"answer": "Notes live in Postgres."}).brief.decisions
    hook = root / ".git" / "hooks" / "commit-msg"  # refuses only the conflict flags, after the approval's commit
    hook.parent.mkdir(exist_ok=True)
    hook.write_text('#!/bin/sh\nif grep -q "conflict on" "$1"; then echo flags refused >&2; exit 1; fi\n')
    hook.chmod(0o755)

    said = picking.approve(2)

    # Accepted policy: the approval's own commit stays; only the refused conflict-flag batch is interrupted.
    assert said.status_code == 409
    assert "flags refused" in said.json()["detail"]
    assert git(root, "log", "-1", "--format=%s") == APPROVED.format(2)
    pending = decision_batch.pending(picking.shared)
    assert pending is not None
    assert rival.id in pending.ids
    assert later.id in pending.ids
    with pytest.raises(decision_store.DecisionsUnavailable):  # the conflict still fails closed for every reader
        decision_store.load(picking.shared, PROJECT)
    a = picking.approved()
    # The refused publication is not recorded as the Change's approval, so the Change still shows v1; the commit stays.
    assert a.brief.approved_version == 1


@pytest.mark.parametrize("mutation", ["withdrawn", "title", "read-back"])
def test_external_rule_changes_do_not_rewrite_own_publication_receipts(
    picking, shared_repo, monkeypatch, mutation
):
    root, _ = shared_repo
    (first,) = approvable(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    (v1,) = picking.approved().decisions_published
    reshape(picking)
    assert approvable(picking, 2, LASTING, OWN).brief.decisions[0].id == first.id
    rule = read(root / rel(first.id))
    changes = {
        "withdrawn": {"state": State.WITHDRAWN},
        "title": {"title": "Where notes are kept"},
        "read-back": {"read_back": "pending", "read_back_why": "check it", "read_back_kind": ReadBackKind.UNCERTAIN},
    }[mutation]
    write(rule.model_copy(update=changes), root / PROJECT, rule.revision)
    changed = read(root / rel(first.id))
    assert changed.revision != rule.revision
    if mutation == "read-back":
        assert changed.rule_revision == rule.rule_revision

    assert picking.approve(2).status_code == 200

    a = picking.approved()
    (p,) = [p for p in a.decisions_published if p.id == first.id]
    assert (p.revision, p.committed) == (v1.revision, True)  # its receipt is the Change's own save, not the change
    assert read(root / rel(first.id)) == changed
    if mutation == "read-back":
        assert first.id in a.decisions_baseline.said
    else:
        assert a.decisions_baseline.revisions.get(first.id) != changed.rule_revision
    if mutation == "withdrawn":
        return
    monkeypatch.setattr(runner, "_run", lambda *_a: None)
    pickers = len(picking.pickers())
    if mutation == "title":
        picking.picks.append(pick_tools.PickResult(picked=[]))

    c = stepped(picking, picking.slug)

    assert c.outcome is None
    if mutation == "title":
        assert first.id in picking.pickers()[-1].message.split("## Decisions")[1]
        assert first.id not in c.decisions_baseline.said
        assert len(picking.pickers()) == pickers + 1
    else:
        assert len(picking.pickers()) == pickers
    assert c.decisions_baseline.revisions[first.id] == changed.rule_revision


@pytest.mark.parametrize("narrowed", [True, False], ids=["project-to-change", "change-to-project"])
def test_scope_transitions_publish_no_dangling_predecessor_link(
    picking, shared_repo, narrowed
):
    root, _ = shared_repo
    decision = LASTING if narrowed else OWN
    (first,) = approvable(picking, 1, decision).brief.decisions
    assert picking.approve(1).status_code == 200
    picking.approved()
    if not narrowed:
        assert not list(root.rglob(f"{first.id}.md"))
    reshape(picking)
    (later,) = approvable(picking, 2, decision | {"scope": "change" if narrowed else "project"}).brief.decisions
    assert (later.id != first.id, later.replaces) == (True, first.id)  # a changed scope is a successor

    assert picking.approve(2).status_code == 200

    if not narrowed:
        rule = read(root / rel(later.id))
        assert (rule.state, rule.links) == (State.IN_FORCE, ())
        assert f"It replaces {first.id}, a decision for this Change alone in an earlier version." in rule.rationale
        assert validate_repo(root) == []
        assert change_record.save(picking.store, picking.approved(), MERGED, AT + timedelta(days=1)) == ""
        (kept,) = root.rglob(f"{first.id}.md")
        assert (read(kept).scope, read(kept).state) == (Scope.CHANGE, State.WITHDRAWN)
        assert read(root / rel(later.id)) == rule
        assert validate_repo(root) == []
        return
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


def reviewed_legacy_decisions(picking, field: str, value: str, count: int) -> Change:
    """Seed an older stored draft, bypassing only today's draft-input validator."""
    drafts = [LASTING | {"question": f"Where do notes live {i}?"} for i in range(count)]
    approvable(picking, 1, *drafts)
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        c.brief.decisions[-1] = c.brief.decisions[-1].model_copy(update={field: value})
        picking.store.write(lock, c)
    return picking.change()


@pytest.mark.parametrize("case", [("question", "   ", 1), ("answer", "\t\n", 2), ("shared", "", 1)])
def test_current_id_bearing_rules_require_buildable_shared_authority(
    picking, shared_repo, monkeypatch, case
):
    """The last decision is unbuildable: alone, and after a valid one that a check of only the first would pass."""
    root, remote = shared_repo
    field, value, count = case
    if field == "shared":
        approvable(picking, 1, LASTING)
        monkeypatch.setattr(picking.store, "shared", None)
        with picking.store.lock(picking.slug) as lock:
            before = picking.store.read(picking.slug)
            why = decision_publication.approve(picking.store, lock, before, BriefApproval(at=AT, version=1))
        assert why
        assert picking.store.read(picking.slug).brief.approved_version is None
        assert picking.store.read(picking.slug).decisions_published == []
        return
    c = reviewed_legacy_decisions(picking, field, value, count)
    before = commits(remote)
    head = git(root, "rev-parse", "HEAD")

    said = picking.approve(1)

    assert said.status_code == 409
    a = picking.approved()
    assert (a.brief.approved_version, a.step.kind, a.decisions_published) == (None, StepKind.SHAPE, [])
    assert (commits(remote), git(root, "rev-parse", "HEAD")) == (before, head)
    assert not list((root / PROJECT / "decisions").glob("*.md"))
    assert c.brief.decisions[-1].id in said.json()["detail"]


def test_idless_legacy_approval_keeps_its_narrow_compatibility_path(picking, monkeypatch):
    approvable(picking, 1, LASTING)
    monkeypatch.setattr(picking.store, "shared", None)
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        c.brief.decisions[0] = c.brief.decisions[0].model_copy(update={"id": ""})
        picking.store.write(lock, c)
        assert decision_publication.approve(picking.store, lock, c, BriefApproval(at=AT, version=1)) == ""

    assert picking.store.read(picking.slug).brief.approved_version == 1
    assert picking.store.read(picking.slug).decisions_published == []


def legacy_approved(picking, version):
    """Seed an approval written by the old software, which could omit malformed authority records."""
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        c.brief.challenged = version
        approval = BriefApproval(at=AT, version=version, published=c.decisions_published)
        picking.store.write(lock, loop.fold(c, [approval], AT))


@pytest.mark.parametrize("replace", [False, True])
def test_corrected_approval_omits_only_proven_never_published_history(picking, shared_repo, replace):
    root, _ = shared_repo
    old = reviewed_legacy_decisions(picking, "answer", "   ", 1).brief.decisions[0]
    legacy_approved(picking, 1)
    assert not (root / rel(old.id)).exists()
    reshape(picking)
    drafts = [LASTING | {"question": old.question, "answer": "Use a corrected SQLite rule."}] if replace else []
    c = approvable(picking, 2, *drafts)
    if replace:
        assert c.brief.decisions[0].replaces == old.id

    assert picking.approve(2).status_code == 200

    assert not (root / rel(old.id)).exists()
    if replace:
        current = read(root / rel(c.brief.decisions[0].id))
        assert (current.state, current.links) == (State.IN_FORCE, ())
    assert validate_repo(root) == []
    assert change_record.save(picking.store, picking.approved(), MERGED, AT + timedelta(days=1)) == ""


def test_correction_preserves_the_published_predecessor_across_an_omitted_history_record(picking, shared_repo):
    root, _ = shared_repo
    (first,) = approvable(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    picking.approved()
    reshape(picking)
    assert picking.save(decisions=[LASTING | {"answer": "A different intermediate rule."}])["version"] == 2
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        omitted = c.brief.decisions[0]
        assert omitted.replaces == first.id
        c.brief.decisions[0] = omitted.model_copy(update={"answer": "   "})
        picking.store.write(lock, c)
    legacy_approved(picking, 2)
    reshape(picking)
    (current,) = approvable(picking, 3, LASTING | {"answer": "A corrected current rule."}).brief.decisions
    assert current.replaces == omitted.id

    assert picking.approve(3).status_code == 200

    assert read(root / rel(first.id)).state == State.REPLACED
    assert not (root / rel(omitted.id)).exists()
    rule = read(root / rel(current.id))
    assert [(link.type, link.target) for link in rule.links] == [(LinkType.REPLACES, first.id)]
    assert validate_repo(root) == []
    assert change_record.save(picking.store, picking.approved(), MERGED, AT + timedelta(days=1)) == ""


def test_a_published_predecessor_retires_from_authority_without_rewriting_malformed_history(picking, shared_repo):
    root, _ = shared_repo
    (first,) = approvable(picking, 1, LASTING).brief.decisions
    assert picking.approve(1).status_code == 200
    picking.approved()
    reshape(picking)
    approvable(picking, 2)
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        old = c.brief.approved[0].decisions[0]
        c.brief.approved[0].decisions[0] = old.model_copy(update={"answer": "   "})
        picking.store.write(lock, c)
    assert picking.approve(2).status_code == 200

    rule = read(root / rel(first.id))
    assert (rule.state, rule.statement) == (State.WITHDRAWN, LASTING["answer"])
    c = picking.approved()
    assert c.brief.approved[0].decisions[0].answer == "   "
    assert validate_repo(root) == []
    assert change_record.save(picking.store, c, MERGED, AT + timedelta(days=1)) == ""


@pytest.mark.parametrize("missing", ["checkout", "project", "decisions-link"])
def test_unavailable_authority_is_not_proof_that_malformed_history_was_never_published(picking, shared_repo, missing):
    root, _ = shared_repo
    reviewed_legacy_decisions(picking, "answer", "   ", 1)
    legacy_approved(picking, 1)
    reshape(picking)
    approvable(picking, 2)
    if missing == "decisions-link":
        (root / PROJECT / "decisions").symlink_to(root / "missing-decisions", target_is_directory=True)
    else:
        path = root if missing == "checkout" else root / PROJECT
        path.rename(path.with_name("temporarily-unavailable"))
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        why = decision_publication.approve(picking.store, lock, c, BriefApproval(at=AT, version=2))

    assert why
    assert picking.store.read(picking.slug).brief.approved_version == 1


def _unavailable(reason: str, note: str = "NOTE-MARK"):
    def fail(*_args, **_kwargs):
        error = decision_store.DecisionsUnavailable(reason)
        error.add_note(note)
        raise error

    return fail


@pytest.mark.parametrize("fails", ["save", "items"])
def test_a_recovery_that_fails_waits_with_its_whole_reason(picking, monkeypatch, whole_error, fails):
    approvable(picking, 1, LASTING)

    def crashed(*_args, **_kwargs):
        raise Crash

    monkeypatch.setattr(decision_store, "save_all", crashed)
    with pytest.raises(Crash):
        picking.approve(1)
    if fails == "save":
        monkeypatch.setattr(decision_store, "save_all", _unavailable(whole_error))
        why = f"DecisionsUnavailable: {whole_error}\nNOTE-MARK"
    else:
        monkeypatch.setattr(decision_publication.decision_archive, "lasting", _unavailable(whole_error))
        why = f"DecisionsUnavailable: {whole_error}\nNOTE-MARK"
    monkeypatch.setattr(runner, "_run", lambda *_a: pytest.fail("no step works before the saves"))

    waiting = stepped(picking, picking.slug)

    reason = f"{decision_publication.UNSAVED}: {why}"
    assert waiting.outcome.reason == reason
    (event,) = [e for e in picking.store.events(picking.slug) if e.get("event") == "decisions-unsaved"]
    assert event["reason"] == reason


@pytest.mark.parametrize("fails", ["save", "items"])
def test_a_day_of_the_same_failed_recovery_asks_though_its_notes_said_different_words(
    picking, monkeypatch, whole_error, fails
):
    """#971: a failed save's notes differ each time; the wait signs the error without them, so a day of it asks,
    showing the last one whole."""
    approvable(picking, 1, LASTING)

    def crashed(*_args, **_kwargs):
        raise Crash

    monkeypatch.setattr(decision_store, "save_all", crashed)
    with pytest.raises(Crash):
        picking.approve(1)
    target = (decision_store, "save_all") if fails == "save" else (decision_publication.decision_archive, "lasting")
    for at, note in ((AT, "the push was refused"), (AT + EPISODE_ASK, "the fetch was cut off")):
        monkeypatch.setattr(*target, _unavailable(whole_error, note))
        with picking.store.lock(picking.slug) as lock:
            assert decision_publication.resume(picking.store, lock, picking.store.read(picking.slug), at) is None

    c = picking.store.read(picking.slug)
    budget = c.budgets.causes[f"network:{c.step.kind}:decisions"]
    assert (budget.since, budget.attempts, c.outcome.exit) == (AT, 2, Exit.ASK)
    reason = f"{decision_publication.UNSAVED}: DecisionsUnavailable: {whole_error}\nthe fetch was cut off"
    since = f"{AT:%Y-%m-%d %H:%M}"
    assert loop.open_question(c).text == f"network keeps failing for {c.step.kind} since {since}; last error: {reason}"
