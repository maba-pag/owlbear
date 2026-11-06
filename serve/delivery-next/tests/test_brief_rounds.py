"""The shaper's brief challenge (TD-221, TD-249, TD-208): asked for in chat, judged in rounds, approved after."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.dispute_tools import ReconsiderResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Exit,
    Outcome,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RECHECK, RoundLoop, RoundPolicy, Verdict
from owlbear_delivery_next.change_flow import brief_rounds, brief_starts, brief_tools, loop, plan_rounds, status
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import chat_client, runner
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
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
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


def action(c: Change) -> str | None:
    """The next action the Change's row shows."""
    return status.status(c, Activity(host_up=True), NOW).action


def test_the_shaper_asks_rejects_and_revises_until_the_owner_may_approve_the_version(shaping):
    assert shaping.save()["version"] == 1
    assert action(shaping.change()) == status.CONTINUE  # D-01M6JY6QW936SGFAJ6W3DV48KA: the chat asks for the challenge
    assert "has not been challenged" in shaping.approve(1).json()["detail"]
    assert shaping.ask_challenge(1).status_code == 200
    assert shaping.change().step.mode == "challenge"
    assert loop.next_step(shaping.change(), NOW).kind == K.SHAPE  # runnable: the host starts the challenger
    assert shaping.ask_challenge(1).status_code == 409  # it runs already
    assert shaping.save(title="Add a farewell")["errors"] == ["change: its challenge runs; save the revision after it"]
    shaping.verdicts += [verdict("AC-1", "scope"), verdict(upheld={"F2": True})]
    c = shaping.step()
    assert ([f.id for f in c.loops[BRIEF].findings], c.outcome.waiting) == (["F1", "F2"], Waiting.CHAT)
    assert c.loops[BRIEF].verdicts == [Verdict(round=1, version=1)]
    assert "the shaper revises brief v1 for F1, F2" in shaping.approve(1).json()["detail"]
    assert action(c) == status.CONTINUE
    assert shaping.ask_challenge(1, {"F2": "no"}).status_code == 409  # F1 is taken: a revision first
    assert shaping.save(criteria=["farewell('Ada') returns exactly 'Bye, Ada!'"])["version"] == 2
    assert shaping.ask_challenge(2, {"F2": "the scope is the package"}).status_code == 200
    assert shaping.change().step.mode == "rejections"  # a last round's rejections only (TD-330)
    c = shaping.step()
    said = shaping.told[-1].message
    assert ("Shaper's reason: the scope is the package" in said, "Judge only these rejections" in said) == (True, True)
    assert (shaping.told[-1].cap, c.outcome.exit, c.loops[BRIEF].findings[1].state) == (0, Exit.ASK, "escalated")
    checked = Verdict(round=1, version=2, recheck=True, upheld=1, repair=True)
    assert c.loops[BRIEF].verdicts[1:] == [checked]  # outside the count
    assert shaping.save(title="Add a farewell").get("errors")[0].startswith("change: a finding")
    c = shaping.answer("fix", "keep the package scope narrow")
    assert (c.loops[BRIEF].findings[1].state, c.outcome.waiting) == ("owner-fix", Waiting.CHAT)
    assert shaping.ask_challenge(2, {"F2": "still no"}).status_code == 409  # the owner's is never rejected
    assert shaping.save(scope=["packages/app/farewell.ts"])["version"] == 3
    assert shaping.ask_challenge(3).status_code == 200
    c = shaping.change()
    assert (c.brief.challenged, c.loops[BRIEF].ended, c.loops[BRIEF].unreviewed) == (3, "count", ["v2", "v3"])
    assert action(c) == status.APPROVE  # only the wait to approve a challenged version is the owner's
    assert [v.version for v in c.loops[BRIEF].verdicts] == [1, 2]  # no challenger read v3
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
    for intent in ("pause", "resume"):  # a paused Change's round could not run, so its Approve waits for Resume
        if intent == "resume":
            assert shaping.approve(2).json()["detail"] == "this Change is paused: resume it to approve"
        shaping.store.put_inbox(shaping.slug, IntentItem(at=datetime.now(UTC), intent=intent))
        shaping.store.fold(Lock(shaping.slug), shaping.slug, datetime.now(UTC))
    assert shaping.approve(2).json() == {"accepted": "brief-challenge"}  # the owner's Approve starts the round (#986)
    c = shaping.step()
    assert "## Focus" in shaping.told[-1].message
    assert (c.brief.challenged, c.loops[BRIEF].round, c.loops[BRIEF].ended) == (2, 2, "clean")
    assert (c.brief.approve_if_clean, c.brief.approved_version) == (2, None)  # the host approves it on its next pass
    assert c.loops[BRIEF].verdicts == [Verdict(round=1, version=1), Verdict(round=2, version=2)]


