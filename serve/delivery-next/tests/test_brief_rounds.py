"""The shaper's brief challenge (TD-221, TD-249, TD-208): asked for in chat, judged in rounds, approved after."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.dispute_tools import ReconsiderResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Exit,
    Plan,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import brief_rounds, brief_tools, loop, plan_rounds
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import mcp_server, runner
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import briefs
from owlbear_delivery_next.state_store.store import Lock, Store

NOW = datetime(2026, 10, 18, 4, tzinfo=UTC)
K = StepKind
DRAFT = {
    "title": "Add farewell",
    "outcome": "farewell(name) says goodbye in the app package.",
    "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
    "scope": ["packages/app"],
}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    paused = staticmethod(lambda: False)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug):
        return Activity(host_up=True)


class Shaping:
    """The chat's host API, the host's runner and the challenger's verdicts, in turn."""

    def __init__(self, tmp_path: Path, repo: Path, monkeypatch) -> None:
        self.store, self.repo = Store(tmp_path / "store"), repo
        self.host = Host()
        self.http = TestClient(api.create_app(self.store, "t", self.host), base_url="http://127.0.0.1",
                               headers={"authorization": "Bearer t"})  # fmt: skip
        self.verdicts: list[tools.ReviewResult] = []
        self.told: list[object] = []
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)
        monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)

    async def run(self, cfg):
        self.told.append(cfg)
        payload = self.verdicts.pop(0)
        if isinstance(payload, Termination):  # a session whose processes are not confirmed gone
            return Run(cfg.session_id, "result", None, termination=payload)
        return Run(cfg.session_id, "result", payload, termination=Termination(confirmed=True))

    @property
    def slug(self) -> str:
        return self.store.slugs()[0]

    def change(self) -> Change:
        return self.store.read(self.slug)

    def save(self, **fields) -> dict:
        body = DRAFT | {"change": "c1"} | fields if self.store.slugs() else DRAFT | fields
        return self.http.post("/api/next/briefs", json=body).json()

    def ask_challenge(self, version: int, rejected: dict[str, str] | None = None):
        said = [{"finding": k, "reason": r} for k, r in (rejected or {}).items()]
        return self.http.post("/api/next/briefs/challenge", json={"change": "c1", "version": version, "rejected": said})

    def step(self) -> Change:
        c = self.change()
        runner._step(self.store, Lock(self.slug), c, c.step, self.repo)  # noqa: SLF001
        return self.change()

    def answer(self, option: str, text: str = "") -> Change:
        q = next(q for q in self.change().questions if q.answer is None)
        self.store.put_inbox(self.slug, AnswerItem(at=datetime.now(UTC), question=q.id, option=option, text=text))
        return self.store.fold(Lock(self.slug), self.slug, datetime.now(UTC))[0]

    def approve(self, version: int, *, unreviewed: bool = False):
        body = {"version": version, "unreviewed": unreviewed}
        return self.http.post(f"/api/next/changes/{self.slug}/approve-brief", json=body)


@pytest.fixture
def shaping(tmp_path, change_repo, monkeypatch) -> Shaping:
    return Shaping(tmp_path, change_repo, monkeypatch)


def verdict(*places: str, upheld: dict[str, bool] | None = None) -> tools.ReviewResult:
    judged = [{"finding": k, "upheld": u, "reason": "see AC-1"} for k, u in (upheld or {}).items()]
    found = [{"place": p, "problem": "untestable", "fix": "name the output"} for p in places]
    return tools.ReviewResult(verdict="fix" if places else "pass", findings=found, rechecked=judged)


