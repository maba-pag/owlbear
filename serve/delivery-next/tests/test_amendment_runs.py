"""TD-185 through the runner: a worker's brief premise runs the amendment's own sessions before its step goes on.

Each case approves a Change on a pick through the host API, puts it at its build step and runs the runner's step entry
with a fake SDK: the builder's session reports the premise, the shaper's and the challenger's sessions answer in turn.
"""

import subprocess
from datetime import UTC, datetime

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts import amend_tools, dispute_tools, pick_tools, tool_schema, tools
from owlbear_delivery_next.change_contracts.amendment_records import Amendment
from owlbear_delivery_next.change_contracts.models import Brief, Change, Criterion, Exit, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundPolicy
from owlbear_delivery_next.change_flow import amending, loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import amendments, sdk_adapter
from owlbear_delivery_next.runtimes.results import ACCEPTED, Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import amendment

K = StepKind
DONE = Termination(confirmed=True)
NOW = datetime(2026, 11, 3, 9, tzinfo=UTC)
TRIMS = "farewell('  Ada ') returns 'Bye, Ada!'"
BRANCH = "owlbear/add-farewell"


def rule() -> Decision:
    return Decision(
        id=new_id(), title="Pages are plain HTML", statement="The pages are plain HTML with no build step.",
        scope=Scope.PROJECT, project="shop-site", origin=Origin.APPROVED, actor="shaper", state=State.IN_FORCE,
        created_at=NOW, topic="pages",
    )  # fmt: skip


def premise(*items: dict) -> tools.WrongPremise:
    args = {"stage": "brief", "reason": "AC-1 is over-specific", "evidence": ["src/app.py:3"], "amendment": list(items)}
    payload, errors = tool_schema.parse(tools.WrongPremise, args)
    assert not errors
    return payload


def candidate(text: str = TRIMS, **said) -> amend_tools.CandidateResult:
    return amend_tools.CandidateResult(items=[{"field": "criterion", "key": "AC-1", "text": text, "why": "spaces"}],
                                       **said)  # fmt: skip


def verdict(v: str = "equivalent", **fields) -> amend_tools.VerdictResult:
    return amend_tools.VerdictResult(verdict=v, reasons="the same cases pass and fail", **fields)


def finding(problem: str = "it no longer says what 'Ada' alone returns") -> dict:
    return {"place": "AC-1", "problem": problem, "fix": "keep the plain case"}


class Amending:
    """A Change approved on a pick at its build step; the builder's sessions report what ``builds`` holds."""

    def __init__(self, picking, monkeypatch) -> None:
        self.p = picking
        first = picking.put(rule())
        picking.save()
        assert picking.ask(1).status_code == 200
        picking.picks.append(pick_tools.PickResult(picked=[{"id": first.id}]))
        picking.verdicts.append(tools.ReviewResult(verdict="pass"))
        picking.step()
        assert picking.approve(1).status_code == 200
        c = picking.approved()
        c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["cd . && true"])])
        c.step = Step(kind=K.BUILD, task="t1")
        c.brief.specified = []  # AC-1 is a generated criterion: Delivery may apply an equivalent rewording alone
        picking.store.write(Lock(picking.slug), c)
        self.builds: list[tools.Args] = []
        self.unconfirmed: set[str] = set()  # the roles whose next session ends with its process left going
        self.head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=picking.repo, check=True, capture_output=True,  # noqa: S607
                                   text=True).stdout.strip()  # fmt: skip
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)

    async def run(self, cfg):
        if cfg.role == tools.PICKER or cfg.kind != K.BUILD:
            if cfg.role in self.unconfirmed:
                self.unconfirmed.discard(cfg.role)
                self.p.told.append(cfg)
                said = self.p.verdicts.pop(0)
                return Run(cfg.session_id, "result", said, termination=Termination(confirmed=False))
            return await self.p.run(cfg)
        self.p.told.append(cfg)
        if not self.builds:
            return Run(cfg.session_id, "error", detail="the next build session", termination=DONE)
        ended = Termination(confirmed="build" not in self.unconfirmed)
        return Run(cfg.session_id, "premise", self.builds.pop(0), head=self.head, termination=ended)

    def step(self):
        c = self.p.change()
        runner._step(self.p.store, Lock(self.p.slug), c, c.step, self.p.repo)  # noqa: SLF001
        return self.p.change()

    def premised(self, *items: dict):
        self.builds.append(premise(*items))
        return self.step()

    def roles(self, since: int = 0) -> list[str]:
        return [cfg.role or cfg.kind.value for cfg in self.p.told[since:] if cfg.role != tools.PICKER]


