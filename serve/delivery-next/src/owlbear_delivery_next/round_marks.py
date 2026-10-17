"""What the Change page shows of the challenge loops (TD-208, TD-217): a marker per round, its findings, what is left.

A round's marker takes its most urgent finding's kind: open (a fix agreed and not made, or a rejection the reviewer did
not accept), unverified (a fix no later round reviewed, or a rejection never judged) or settled (a verified fix, an
accepted rejection, a finding dropped or withdrawn). Only the current attempt of each loop is shown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.round_records import FINAL

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.round_records import RoundFinding, RoundLoop

KINDS = ("open", "unverified", "settled")  # most urgent first
SAID = {  # per finding state and kind: one and many
    ("open", "open"): ("fix agreed, not made", "fixes agreed, not made"),
    ("owner-fix", "open"): ("fix you decided on, not made", "fixes you decided on, not made"),
    ("escalated", "open"): ("rejection the reviewer did not accept", "rejections the reviewer did not accept"),
    ("fixed", "unverified"): ("fix reported, not re-reviewed", "fixes reported, not re-reviewed"),
    ("rejected", "unverified"): ("rejection not reviewed", "rejections not reviewed"),
    ("fixed", "settled"): ("fix verified", "fixes verified"),
    ("standing", "settled"): ("rejection the reviewer accepted", "rejections the reviewer accepted"),
    ("owner-drop", "settled"): ("dropped by you", "dropped by you"),
    ("withdrawn", "settled"): ("withdrawn by the reviewer", "withdrawn by the reviewer"),
}


def kind(lp: RoundLoop, f: RoundFinding) -> str:
    """Open, unverified or settled: a fix counts as verified once a full round ran after its repair reported it."""
    if f.state in {"open", "owner-fix", "escalated"}:
        return "open"
    if f.state == "rejected" or (f.state == "fixed" and f.repair not in lp.reviewed):
        return "unverified"
    return "settled"


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
    loops = [lp for k, lp in c.loops.items() if k == FINAL or k in tasks]
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
        "unreviewed": unreviewed,
        "standing": standing,
    }
