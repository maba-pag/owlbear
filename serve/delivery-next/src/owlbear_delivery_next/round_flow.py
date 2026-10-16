"""After a looped repair build (TD-208, TD-218): the next round, a rejections-only check, the owner or the end."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.models import ErrorKind, Option, Question, StepKind
from owlbear_delivery_next.moves import ask, go, open_task, resolved, subject_of
from owlbear_delivery_next.round_records import FINAL, RECHECK

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.models import Change, Task
    from owlbear_delivery_next.round_records import RoundFinding, RoundLoop

PREFIX = cause_key(ErrorKind.REVIEW, StepKind.REVIEW, "round ")
RETRY = "rebuild"  # a build step's mode while its rejected attempt is undone before a fresh build (TD-210)
OPTIONS = [
    Option(id="another", label="Another round", next="another"),
    Option(id="retry", label="Reject the work and retry it", next=RETRY),
]
HOW = {"fixed": "fixed, not re-reviewed", "owner-fix": "you decided to fix it", "owner-drop": "you dropped it"}


def built(c: Change, now: datetime) -> None:
    """After a build: the next round reviews it, unless its loop's latest round was the last."""
    s = c.step
    task = next((t for t in c.plan.tasks if t.id == s.task), None) if c.plan else None
    subject = subject_of(c, task) if task and task.origin == "review" else FINAL
    lp = c.loops.get(subject) if subject != FINAL else None
    if task is None or lp is None or not lp.last:
        go(c, StepKind.REVIEW, s.task)
        return
    limit = lp.policy.max_rounds + lp.extra
    if lp.found <= lp.policy.last_round_at and lp.round < limit and any(d.upheld is None for d in task.disputes):
        go(c, StepKind.REVIEW, task.id, RECHECK)  # TD-218: the early last round's rejections are judged
    elif lp.round >= limit and lp.found >= lp.policy.ask_owner_at:
        ask(c, question(lp, task), now)
    else:
        end(c, lp, task)


def passed(c: Change) -> None:
    """A task review passed: its loop ends clean, or by count when a rejections-only check left a repair unreviewed."""
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
    if task and (lp := c.loops.get(subject_of(c, task))) and not lp.ended:
        lp.ended = "count" if lp.unreviewed else "clean"


def end(c: Change, lp: RoundLoop, task: Task) -> None:
    """The loop ends with this repair unreviewed; the Change goes on to the next task or the final review."""
    lp.unreviewed.append(task.id)
    lp.ended = "count" if lp.found <= lp.policy.last_round_at else "max"
    done = resolved(c, task.id)
    for t in c.plan.tasks if c.plan else []:
        t.done = t.done or t.id in done
    nxt = open_task(c)
    if nxt:
        go(c, StepKind.BUILD, nxt.id)
    else:
        go(c, StepKind.REVIEW, mode="final")


def question(lp: RoundLoop, task: Task) -> Question:
    """The owner's choice after the last allowed round: every finding of that round, whole, with what became of it."""
    said = "; ".join(_said(f) for f in lp.findings if f.raised == lp.round)
    text = (
        f"Review round {lp.round} of task {lp.subject} found {lp.found} new findings, and it was the last allowed "
        f"round: {said}. Another round reviews this repair; a retry rebuilds the task from its plan entry with a "
        "fresh builder, the rejected attempt archived on a branch."
    )
    return Question(step=StepKind.REVIEW, text=text, options=OPTIONS, cause=f"{PREFIX}{lp.subject} {task.id}")


def _said(f: RoundFinding) -> str:
    why = f" ({' '.join(f.reason.split())})" if f.state == "rejected" else ""
    return f"{f.id} {HOW.get(f.state, f.state)}{why}: {f.text}"


def decided(c: Change, q: Question, target: str) -> None:
    """The owner's choice: one more round reviews the repair, or the subject task is rebuilt (TD-208, TD-210)."""
    subject, _, task_id = (q.cause or "").removeprefix(PREFIX).partition(" ")
    if (lp := c.loops.get(subject)) is None:
        return
    if target == RETRY:
        go(c, StepKind.BUILD, subject, RETRY)
    else:
        lp.extra += 1
        go(c, StepKind.REVIEW, task_id)
