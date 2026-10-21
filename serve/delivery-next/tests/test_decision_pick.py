"""The decision pick at shaping (TD-459): picked once per brief version before its challenge, pinned at approval."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import Change, Exit, StepKind, Waiting
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import pick

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
DRAFT = {
    "title": "Add farewell",
    "outcome": "farewell(name) says goodbye in the app package.",
    "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
    "scope": ["packages/app"],
}
USAGE = {"credits": 6.0, "models": {"gpt-6.1-sol": {"credits": 6.0, "tokens": 900}}}


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Pages are plain HTML", "statement": "The pages are plain HTML with no build step.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.APPROVED, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT, "topic": "pages",
    }  # fmt: skip
    return Decision(**{**fields, **changes})


class Host:
    wake = SimpleNamespace(set=lambda: None)
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=AT, code=CURRENT)  # noqa: S106

    def activity(self, _slug):
        return Activity(host_up=True)


class Picking:
    """The chat's host API on a project with decisions; the picker's and the challenger's answers, in turn."""

    def __init__(self, tmp_path: Path, repo: Path, shared: DataRepo, monkeypatch) -> None:
        self.shared, self.repo = shared, repo
        self.store = Store(tmp_path / "store", shared, PROJECT)
        self.http = TestClient(api.create_app(self.store, "t", Host()), base_url="http://127.0.0.1",
                               headers={"authorization": "Bearer t"})  # fmt: skip
        self.picks: list[pick_tools.PickResult | str] = []  # a str is the ending of a failed session
        self.verdicts: list[tools.ReviewResult] = []
        self.told: list[sdk_adapter.Session] = []
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)
        monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)

    async def run(self, cfg):
        self.told.append(cfg)
        done = Termination(confirmed=True)
        if cfg.role != tools.PICKER:
            return Run(cfg.session_id, "result", self.verdicts.pop(0), termination=done)
        said = self.picks.pop(0)
        if isinstance(said, str):
            return Run(cfg.session_id, said, None, detail="the runtime did not start", termination=done)
        return Run(cfg.session_id, "result", said, usage=USAGE, termination=done)

    def pickers(self) -> list[sdk_adapter.Session]:
        return [cfg for cfg in self.told if cfg.role == tools.PICKER]

    @property
    def slug(self) -> str:
        return self.store.slugs()[0]

    def change(self) -> Change:
        return self.store.read(self.slug)

    def put(self, decision: Decision) -> Decision:
        write(decision, self.shared.root if decision.scope is Scope.GLOBAL else self.shared.root / PROJECT)
        return decision

    def save(self, **fields) -> dict:
        body = DRAFT | {"change": "c1"} | fields if self.store.slugs() else DRAFT | fields
        return self.http.post("/api/next/briefs", json=body).json()

    def ask(self, version: int, rejected: dict[str, str] | None = None, *, retry: bool = False):
        said = [{"finding": k, "reason": r} for k, r in (rejected or {}).items()]
        body = {"change": "c1", "version": version, "rejected": said, "retry_pick": retry}
        return self.http.post("/api/next/briefs/challenge", json=body)

    def step(self) -> Change:
        c = self.change()
        runner._step(self.store, Lock(self.slug), c, c.step, self.repo)  # noqa: SLF001
        return self.change()

    def approve(self, version: int, *, unreviewed: bool = False):
        body = {"version": version, "unreviewed": unreviewed}
        return self.http.post(f"/api/next/changes/{self.slug}/approve-brief", json=body)

    def approved(self) -> Change:
        return self.store.fold(Lock(self.slug), self.slug, datetime.now(UTC))[0]


@pytest.fixture
def picking(tmp_path, change_repo, shared_repo, monkeypatch) -> Picking:
    shared = DataRepo(shared_repo[0])
    shared.claim(PROJECT, "github.com/acme/shop-site")
    return Picking(tmp_path, change_repo, shared, monkeypatch)


def picked(*ids: str) -> pick_tools.PickResult:
    return pick_tools.PickResult(picked=[{"id": i, "note": "it governs the page"} for i in ids])


def verdict(*places: str) -> tools.ReviewResult:
    found = [{"place": p, "problem": "untestable", "fix": "name the output"} for p in places]
    return tools.ReviewResult(verdict="fix" if places else "pass", findings=found)


