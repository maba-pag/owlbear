"""The decision pick at shaping (TD-459): picked once per brief version before its challenge, pinned at approval."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import Exit, StepKind, Waiting
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.workflow_steps import pick

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Pages are plain HTML", "statement": "The pages are plain HTML with no build step.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.APPROVED, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT, "topic": "pages",
    }  # fmt: skip
    return Decision(**{**fields, **changes})


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


def test_approval_checks_the_pick_and_pins_the_baseline_from_one_read(picking, monkeypatch):
    rule = picking.put(make())
    picking.save()
    picking.ask(1)
    picking.picks.append(picked(rule.id))
    picking.verdicts.append(verdict())
    picking.step()
    real, reads = decision_store.load, []

    def load(shared, project):
        reads.append(project)
        view = real(shared, project)
        if len(reads) == 1:  # the rule changes right after the approval read the list
            changed = rule.model_copy(update={"title": "Pages are plain HTML and CSS"})
            write(changed, picking.shared.root / PROJECT, rule.revision)
        return view

    monkeypatch.setattr(decision_store, "load", load)
    assert picking.approve(1).status_code == 200
    assert picking.approved().decisions_baseline.revisions[rule.id] == rule.rule_revision  # the gate sees the change
    assert len(reads) == 1


def test_a_pick_retried_while_the_shaper_revises_runs_and_leaves_that_wait(picking):
    rule = picking.put(make())
    picking.save()
    picking.ask(1)
    picking.picks.append("error")
    picking.verdicts.append(verdict("AC-1"))
    c = picking.step()
    waited = c.outcome
    assert (c.brief.picked.status, waited.waiting) == ("failed", Waiting.CHAT)
    assert waited.reason == "the shaper revises brief v1 for F1"
    assert picking.ask(1, retry=True).status_code == 200
    c = picking.change()
    assert (c.outcome, loop.next_step(c, AT).kind) == (waited, StepKind.SHAPE)  # the runner picks during the wait
    paused = c.model_copy(deep=True)
    paused.intent.paused_at = AT
    asked = c.model_copy(update={"outcome": waited.model_copy(update={"exit": Exit.ASK})})
    assert (loop.next_step(paused, AT), loop.next_step(asked, AT)) == (None, None)
    picking.picks.append(picked(rule.id))
    c = picking.step()
    assert (c.brief.picked.status, len(picking.told), c.outcome) == ("ok", 3, waited)  # no challenger; the same wait
    assert loop.next_step(c, AT) is None


class Killed(BaseException):
    """The runner is killed in the middle of a session: nothing after it runs."""


def test_an_interrupted_pick_resumes_its_recorded_session_so_its_spend_counts(picking, monkeypatch):
    rule = picking.put(make())
    picking.save()
    picking.ask(1)
    started = []

    async def killed(cfg):
        started.append(cfg)
        raise Killed

    monkeypatch.setattr(sdk_adapter, "run", killed)
    with pytest.raises(Killed):
        picking.step()
    first = started[0]
    assert (first.resume, picking.change().brief.picked.status) == (False, "owed")
    assert picking.change().brief.picked.session == first.session_id  # recorded before the runtime started
    monkeypatch.setattr(sdk_adapter, "run", picking.run)
    picking.picks.append(picked(rule.id))  # its runtime reports the session's whole usage, before the kill too
    picking.verdicts.append(verdict())
    c = picking.step()
    again = picking.pickers()[0]
    assert (again.session_id, again.resume, again.fresh) == (first.session_id, True, first.message)
    assert (c.brief.picked.status, c.spend.last[first.session_id].credits) == ("ok", 6.0)


def test_a_correction_log_that_is_not_utf8_fails_the_pick_with_its_reason(picking):
    picking.put(make())
    (picking.shared.root / pick.LOG).write_bytes(b"- Missed \xff\xfe rules\n")
    picking.save()
    picking.ask(1)
    picking.verdicts.append(verdict())
    c = picking.step()
    assert (c.brief.picked.status, picking.pickers()) == ("failed", [])
    assert "utf-8" in c.brief.picked.reason
    assert "the picker failed" in picking.approve(1).json()["detail"]


def test_a_pick_has_no_size_limit_but_each_id_is_still_checked():
    many = [{"id": f"D-{n:026d}"} for n in range(1_500)]  # the list it picks from has no size limit (TD-456)
    assert len(pick_tools.PickResult.model_validate({"picked": many}).picked) == 1_500
    assert "maxItems" not in pick_tools.PickResult.model_json_schema()["properties"]["picked"]
    with pytest.raises(ValueError, match="at most 40 characters"):
        pick_tools.PickResult.model_validate({"picked": [{"id": "D-" + "0" * 40}]})
