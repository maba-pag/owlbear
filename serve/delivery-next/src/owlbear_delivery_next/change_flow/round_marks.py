"""What the Change page shows of the challenge loops (TD-208, TD-217): a marker per round, its findings, what is left.

A round's marker takes its most urgent finding's kind: open (a fix agreed and not made, or a rejection the reviewer did
not accept), unverified (a fix no later round reviewed, or a rejection never judged) or settled (a verified fix, an
accepted rejection, a finding dropped or withdrawn). Only the current attempt of each loop is shown.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.round_records import BRIEF, FINAL, PLAN

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Criterion
    from owlbear_delivery_next.change_contracts.round_records import RoundFinding, RoundLoop

KINDS = ("open", "unverified", "settled")  # most urgent first
SHOWN = 3  # problems a question names before it counts the rest
SAID = {  # per finding state and kind: one and many
    ("open", "open"): ("fix agreed, not made", "fixes agreed, not made"),
    ("owner-fix", "open"): ("fix you decided on, not made", "fixes you decided on, not made"),
    ("escalated", "open"): ("rejection the reviewer did not accept", "rejections the reviewer did not accept"),
    ("left-open", "open"): ("left open, rejected and upheld", "left open, rejected and upheld"),
    ("fixed", "unverified"): ("fix reported, not re-reviewed", "fixes reported, not re-reviewed"),
    ("rejected", "unverified"): ("rejection not reviewed", "rejections not reviewed"),
    ("fixed", "settled"): ("fix verified", "fixes verified"),
    ("standing", "settled"): ("rejection the reviewer accepted", "rejections the reviewer accepted"),
    ("owner-drop", "settled"): ("dropped by you", "dropped by you"),
    ("withdrawn", "settled"): ("withdrawn by the reviewer", "withdrawn by the reviewer"),
}


def kind(lp: RoundLoop, f: RoundFinding) -> str:
    """Open, unverified or settled: a fix counts as verified once a full round ran after its repair reported it."""
    if f.state in {"open", "owner-fix", "escalated", "left-open"}:
        return "open"
    if f.state == "rejected" or (f.state == "fixed" and f.repair not in lp.reviewed):
        return "unverified"
    return "settled"


def unmet(c: Change, lp: RoundLoop) -> list[Criterion]:
    """The brief's criteria an open finding of the final loop *lp* or a task loop names (TD-341)."""
    loops = [lp, *(x for k, x in c.loops.items() if k != FINAL)]
    said = [f.text for x in loops for f in x.findings if kind(x, f) == "open"]
    return [k for k in c.brief.criteria if any(re.search(rf"(?<![\w-]){re.escape(k.id)}(?![\w-])", s) for s in said)]


def problem(text: str) -> str:
    """A finding's problem without its place and fix: findings read ``place: problem - fix: fix``."""
    said = " ".join(text.removeprefix("- ").split(" - fix:", 1)[0].split())
    return re.sub(r"^\S+:\s+(?=\S)", "", said)  # the file and line stay in the question's details


def some(items: list[str]) -> str:
    """The first few of *items* and how many more there are."""
    more = f"; and {len(items) - SHOWN} more" if len(items) > SHOWN else ""
    return "; ".join(items[:SHOWN]) + more


def risk(c: Change, lp: RoundLoop) -> str:
    """What the loop's work may still get wrong, in the reviewer's words (#1168): the problems first, never counts."""
    kinds = [(f, kind(lp, f)) for f in lp.findings]
    still = [problem(f.text) for f, k in kinds if k == "open"]
    unseen = [problem(f.text) for f, k in kinds if k == "unverified"]
    said = [f"The review says this is still wrong: {some(still)}."] if still else []
    if unseen:
        said.append(f"Reported fixed or rejected by the builder, and not reviewed again: {some(unseen)}.")
    if named := unmet(c, lp):
        said.append(f"Acceptance criteria the open findings name: {some([f'{k.id} ({k.text})' for k in named])}.")
    return " ".join(said)


