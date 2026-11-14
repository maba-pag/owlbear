"""A builder's rejection of review findings (TD-124, TD-208): judged by the next round's reviewer, then the owner."""

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import dispute_tools, tool_schema, tools
from owlbear_delivery_next.change_contracts.models import ItemRef, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import ACCEPTED, Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.workflow_steps import review

K = StepKind


def gate(tmp_path: Path, kind: StepKind, tree: tools.Worktree, submit: tools.Spec | None = None, **bounds) -> Gate:
    cfg = sdk_adapter.Session(
        kind, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: tree, checks=("npm test",),
        submit=submit or (tools.REVIEW if kind == K.REVIEW else tools.SUBMIT), **bounds,
    )  # fmt: skip
    return Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)


def rejecting(*keys: str) -> dict:
    rejected = [{"finding": k, "reason": "a.txt:1 already says Hallo"} for k in keys]
    return {"summary": "Rejected.", "checks": [], "rejected": rejected}


def test_both_results_offer_their_dispute_fields_to_every_runtime():
    assert "rejected" in tool_schema.schema(tools.SUBMIT)["properties"]
    assert "rechecked" in tool_schema.schema(tools.REVIEW)["properties"]


def test_a_finding_is_known_by_its_place_and_problem_on_every_path():
    finding = tools.Finding(place="a.txt:1", problem="AC-1\n greets in English", fix="use Hallo")
    line = review.lines(tools.ReviewResult(verdict="fix", findings=[finding]))[0]
    assert line == "- a.txt:1: AC-1 greets in English - fix: use Hallo"  # one line, so a repair task can key it
    assert review.score([line], K.REVIEW) == review.score([line.replace("Hallo", "Servus")], K.REVIEW)


@pytest.mark.parametrize(
    ("offered", "keys", "error"),
    [
        (("F1", "F2"), ("F1", "F2"), None),  # every finding rejected: no commit, no checks
        (("F1", "F2"), ("F1",), "changes: no commit - fix and commit F2"),
        (("F1", "F2"), ("F3",), "rejected: F3 is no finding key"),
        (("F1", "F2"), ("F1", "F1", "F2"), "rejected: F1 listed twice"),
        ((), ("F1",), "rejected: this task offers no rejection"),
    ],
)
def test_a_rejection_only_result_needs_every_finding_rejected(tmp_path, offered, keys, error):
    g = gate(tmp_path, K.BUILD, tools.Worktree(head="a", base="a"), rejectable=offered)
    text, ok = g.call(tools.SUBMIT, rejecting(*keys))
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


@pytest.mark.parametrize(
    ("keys", "error"),
    [(("F1", "F2"), None), (("F1",), "rechecked: missing F2"), (("F1", "F2", "F3"), "F3 is not listed")],
)
def test_a_review_answers_each_listed_recheck_once(tmp_path, keys, error):
    g = gate(tmp_path, K.REVIEW, tools.Worktree(head="b", base="a"), rechecks=("F1", "F2"))
    rechecked = [{"finding": k, "upheld": False, "reason": "it trims"} for k in keys]
    text, ok = g.call(tools.REVIEW, {"verdict": "pass", "rechecked": rechecked})
    assert ok if error is None else (not ok and error in text)


@pytest.mark.parametrize(
    ("offered", "keys", "error"),
    [
        (("F2",), ("F1", "F2"), "rejected: F1 is the owner's decision"),
        (("F2",), ("F2",), "changes: no commit - fix and commit F1"),
        (("F2",), ("F3",), "rejected: F3 is no finding key of this task - use F2"),
        ((), ("F1",), "rejected: the owner decided every finding"),
    ],
)
def test_a_finding_the_owner_decided_is_never_rejected(tmp_path, offered, keys, error):
    g = gate(tmp_path, K.BUILD, tools.Worktree(head="a", base="a"), rejectable=offered, settled=("F1",))
    text, ok = g.call(tools.SUBMIT, rejecting(*keys))
    assert (ok, error in text, "or reject" in text) == (False, True, False)


def test_a_conversation_reply_never_skips_a_finding_the_owner_decided(tmp_path):
    item = ItemRef(id="c1", kind="comment", version="v1", task="t1")
    g = gate(tmp_path, K.BUILD, tools.Worktree(head="a", base="a"), rejectable=("F2",), settled=("F1",), item=item)
    reply = {"how": "answered", "text": "It already greets in German."}
    text, ok = g.call(tools.SUBMIT, {"summary": "R.", "checks": [], "response": reply})
    assert (ok, "changes: no commit - fix and commit F2, F1" in text) == (False, True)


@pytest.mark.parametrize(
    ("given", "cap", "error"),
    [
        ({"upheld": True}, 1, None),
        ({}, 1, "rechecked: F1 needs upheld true or false"),
        ({"upheld": False}, 0, "findings: 1 given, at most 0"),
    ],
)
def test_a_judgement_needs_a_verdict_and_new_findings_stay_within_the_cap(tmp_path, given, cap, error):
    g = gate(tmp_path, K.REVIEW, tools.Worktree(head="b", base="a"), rechecks=("F1",), cap=cap)
    found = [{"place": "a.txt:3", "problem": "p", "fix": "f"}]
    args = {"verdict": "fix", "findings": found, "rechecked": [{"finding": "F1", "reason": "r"} | given]}
    text, ok = g.call(tools.REVIEW, args)
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


@pytest.mark.parametrize(
    ("given", "error"),
    [
        ([("F1", "withdrawn", ""), ("F2", "clarified", "a.txt:2: p - fix: f")], None),
        ([("F1", "withdrawn", "")], "reconsidered: missing F2"),
        ([("F1", "withdrawn", ""), ("F2", "clarified", " ")], "reconsidered: F2 is clarified but has no text"),
    ],
)
def test_a_reconsideration_answers_each_finding_and_restates_a_clarified_one(tmp_path, given, error):
    g = gate(tmp_path, K.REVIEW, tools.Worktree(head="a", base="a"), dispute_tools.SUBMIT, rechecks=("F1", "F2"))
    verdicts = [{"finding": k, "verdict": v, "text": t, "reason": "r"} for k, v, t in given]
    text, ok = g.call(dispute_tools.SUBMIT, {"reconsidered": verdicts})
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)