AC1 = {"field": "criterion", "key": "AC-1", "text": TRIMS, "why": "spaces around a name are no part of it"}


def test_a_premise_runs_its_amendment_on_the_shaper_and_a_separate_challenger_without_a_brief_draft(
    picking, monkeypatch
):
    run = Amending(picking, monkeypatch)
    c = picking.change()
    c.amendments = [Amendment(id=f"A{i}", at=NOW, source="worker", step="build", session="s", base=1, items=[],
                              state="declined", declined="not now") for i in (1, 2, 3)]  # fmt: skip
    picking.store.write(Lock(picking.slug), c)
    before, loops, told = c.brief.model_dump(), c.loops[BRIEF].model_dump(), len(picking.told)

    c = run.premised(AC1)

    a = amending.current(c)
    assert (a.id, a.source, c.amending.phase, c.step.kind, c.step.task) == ("A4", "worker", "prepare", K.BUILD, "t1")
    assert (c.brief.model_dump(), loop.open_question(c)) == (before, None)  # a fourth proceeds; nothing applied yet
    picking.verdicts += [candidate(), verdict(qualifies=True)]
    run.step()
    c = run.step()

    assert run.roles(told) == ["build", "shaper", "challenger"]
    shaper, challenger = picking.told[-2:]
    assert shaper.session_id != challenger.session_id
    assert (shaper.resume, challenger.resume, shaper.policy.write, challenger.policy.write) == (
        False,
        False,
        False,
        False,
    )
    assert (c.brief.requested, c.loops[BRIEF].model_dump()) == (before["requested"], loops)  # no brief challenge
    (*_, a) = c.amendments
    assert (a.state, a.level, a.verdict, a.challenger, c.brief.version) == (
        "applied",
        "autonomous",
        "equivalent",
        challenger.session_id,
        2,
    )
    assert [k.text for k in c.brief.criteria] == [TRIMS]
    assert (c.amending, c.step.kind, c.step.task) == (None, K.BUILD, "t1")  # the stopped task reruns on v2