def test_a_version_saved_after_the_loop_ended_waits_for_the_challenge_delivery_starts(shaping):
    shaping.save()
    assert not brief_starts.waiting(shaping.change())  # a first draft: no loop ended yet, the shaper asks
    shaping.ask_challenge(1)
    assert not brief_starts.waiting(shaping.change())  # its challenge runs
    shaping.verdicts += [verdict("AC-1")]
    shaping.step()
    shaping.save(title="Add a farewell")
    assert not brief_starts.waiting(shaping.change())  # the loop goes on: the shaper revises for F1
    shaping.ask_challenge(2)
    shaping.verdicts += [verdict()]
    assert shaping.step().brief.challenged == 2
    assert not brief_starts.waiting(shaping.change())  # the loop ended on this version: approvable
    shaping.save(title="Add a farewell, kindly")
    assert brief_starts.waiting(shaping.change())


def test_the_owners_approval_holds_only_through_a_clean_verdict_on_its_version(shaping):
    def approves(version: int) -> None:  # what the owner's Approve records before it asks for the round (#986)
        with shaping.store.lock(shaping.slug) as lock:
            c = shaping.store.read(shaping.slug)
            c.brief.approve_if_clean = version
            shaping.store.write(lock, c)

    shaping.save()
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict()]
    shaping.step()
    shaping.save(title="Add a farewell")
    approves(2)
    shaping.ask_challenge(2)
    shaping.verdicts += [verdict()]
    c = shaping.step()
    assert (c.brief.approve_if_clean, brief_starts.approving(c)) == (2, True)
    shaping.save(title="Add a farewell, kindly")
    assert not brief_starts.approving(shaping.change())  # a later save leaves it on its own version
    approves(3)
    shaping.ask_challenge(3)
    shaping.verdicts += [verdict("AC-1")]
    c = shaping.step()
    assert (c.brief.approve_if_clean, brief_starts.approving(c)) == (None, False)  # findings: the shaper revises


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
    assert (c.loops[BRIEF].attempt, c.outcome.waiting, c.brief.challenged, action(c)) == (
        2, Waiting.CHAT, None, status.CONTINUE
    )  # fmt: skip
    assert "asked to shape the brief again after round 1" in brief_rounds.status(c)["why_again"]


def test_the_chat_tool_waits_for_the_verdict_and_returns_the_findings_by_id(shaping, monkeypatch, chat_replied):
    shaping.save()
    shaping.host.paused = lambda: True  # TD-287: the challenge the owner's chat asks for runs while paused
    shaping.verdicts += [verdict("AC-1")]
    chat, _ = chat_of(shaping, chat_replied)
    monkeypatch.setattr(chat_client, "POLL", 0)
    monkeypatch.setattr(chat_client, "_pause", lambda _s: shaping.step())  # the host runs meanwhile
    out = chat.challenge_brief("c1", 1, [])
    assert (out["requested"], [f["id"] for f in out["findings"]], out["approvable"]) == (True, ["F1"], False)
    assert ("running" in out, "next" in out) == (False, True)  # the verdict as the host read it, with its guidance
    assert chat.challenge_brief("c1", 2, [])["requested"] is False  # no such version


def test_a_challenge_asked_before_a_stop_when_idle_is_recorded_and_the_chat_returns_at_once(shaping, monkeypatch):
    shaping.save()
    shaping.host.draining = lambda: True
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = Path(), shaping.store.root
    chat.call = lambda method, path, body=None: (
        200,
        shaping.http.request(method, f"/api/next{path}", json=body).json(),
    )
    monkeypatch.setattr(chat_client, "_pause", lambda _s: pytest.fail("a paused challenge is not waited for"))
    assert chat.challenge_brief("c1", 1, []) == {"requested": True, "running": False, "next": chat_client.PAUSED}
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
    assert action(c) == status.CONTINUE  # the approved version is challenged, but approved already


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