def test_the_shaper_asks_rejects_and_revises_until_the_owner_may_approve_the_version(shaping):
    assert shaping.save()["version"] == 1
    assert "has not been challenged" in shaping.approve(1).json()["detail"]
    assert shaping.ask_challenge(1).status_code == 200
    assert shaping.change().step.mode == "challenge"
    assert loop.next_step(shaping.change(), NOW).kind == K.SHAPE  # runnable: the host starts the challenger
    assert shaping.ask_challenge(1).status_code == 409  # it runs already
    assert shaping.save(title="Add a farewell")["errors"] == ["change: its challenge runs; save the revision after it"]
    shaping.verdicts += [verdict("AC-1", "scope"), verdict(upheld={"F2": True})]
    c = shaping.step()
    assert ([f.id for f in c.loops[BRIEF].findings], c.outcome.waiting) == (["F1", "F2"], Waiting.CHAT)
    assert "the shaper revises brief v1 for F1, F2" in shaping.approve(1).json()["detail"]
    assert shaping.ask_challenge(1, {"F2": "no"}).status_code == 409  # F1 is taken: a revision first
    assert shaping.save(criteria=["farewell('Ada') returns exactly 'Bye, Ada!'"])["version"] == 2
    assert shaping.ask_challenge(2, {"F2": "the scope is the package"}).status_code == 200
    assert shaping.change().step.mode == "rejections"  # an early last round's rejections only (TD-218)
    c = shaping.step()
    said = shaping.told[-1].message
    assert ("Shaper's reason: the scope is the package" in said, "Judge only these rejections" in said) == (True, True)
    assert (shaping.told[-1].cap, c.outcome.exit, c.loops[BRIEF].findings[1].state) == (0, Exit.ASK, "escalated")
    assert shaping.save(title="Add a farewell").get("errors")[0].startswith("change: a finding")
    c = shaping.answer("fix", "keep the package scope narrow")
    assert (c.loops[BRIEF].findings[1].state, c.outcome.waiting) == ("owner-fix", Waiting.CHAT)
    assert shaping.ask_challenge(2, {"F2": "still no"}).status_code == 409  # the owner's is never rejected
    assert shaping.save(scope=["packages/app/farewell.ts"])["version"] == 3
    assert shaping.ask_challenge(3).status_code == 200
    c = shaping.change()
    assert (c.brief.challenged, c.loops[BRIEF].ended, c.loops[BRIEF].unreviewed) == (3, "count", ["v2", "v3"])
    assert "was not reviewed" in shaping.approve(3).json()["detail"]  # TD-255: the owner ticks that he accepts it
    assert shaping.approve(3, unreviewed=True).json() == {"accepted": "brief-approval"}
    c, step = shaping.store.fold(Lock(shaping.slug), shaping.slug, datetime.now(UTC))
    assert (c.brief.approved_version, step.kind) == (3, K.PLAN)
    plan_rounds.loop(c, RoundPolicy(), NOW)
    c = loop.apply(c, loop.StepResult(exit=Exit.DONE, plan=Plan(tasks=[Task(id="t1", title="a")])), NOW)
    assert (c.step.kind, BRIEF in c.loops) == (K.BUILD, True)  # the brief's loop stays with the Change


def test_a_save_after_the_loop_ended_needs_one_more_round_on_the_changes(shaping):
    shaping.save()
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict(), verdict()]
    assert shaping.step().brief.challenged == 1
    assert "challenged already" in shaping.ask_challenge(1).json()["detail"]
    assert shaping.save(title="Add a farewell")["version"] == 2
    assert shaping.approve(2).status_code == 409
    shaping.ask_challenge(2)
    c = shaping.step()
    assert "## Focus" in shaping.told[-1].message
    assert (c.brief.challenged, c.loops[BRIEF].round, c.loops[BRIEF].ended) == (2, 2, "clean")