def test_the_first_challenge_request_picks_from_the_complete_list_and_approval_pins_the_pick(picking):
    rule, general = picking.put(make()), picking.put(make(scope=Scope.GLOBAL, project="", title="Ask one question"))
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    old = picking.put(make(title="Pages use React", state=State.REPLACED))
    (picking.shared.root / PROJECT / pick.LOG).write_text("- Missed page rules when a page changed: include them.\n")
    picking.save()
    assert picking.ask(1).status_code == 200
    assert picking.change().brief.picked.status == "owed"
    picking.picks.append(picked(rule.id, general.id, "D-NOTONTHELIST"))
    picking.verdicts.append(verdict())
    c = picking.step()
    first, judge = picking.told
    assert (first.role, judge.role, first.model, first.effort) == ("picker", "challenger", "gpt-6.1-sol", "medium")
    said = first.message
    assert said.startswith(pick.INSTRUCTION)
    assert said.index("Missed page rules") < said.index(f"{rule.id} | pages | {rule.statement}") < said.index("Title:")
    assert (other.id in said, general.id in said, old.id in said) == (True, True, False)  # in force: the whole list
    opts = sdk_adapter._Step(first, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert [t.name for t in opts["tools"]] == opts["custom_agents"][0]["tools"] == ["submit_result"]  # nothing else
    p = c.brief.picked
    assert (p.status, p.version, [d.id for d in p.decisions]) == ("ok", 1, [rule.id, general.id])
    assert [d.revision for d in p.decisions] == [rule.rule_revision, general.rule_revision]
    assert p.dropped == ["D-NOTONTHELIST"]
    assert "D-NOTONTHELIST" in p.reason
    assert c.spend.credits == 6.0  # the pick's session counts like any other
    shown = picking.http.get(f"/api/next/changes/{picking.slug}").json()["brief"]["picked"]
    assert (shown["status"], shown["decisions"]) == ("ok", ["Pages are plain HTML", "Ask one question"])
    assert picking.approve(1).status_code == 200
    pinned = picking.approved().brief
    assert (pinned.approved_version, [d.id for d in pinned.approved[-1].picked.decisions]) == (1, [rule.id, general.id])


def test_a_repeated_request_keeps_the_pick_and_a_new_version_picks_again(picking):
    rule = picking.put(make())
    picking.save()
    picking.ask(1)
    picking.picks.append(picked(rule.id))
    picking.verdicts.append(verdict("AC-1"))
    picking.step()
    assert picking.ask(1, {"F1": "AC-1 names the output"}).status_code == 200  # the same version again
    picking.verdicts.append(tools.ReviewResult(verdict="pass", rechecked=[{"finding": "F1", "upheld": False,
                                                                           "reason": "it does"}]))  # fmt: skip
    picking.step()
    assert len(picking.pickers()) == 1
    assert picking.save(title="Add a farewell")["version"] == 2
    assert picking.ask(2).status_code == 200
    picking.picks.append(picked())
    picking.verdicts.append(verdict())
    c = picking.step()
    assert (len(picking.pickers()), c.brief.picked.version, c.brief.picked.decisions) == (2, 2, [])


def test_a_failed_pick_blocks_approval_until_a_retry_that_uses_no_round(picking):
    rule = picking.put(make())
    picking.save()
    picking.ask(1)
    picking.picks.append("error")
    picking.verdicts.append(verdict())
    c = picking.step()
    assert (c.brief.picked.status, c.brief.challenged) == ("failed", 1)  # the challenge still ran
    assert "the runtime did not start" in c.brief.picked.reason
    refused = picking.approve(1).json()["detail"]
    assert "the picker failed" in refused
    assert "retry_pick" in refused
    assert "the picker failed" in picking.ask(1).json()["detail"]  # a challenge request does not pick again
    assert picking.ask(1, {"F1": "no"}, retry=True).status_code == 422
    rounds = c.loops[BRIEF].round
    assert picking.ask(1, retry=True).status_code == 200
    assert loop.next_step(picking.change(), AT).kind == StepKind.SHAPE  # runnable: the runner picks
    picking.picks.append(picked(rule.id))
    c = picking.step()
    assert (c.brief.picked.status, c.loops[BRIEF].round, len(picking.told)) == ("ok", rounds, 3)  # no challenger
    assert (c.outcome.exit, c.outcome.waiting, c.outcome.reason) == (Exit.PENDING, Waiting.CHAT, "approve brief v1")
    picking.put(make(title="Pages load in 1 s", statement="Every page loads in under a second."))
    assert "changed since they were picked" in picking.approve(1).json()["detail"]  # approval never picks
    assert picking.ask(1, retry=True).status_code == 200
    picking.picks.append(picked(rule.id))
    picking.step()
    assert picking.approve(1).status_code == 200


def test_an_unreviewed_last_revision_is_picked_and_pinned_without_a_challenger(picking):
    rule = picking.put(make())
    picking.save()
    with picking.store.lock(picking.slug) as lock:
        c = picking.store.read(picking.slug)
        last = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=5)
        c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=last)
        picking.store.write(lock, c)
    picking.ask(1)
    picking.picks.append(picked(rule.id))
    picking.verdicts.append(verdict("AC-1"))
    picking.step()
    assert picking.save(criteria=["farewell('Ada') returns exactly 'Bye, Ada!'"])["version"] == 2
    assert picking.ask(2).status_code == 200
    c = picking.change()
    assert (c.brief.challenged, c.loops[BRIEF].unreviewed, c.brief.picked.status) == (2, ["v2"], "owed")
    assert "picks the decisions" in picking.approve(2, unreviewed=True).json()["detail"]
    picking.picks.append(picked(rule.id))
    c = picking.step()
    assert (c.brief.picked.version, c.outcome.reason, len(picking.told)) == (2, "approve brief v2", 3)
    assert picking.approve(2, unreviewed=True).status_code == 200
    assert picking.approved().brief.approved[-1].picked.version == 2