def test_an_unchanged_version_at_the_round_limit_needs_no_tick(shaping):
    shaping.save()
    with shaping.store.lock(shaping.slug) as lock:
        c = shaping.store.read(shaping.slug)
        one = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=2)
        c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=one)
        shaping.store.write(lock, c)
    shaping.ask_challenge(1)
    shaping.verdicts += [verdict("AC-1"), verdict(upheld={"F1": False})]
    shaping.step()
    assert shaping.ask_challenge(1, {"F1": "it is checkable"}).status_code == 200
    assert shaping.change().step.mode == RECHECK  # TD-330: the last round's rejection is judged, outside the count
    shaping.step()
    c = shaping.change()
    assert (c.brief.challenged, c.loops[BRIEF].round, c.loops[BRIEF].ended, c.loops[BRIEF].unreviewed) == (
        1, 1, "clean", []
    )  # fmt: skip
    assert shaping.approve(1).json() == {"accepted": "brief-approval"}


def _shaped_away(c: Change) -> None:
    c.step = Step(kind=K.PLAN)


def _reviewed(c: Change) -> None:
    c.loops[BRIEF].unreviewed = []


def _running(c: Change) -> None:
    c.step = Step(kind=K.SHAPE, mode=brief_rounds.CHALLENGE)


def _owner_asked(c: Change) -> None:
    q = Question(id="q1", step=K.SHAPE, text="?", options=brief_rounds.OPTIONS, cause=f"{brief_rounds.DISPUTE}1 F1")
    c.questions.append(q)
    c.outcome = Outcome(exit=Exit.ASK, question="q1", at=NOW)


def _pick_failed(c: Change) -> None:
    c.brief.picked = Pick(version=2, status="failed", reason="the runtime did not start")


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (_shaped_away, "the Change is not being shaped"),
        (_reviewed, "a challenge has read brief v2's last revision"),
        (_running, "its challenge runs or waits for your decision"),
        (_owner_asked, "its challenge runs or waits for your decision"),
        (_pick_failed, "picking brief v2's decisions failed; pick them again first"),  # as the chat's request is
    ],
)
def test_one_more_challenge_is_refused_unless_the_version_waits_unreviewed(change, said):
    c = Change(slug="c1", brief=Brief(version=2, requested=2, challenged=2), step=Step(kind=K.SHAPE))
    c.loops[BRIEF] = RoundLoop(
        subject=BRIEF, policy=RoundPolicy(max_rounds=1), round=1, head="1", ended="count", unreviewed=["v2"]
    )
    change(c)
    before = c.model_dump()
    assert brief_rounds.again(c, 2) == said
    assert c.model_dump() == before


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


def chat_of(shaping, chat_replied, after=None) -> tuple[chat_client.Chat, list[tuple[str, str]]]:
    """A chat whose host is *shaping*'s API, checked for what a chat reads of it; and each request it sends.

    *after* runs once, right after the host answered the chat's request for a challenge.
    """
    chat, sent = chat_client.Chat(Path(), shaping.store.root), []
    hooks = [after] if after else []

    def call(method, path, body=None):
        sent.append((method, path))
        r = shaping.http.request(method, f"/api/next{path}", json=body)
        if r.status_code == 200:
            chat_replied(method, path, r.json())
        if path == "/briefs/challenge" and hooks:
            hooks.pop()()
        return r.status_code, r.json()

    chat.call = call
    return chat, sent


@pytest.mark.parametrize("landed_first", [True, False])
def test_the_wait_for_a_challenge_asked_for_earlier_returns_its_findings_and_asks_for_nothing(
    shaping, monkeypatch, chat_replied, landed_first
):
    shaping.save()
    shaping.verdicts += [verdict("AC-1")]
    chat, sent = chat_of(shaping, chat_replied)
    assert shaping.ask_challenge(1).status_code == 200  # what challenge_brief sent, when its wait was cut short
    if landed_first:
        shaping.step()
    monkeypatch.setattr(chat_client, "_pause", lambda _s: shaping.step())  # the host runs meanwhile
    out = chat.await_challenge("c1", 1)
    assert (out["running"], out["version"], [f["id"] for f in out["findings"]]) == (False, 1, ["F1"])
    assert {method for method, _path in sent} == {"GET"}
    challenged = shaping.change().brief.challenged  # a verdict with findings does not end the loop
    assert (shaping.change().loops[BRIEF].round, challenged) == (1, None)