def test_the_last_allowed_round_with_many_findings_asks_the_owner(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        few = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=1)
        c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=few)
        shaping.store.write(lock, c)
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1")]
    shaping.step()
    shaping.save(title="Add a farewell")
    assert shaping.ask_challenge(2).status_code == 200
    q = next(q for q in shaping.change().questions if q.answer is None)
    assert [o.id for o in q.options] == ["another", "retry"]
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        orphan = q.model_copy(update={"id": "q9", "cause": f"{brief_rounds.DISPUTE}1 F9"})
        c.questions.append(orphan)
        shaping.store.write(lock, c)
    shaping.store.put_inbox(shaping.slug, AnswerItem(at=datetime.now(UTC), question="q9", option="another"))
    c = shaping.store.fold(Lock(shaping.slug), shaping.slug, datetime.now(UTC))[0]
    assert (c.questions[-1].answer, c.loops[BRIEF].extra) == (None, 0)  # not the open question: nothing recorded
    c = shaping.answer("retry")
    assert c.questions[-1].answer.option == brief_rounds.RETIRED  # a question of the attempt that ended
    assert (c.loops[BRIEF].attempt, c.outcome.waiting, c.brief.challenged) == (2, Waiting.CHAT, None)
    assert "asked to shape the brief again after round 1" in brief_rounds.status(c)["why_again"]


def test_the_chat_tool_waits_for_the_verdict_and_returns_the_findings_by_id(shaping, monkeypatch):
    shaping.save()
    shaping.verdicts += [verdict("AC-1")]
    chat = mcp_server.Chat.__new__(mcp_server.Chat)
    chat.store = shaping.store

    def call(method, path, body=None):
        r = shaping.http.request(method, f"/api/next{path}", json=body)
        return r.status_code, r.json()

    chat.call = call
    monkeypatch.setattr(mcp_server, "POLL", 0)
    monkeypatch.setattr(mcp_server, "_pause", lambda _s: shaping.step())  # the host runs meanwhile
    out = chat.challenge_brief("c1", 1, [])
    assert (out["requested"], [f["id"] for f in out["findings"]], out["approvable"]) == (True, ["F1"], False)
    assert chat.challenge_brief("c1", 2, [])["requested"] is False  # no such version


def test_a_challenge_asked_while_delivery_is_paused_is_recorded_and_the_chat_returns_at_once(shaping, monkeypatch):
    shaping.save()
    shaping.host.paused = lambda: True
    chat = mcp_server.Chat.__new__(mcp_server.Chat)
    chat.store = shaping.store
    chat.call = lambda method, path, body=None: (
        200,
        shaping.http.request(method, f"/api/next{path}", json=body).json(),
    )
    monkeypatch.setattr(mcp_server, "_pause", lambda _s: pytest.fail("a paused challenge is not waited for"))
    assert chat.challenge_brief("c1", 1, []) == {"requested": True, "running": False, "next": mcp_server.PAUSED}
    assert shaping.change().step.mode == "challenge"  # TD-283: the request is in; the challenger starts after Resume


def test_an_upheld_rejection_whose_question_a_stop_replaced_is_asked_again(shaping):
    shaping.save()
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": True})]
    shaping.step()
    shaping.ask_challenge(1, {"F1": "no"})
    c = shaping.step()
    with shaping.store.lock(shaping.slug) as lock:
        c.outcome = None
        shaping.store.write(lock, c)
    c = shaping.step()
    assert (c.outcome.exit, len(shaping.told)) == (Exit.ASK, 2)