def test_each_amendment_s_sessions_hold_the_decisions_the_stopped_step_works_by(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    told = len(picking.told)
    for text in (TRIMS, f"{TRIMS} and 'Ada' alone returns 'Bye, Ada!'"):  # the second amends v2, which no pick chose
        run.premised(AC1 | {"text": text})
        picking.verdicts += [candidate(text), verdict(qualifies=True)]
        run.step()
        c = run.step()

    assert (c.brief.version, run.roles(told)) == (3, ["build", "shaper", "challenger"] * 2)
    assert all("Pages are plain HTML" in cfg.message for cfg in picking.told[told:] if cfg.role != tools.PICKER)


def test_a_pinned_brief_loop_setting_is_honoured_and_the_verdict_binds_the_revised_wording(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    c = picking.change()
    c.loops[BRIEF].policy = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=0, ask_owner_at=4)
    picking.store.write(Lock(picking.slug), c)
    told = len(picking.told)
    revised = "farewell('  Ada ') and farewell('Ada') return 'Bye, Ada!'"
    run.premised(AC1)
    picking.verdicts += [candidate(), verdict(qualifies=True, findings=[finding()]), candidate(revised),
                         verdict(qualifies=True)]  # fmt: skip

    c = [run.step() for _ in range(4)][-1]

    (*_, a) = c.amendments
    lp = c.loops[amending.key(a)]
    assert run.roles(told) == ["build", "shaper", "challenger", "shaper", "challenger"]
    assert (lp.policy.last_round_at, lp.round, lp.ended, a.unreviewed) == (0, 2, "clean", False)  # no last round at 1
    assert (a.state, a.level, a.challenger) == ("applied", "autonomous", picking.told[-1].session_id)
    assert [k.text for k in c.brief.criteria] == [revised]


@pytest.mark.parametrize("source", ["worker", "answer"])
def test_a_loop_that_ends_on_a_revision_no_round_judged_applies_only_on_his_acceptance_of_it(
    picking, monkeypatch, source
):
    run = Amending(picking, monkeypatch)
    if source == "worker":
        run.premised(AC1)
    else:  # his answer's amendment, as the answers fold starts it
        c = picking.change()
        amending.start(c, "answer", reason="he wants spaces around a name trimmed", now=NOW)
        picking.store.write(Lock(picking.slug), c)
    picking.verdicts += [candidate("farewell trims"), verdict(qualifies=True, findings=[finding()]), candidate()]

    c = [run.step() for _ in range(3)][-1]  # one finding: the default policy's last round; the revision ends it

    q, (*_, a) = loop.open_question(c), c.amendments
    assert (amending.owned(q), [o.id for o in q.options]) == (
        (a.id, "decide"),
        ["accept-unreviewed", "within", "reshape", "stop"],
    )
    assert ("no round reviewed it" in q.text, a.unreviewed, a.state, c.brief.version) == (True, True, "proposed", 1)
    url = f"/api/next/changes/{picking.slug}/answers"
    assert picking.http.post(url, json={"question": q.id, "option": "yes"}).status_code == 422  # a plain yes
    assert picking.http.post(url, json={"question": q.id, "option": "accept-unreviewed"}).status_code == 200
    c = picking.approved()
    assert (c.amendments[-1].state, c.amendments[-1].level, [k.text for k in c.brief.criteria]) == (
        "applied",
        "approved",
        [TRIMS],
    )


def test_the_last_rounds_rejection_is_rechecked_and_an_upheld_one_reaches_him(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    run.premised(AC1)
    rejected = candidate(rejected=[{"finding": "F1", "reason": "AC-2 keeps the plain case"}])
    upheld = verdict(rechecked=[{"finding": "F1", "upheld": True, "reason": "there is no AC-2"}])
    picking.verdicts += [candidate(), verdict(qualifies=True, findings=[finding()]), rejected, upheld]

    c = [run.step() for _ in range(4)][-1]

    recheck = picking.told[-1]
    assert (recheck.role, recheck.rechecks, recheck.cap) == ("challenger", ("F1",), 0)  # rejections only
    q, (*_, a) = loop.open_question(c), c.amendments
    assert (amending.owned(q), [o.id for o in q.options], c.brief.version) == (
        (a.id, "finding F1"),
        ["fix", "reconsider", "drop"],
        1,
    )
    assert "there is no AC-2" in q.text


@pytest.mark.parametrize(
    ("said", "then"),
    [
        ("withdrawn", ("withdrawn", None, 2)),
        ("clarified", ("owner-fix", "revise", 1)),
        ("unsure", ("escalated", "ask", 1)),
    ],
)
def test_an_upheld_finding_he_sends_back_with_a_note_is_reconsidered_once(picking, monkeypatch, said, then):
    run = Amending(picking, monkeypatch)
    run.premised(AC1)
    rejected = candidate(rejected=[{"finding": "F1", "reason": "AC-2 keeps the plain case"}])
    upheld = verdict(rechecked=[{"finding": "F1", "upheld": True, "reason": "there is no AC-2"}])
    picking.verdicts += [candidate(), verdict(qualifies=True, findings=[finding()]), rejected, upheld]
    for _ in range(4):
        run.step()
    q, url = loop.open_question(picking.change()), f"/api/next/changes/{picking.slug}/answers"
    assert picking.http.post(url, json={"question": q.id, "option": "reconsider"}).status_code == 422  # no note
    note = {"question": q.id, "option": "reconsider", "text": "AC-1 itself keeps 'Ada' alone"}
    assert picking.http.post(url, json=note).status_code == 200
    reconsidered = {"finding": "F1", "verdict": said, "reason": "AC-1 keeps it", "text": "only the plain case"}
    picking.verdicts += [dispute_tools.ReconsiderResult(reconsidered=[reconsidered])]

    assert picking.approved().amending.phase == "reconsider"  # the answers fold

    c = run.step()

    told, f = picking.told[-1], c.loops[amending.key(amending.current(c) or c.amendments[-1])].findings[0]
    assert (told.role, told.rechecks, told.cap) == ("challenger", ("F1",), 0)
    assert "AC-1 itself keeps 'Ada' alone" in told.message
    assert (f.state, c.amending and c.amending.phase, c.brief.version) == then
    q = loop.open_question(c)
    assert ([o.id for o in q.options] if q else None) == (["fix", "drop"] if said == "unsure" else None)  # asked once
    assert q is None or ("AC-1 itself keeps 'Ada' alone" in q.text and "only the plain case" not in q.text)


@pytest.mark.parametrize(("role", "phase"), [("shaper", "prepare"), ("challenger", "challenge")])
def test_a_session_left_going_leaves_its_phase_without_a_result(picking, monkeypatch, role, phase):
    run = Amending(picking, monkeypatch)
    run.premised(AC1)
    if role == "challenger":
        picking.verdicts.append(candidate())
        run.step()
    run.unconfirmed.add(role)
    picking.verdicts.append(verdict(qualifies=True) if role == "challenger" else candidate("never prepared"))
    items = [i.model_dump() for i in amending.current(picking.change()).items]

    c = run.step()

    a = amending.current(c)
    assert (c.amending.phase, a.verdict, a.challenger, [i.model_dump() for i in a.items]) == (phase, "", "", items)
    assert (c.outcome.exit in {Exit.STOP, Exit.RETRY}, c.brief.version) == (True, 1)


class GitHub:
    """The PR as GitHub reports it at the merge step."""

    def __init__(self, *, merged: bool) -> None:
        self.merged = merged

    def read_pull_request(self, _repo, number):
        return PullRequest(
            repository="acme/shop-site", number=number, node_id="n", url="https://x/pull/7",
            head_branch=BRANCH, head_sha="a" * 40, base_branch="main", draft=False,
            state="closed" if self.merged else "open", merged=self.merged,
            merge_commit_sha="b" * 40 if self.merged else None,
        )  # fmt: skip


@pytest.mark.parametrize(("merged", "killed"), [(True, False), (False, False), (True, True)])
def test_a_submitted_merge_is_observed_before_the_amendment_goes_on(picking, monkeypatch, merged, killed):
    run = Amending(picking, monkeypatch)
    c = picking.change()
    amending.start(c, "answer", reason="he wants spaces around a name trimmed", now=NOW)
    c.step, c.names.pr, c.names.target = Step(kind=K.MERGE), 7, "main"
    c.names.branch = BRANCH
    picking.store.write(Lock(picking.slug), c)
    monkeypatch.setattr(amendment.profile, "provider", lambda _prof, _repo, _writer: GitHub(merged=merged))
    repo = {profile.REPO: ProfileEntry(state="known", value="acme/shop-site")}
    monkeypatch.setattr(picking.store, "read_profile", lambda: Profile(version=1, entries=repo))
    told = len(picking.told)
    picking.verdicts.append(candidate())

    c = run.step()

    if not merged:  # the amendment goes on on this Change
        assert (run.roles(told), c.amending.phase, c.step.kind) == (["shaper"], "challenge", K.MERGE)
        return
    assert (run.roles(told), c.step.kind, c.amending is not None) == ([], K.CLEANUP, True)  # the merge ends first
    if killed:  # the runner dies once the follow-up exists: the record says so, and no rerun makes a second one
        write = picking.store.write

        def dies(lock, change):
            if any(x.state == "moved" for x in change.amendments):
                killed = "killed"
                raise RuntimeError(killed)
            write(lock, change)

        monkeypatch.setattr(picking.store, "write", dies)
        with pytest.raises(RuntimeError, match="killed"):
            run.step()
        monkeypatch.setattr(picking.store, "write", write)
    c = picking.change() if killed else run.step()
    (a,) = c.amendments
    assert (a.state, c.amending, c.brief.version) == ("moved", None, 1)  # this Change finishes unchanged
    (new,) = [picking.store.read(s) for s in picking.store.slugs() if s != picking.slug]
    assert (a.moved_to, new.handle, new.step.kind, new.amendments[0].state) == (
        new.handle,
        new.handle,
        K.SHAPE,
        "recorded",
    )
    assert "merged before its amendment A1 ended" in new.intent.words


def test_an_unset_challenger_asks_for_its_settings_and_keeps_the_amendment_where_it_was(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    run.premised(AC1)
    picking.verdicts.append(candidate())
    run.step()
    base = config.BASE
    monkeypatch.setattr(config, "BASE", base.model_copy(
        update={"agents": {r: a for r, a in base.agents.items() if r != "challenger"}}))  # fmt: skip
    told = len(picking.told)

    c = run.step()

    q = loop.open_question(c)
    assert (run.roles(told), c.amending.phase, amending.current(c).verdict) == ([], "challenge", "")
    assert "agents.challenger." in q.text


@pytest.mark.parametrize(
    ("stage", "extra", "error"),
    [
        ("brief", (), ""),
        ("plan", (), "amendment: only with stage brief"),
        ("brief", (AC1,), "amendment: criterion:AC-1 listed twice"),
        ("brief", ({"field": "criterion", "key": "AC-9", "text": "x", "why": "y"},), "criterion:AC-9 is not in"),
        ("brief", ({"field": "ui", "text": "False", "why": "no page"},), ""),
        ("brief", ({"field": "ui", "text": "no page", "why": "y"},), "ui takes text true or false"),
    ],
)
def test_a_premise_may_name_any_amendable_item_the_owners_own_included(tmp_path, stage, extra, error):
    brief = Brief(version=1, criteria=[Criterion(id="AC-1", text="farewell('Ada') returns 'Bye, Ada!'")],
                  scope=["packages/app"], specified=["AC-1"])  # fmt: skip
    c = Change(slug="c1", brief=brief)
    cfg = sdk_adapter.Session(
        K.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: None, checks=(),
        amendable=amendments.amendable(c),
    )  # fmt: skip
    scope = c.brief.scope[0]
    args = premise(AC1, {"field": "scope", "key": scope, "text": f"{scope} and packages/web", "why": "web shows it"},
                   {"field": "visual", "text": "the farewell page shows Bye", "why": "no state shows it"},
                   *extra).model_dump() | {"stage": stage}  # fmt: skip

    text, ok = Gate(cfg, Run("s1"), lambda **_e: None, lambda: None).call(tools.PREMISE, args)

    assert (ok, text) == (True, ACCEPTED) if not error else (not ok and error in text)


def test_a_premise_from_a_session_left_going_starts_no_amendment(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    run.unconfirmed.add("build")

    c = run.premised(AC1)

    assert (c.amendments, c.amending, c.brief.version) == ([], None, 1)


def test_a_challengers_run_is_kept_when_its_settlement_fails_and_is_never_paid_again(picking, monkeypatch):
    run = Amending(picking, monkeypatch)
    run.premised(AC1)
    picking.verdicts.append(candidate())
    run.step()
    picking.verdicts += [verdict(qualifies=True), verdict(qualifies=True)]
    write, told = picking.store.write, len(picking.told)

    def fails(lock, change):
        if any(a.state == "applied" for a in change.amendments):
            raise OSError(28, "the settling write fails")
        write(lock, change)

    monkeypatch.setattr(picking.store, "write", fails)
    with pytest.raises(OSError, match="settling write"):
        run.step()
    monkeypatch.setattr(picking.store, "write", write)
    kept = picking.change().pending_child
    c = run.step()

    assert (kept.label, kept.parent, kept.run is not None) == (amend_tools.CHALLENGE, "A1:challenge:0", True)
    assert (run.roles(told), len(picking.verdicts)) == (["challenger"], 1)  # the second verdict is never asked for
    assert (c.amendments[-1].state, c.pending_child, c.brief.version) == ("applied", None, 2)
    steps = [e for e in picking.store.events(picking.slug) if e.get("kind") == amend_tools.CHALLENGE]
    assert [e.get("event") for e in steps] == ["step"]  # its usage counts once, with its settlement