def rounds(lp: RoundLoop, findings: list[RoundFinding]) -> list[dict[str, object]]:
    """One marker per round with findings: its kind and count, and every finding of it with its reasons."""
    out: list[dict[str, object]] = []
    for n in sorted({f.raised for f in findings}):
        mine = [(f, kind(lp, f)) for f in findings if f.raised == n]
        kinds = [k for _, k in mine]
        top = next(k for k in KINDS if k in kinds)
        counts: dict[tuple[str, str], int] = {}
        for f, k in mine:
            counts[f.state, k] = counts.get((f.state, k), 0) + 1
        said = "; ".join(f"{c} {SAID[key][c > 1]}" for key, c in counts.items())
        latest = " (latest)" if n == lp.round else ""
        out.append(
            {
                "round": n,
                "last": n == lp.round,
                "kind": top,
                "count": kinds.count(top),
                "said": f"Round {n}{latest}: {said}",
                "findings": [_finding(f, k) for f, k in mine],
            }
        )
    return out


def _finding(f: RoundFinding, k: str) -> dict[str, object]:
    return {
        "id": f.id,
        "text": f.text,
        "kind": k,
        "state": SAID[f.state, k][0],
        "tasks": f.tasks,
        "reason": f.reason,
        "judgement": f.judgement,
        "note": f.note,
    }


def left(c: Change) -> list[dict[str, str]]:
    """Every finding left open after approval, in the order it happened, with where it was raised and both reasons.

    The PR description and the Change page list the same entries (D-01M7866JPJ080C8545DH00WY1H).
    """
    plan = c.loops.get(PLAN)
    out = []
    for e in c.left:
        if e.loop == PLAN:
            where = "Plan challenge of an earlier plan" if plan and e.attempt != plan.attempt else "Plan challenge"
        else:
            where = "Final review" if e.loop == FINAL else f"Review of task {e.loop}"
        worker, judge = ("Planner", "Challenger") if e.loop == PLAN else ("Builder", "Reviewer")
        out.append(
            {"where": where, "id": e.id, "text": e.text, "worker": worker, "reason": e.reason, "judge": judge}
            | {"judgement": e.judgement}
        )
    return out


def shown(c: Change) -> dict[str, object]:
    """Per plan task its task review's and the final review's markers; the final review's own; what is left open."""
    final = c.loops.get(FINAL)
    plan = [t for t in c.plan.tasks if t.origin == "plan"] if c.plan else []
    tasks = {
        t.id: {
            "task": rounds(lp, lp.findings) if (lp := c.loops.get(t.id)) else [],
            "final": rounds(final, [f for f in final.findings if t.id in f.tasks]) if final else [],
        }
        for t in plan
    }
    titles = {t.id: t.title for t in c.plan.tasks} if c.plan else {}
    plan_loop, brief_loop = c.loops.get(PLAN), c.loops.get(BRIEF)
    titles |= (
        {i: f"the plan as revised after challenge round {i[1:]}" for i in plan_loop.unreviewed} if plan_loop else {}
    )
    titles |= {i: f"brief {i}, revised after its last challenge" for i in brief_loop.unreviewed} if brief_loop else {}
    loops = [lp for k, lp in c.loops.items() if k in {FINAL, PLAN, BRIEF} or k in tasks]
    unreviewed = [{"id": i, "title": titles.get(i, ""), "loop": lp.subject} for lp in loops for i in lp.unreviewed]
    standing = [
        {"loop": lp.subject} | _finding(f, kind(lp, f))
        for lp in loops
        for f in lp.findings
        if f.state in {"rejected", "standing"}
    ]
    return {
        "tasks": tasks,
        "final": rounds(final, final.findings) if final else [],
        "attempt": final.attempt if final else 0,
        "plan": rounds(plan_loop, plan_loop.findings) if plan_loop else [],  # the plan challenge's (TD-190)
        "brief": rounds(brief_loop, brief_loop.findings) if brief_loop else [],  # the brief challenge's (TD-221)
        "unreviewed": unreviewed,
        "standing": standing,
        "left": left(c),
    }