def test_an_old_approval_without_its_challenge_is_challenged_then_planned(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        c.brief.approved_version = 1  # the old flow approved before its challenge
        c.outcome = None
        shaping.store.write(lock, c)
    shaping.verdicts += [verdict()]
    c = shaping.step()
    assert (c.step.kind, c.brief.challenged) == (K.PLAN, 1)


def test_an_old_approval_whose_disputed_finding_the_owner_drops_goes_on_to_planning(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        c.brief.approved_version, c.outcome = 1, None
        shaping.store.write(lock, c)
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": True})]
    shaping.step()
    assert shaping.ask_challenge(1, {"F1": "it is checkable"}).status_code == 200
    shaping.step()
    c = shaping.answer("drop", "fine as is")
    assert loop.next_step(c, NOW).kind == K.SHAPE  # runnable, not waiting for an approval it has
    with shaping.store.lock(shaping.slug) as lock:  # a save before the step ran: the new version waits for its own
        kept = shaping.store.read(shaping.slug)
        shaping.store.write(lock, briefs.drafted(kept, brief_tools.BriefDraft(**DRAFT, change="c1"), kept.slug, "c1",
                                                Profile()))  # fmt: skip
    assert shaping.change().step.mode is None
    with shaping.store.lock(shaping.slug) as lock:
        shaping.store.write(lock, c)
    assert shaping.step().step.kind == K.PLAN


def test_a_clarified_reconsideration_hands_the_finding_to_the_shaper_who_may_save_again(shaping):
    shaping.save()
    shaping.ask_challenge(1)
    clarified = [{"finding": "F1", "verdict": "clarified", "text": "AC-1: name the exact text", "reason": "r"}]
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": True}), ReconsiderResult(reconsidered=clarified)]
    shaping.step()
    shaping.ask_challenge(1, {"F1": "no"})
    shaping.step()
    assert shaping.answer("reconsider", "narrow it").step.mode == "reconsider"
    c = shaping.step()
    assert (c.step.mode, c.outcome.waiting, c.loops[BRIEF].findings[0].state) == (None, Waiting.CHAT, "owner-fix")
    assert shaping.save(title="Add a farewell")["version"] == 2


def test_a_return_to_shaping_after_approval_waits_for_the_revision_and_never_plans_by_itself(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        c.brief.approved_version = c.brief.challenged = 1  # approved, then a premise or the owner's intent came back
        c.outcome = None
        shaping.store.write(lock, c)
    c = shaping.step()
    assert (c.step.kind, c.outcome.waiting, shaping.told) == (K.SHAPE, Waiting.CHAT, [])


def test_a_reconsideration_that_cannot_confirm_its_end_stops_the_change_for_the_owner(shaping):
    shaping.save()
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": True}), Termination(confirmed=False)]
    shaping.step()
    shaping.ask_challenge(1, {"F1": "no"})
    shaping.step()
    shaping.answer("reconsider", "narrow it")
    c = shaping.step()
    assert (c.outcome.exit, c.step.mode, loop.next_step(c, NOW)) == (Exit.STOP, "reconsider", None)


def test_an_unchanged_version_whose_rejections_the_check_accepted_needs_no_tick(shaping):
    shaping.save()
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": False})]
    shaping.step()
    assert shaping.ask_challenge(1, {"F1": "it is checkable"}).status_code == 200  # no revision: rejected whole
    c = shaping.step()
    assert (c.brief.challenged, c.loops[BRIEF].unreviewed) == (1, [])
    assert shaping.approve(1).json() == {"accepted": "brief-approval"}


def test_an_unchanged_version_at_the_round_limit_needs_no_tick(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        one = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=2)
        c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=one)
        shaping.store.write(lock, c)
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1")]
    shaping.step()
    assert shaping.ask_challenge(1, {"F1": "it is checkable"}).status_code == 200  # the last round: no session
    c = shaping.change()
    assert (c.brief.challenged, c.loops[BRIEF].ended, c.loops[BRIEF].unreviewed) == (1, "max", [])
    assert shaping.approve(1).json() == {"accepted": "brief-approval"}


def test_a_wait_for_a_verdict_ends_when_its_request_was_retired():
    c = Change(slug="c1", brief=Brief(version=1, requested=1), step=Step(kind=K.SHAPE, mode="challenge"))
    c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=RoundPolicy())
    assert brief_rounds.running(c, 1, 1) is True
    assert brief_rounds.running(c, 1, 2) is False  # the owner had the brief shaped again
    c.brief.requested = None
    assert brief_rounds.running(c, 1, 1) is False


def test_the_brief_challenger_never_sees_the_owners_brief_decisions():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.SHAPE))
    lp = c.loops.setdefault(BRIEF, RoundLoop(subject=BRIEF, policy=RoundPolicy()))
    lp.raise_findings(["AC-1: secret finding - fix: y"])
    f = lp.findings[0]
    f.state, f.reason = "escalated", "no"
    q = brief_rounds.question(lp, f).model_copy(update={"id": "q1"})
    q.answer = Answer(option="fix", text="do it", at=NOW)
    c.questions.append(q)
    assert "secret finding" not in step_input.brief_challenge(c, Path("/w"))