def owner_does(shaping, intent: str) -> None:
    """The owner pauses, resumes or abandons the Change on the Changes page, and Delivery folds it in."""
    assert shaping.http.post(f"/api/next/changes/{shaping.slug}/intent", json={"intent": intent}).status_code == 200
    shaping.store.fold(Lock(shaping.slug), shaping.slug, datetime.now(UTC))


def test_the_wait_says_it_is_no_longer_shaped_or_that_the_owner_must_resume_instead_of_running_on(
    shaping, monkeypatch, chat_replied
):
    shaping.save()
    shaping.ask_challenge(1)
    chat, _ = chat_of(shaping, chat_replied)
    monkeypatch.setattr(chat_client, "WAIT", 0)  # the deadline is the first read
    assert chat.await_challenge("c1", 1)["running"] is True
    owner_does(shaping, "pause")
    paused = chat.await_challenge("c1", 1)
    assert (paused["running"], paused["owner_action"]) == (False, "Resume")
    owner_does(shaping, "resume")
    owner_does(shaping, "abandon")
    shaping.step()
    gone = chat.await_challenge("c1", 1)
    assert (gone["running"], gone["next"]) == (False, "the Change is no longer being shaped")
    assert "Abandoned" in gone["line"]


@pytest.mark.parametrize("tool", ["challenge_brief", "await_challenge"])
def test_an_abandoned_recheck_of_the_same_draft_is_told_as_no_longer_shaped_not_as_the_previous_findings(
    shaping, monkeypatch, chat_replied, tool
):
    shaping.save()
    shaping.verdicts += [verdict("AC-1")]
    shaping.ask_challenge(1)
    shaping.step()  # round 1 found F1

    def abandon():
        owner_does(shaping, "abandon")
        shaping.step()

    monkeypatch.setattr(chat_client, "WAIT", 0)
    if tool == "challenge_brief":  # the shaper rejects F1 through the tool: a recheck runs, then is abandoned
        chat, _ = chat_of(shaping, chat_replied, after=abandon)
        gone = chat.challenge_brief("c1", 1, [{"finding": "F1", "reason": "see AC-1"}])
    else:
        assert shaping.ask_challenge(1, {"F1": "see AC-1"}).status_code == 200
        chat, _ = chat_of(shaping, chat_replied)
        assert chat.await_challenge("c1", 1)["running"] is True
        abandon()
        gone = chat.await_challenge("c1", 1)
    attempt = shaping.change().loops[BRIEF].attempt
    stale = shaping.http.get(f"/api/next/chat/challenge/{shaping.slug}?version=1&attempt={attempt}").json()
    assert (stale["running"], [f["id"] for f in stale["findings"]]) == (False, ["F1"])  # the host's read of it
    line = shaping.http.get("/api/next/changes").json()[0]["line"]
    told = {"running": False, "line": line, "next": "the Change is no longer being shaped"}
    assert gone == told | ({"requested": True} if tool == "challenge_brief" else {})


@pytest.mark.parametrize("ending", ["abandoned", "stopped", "paused"])
def test_a_challenge_asked_for_by_the_tool_ends_with_who_must_act_when_the_change_is_abandoned_stopped_or_paused(
    shaping, monkeypatch, chat_replied, ending
):
    shaping.save()
    if ending == "stopped":
        shaping.verdicts += [Termination(confirmed=False)]  # the challenger's end is not confirmed
    acts = {
        "abandoned": lambda: (owner_does(shaping, "abandon"), shaping.step()),
        "stopped": shaping.step,
        "paused": lambda: owner_does(shaping, "pause"),
    }
    chat, _ = chat_of(shaping, chat_replied, after=acts[ending])
    monkeypatch.setattr(chat_client, "WAIT", 0)  # the deadline is the first read
    out = chat.challenge_brief("c1", 1, [])
    row = shaping.http.get("/api/next/changes").json()[0]
    if ending == "abandoned":
        told = {"next": "the Change is no longer being shaped"}
    else:
        assert (row["actor"], row["action"] is not None) == ("you", True)
        told = {"owner_action": "Resume" if ending == "paused" else row["action"]}
    assert out == {"requested": True, "running": False, "line": row["line"]} | told
