"""After a looped repair build (TD-208, TD-218): the next round, a rejections-only check, the owner or the end.

The final review's loop also reaches its reviewer's prompt (the plan tasks to name, the focus of a re-entry) and
restarts on the owner's request (TD-215, TD-216).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.evidence import criteria
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.models import Answer, ErrorKind, Option, Question, StepKind
from owlbear_delivery_next.moves import ask, go, loop_of, open_task, resolved
from owlbear_delivery_next.round_records import FINAL, RECHECK, Completion, RoundLoop

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change, Task
    from owlbear_delivery_next.round_records import Ended, RoundFinding

PREFIX = cause_key(ErrorKind.REVIEW, StepKind.REVIEW, "round ")
RETRY = "rebuild"  # a build step's mode while its rejected attempt is undone before a fresh build (TD-210)
OPTIONS = [
    Option(id="another", label="Another round", next="another"),
    Option(id="retry", label="Reject the work and retry it", next=RETRY),
]
FINAL_OPTIONS = [
    Option(id="another", label="Another round", next="another"),
    Option(id="accept", label="Accept as done", next="accept"),
]
HOW = {"fixed": "fixed, not re-reviewed", "owner-fix": "you decided to fix it", "owner-drop": "you dropped it"}
TASKS = (
    "Name the plan tasks each finding belongs to in its `tasks`; when no plan task fits, say why in `no_task` instead."
)
FOCUS = (
    "New work reached this review after its loop ended. Judge the diff since the last reviewed commit and what it "
    "affects or calls, plus obvious low-hanging issues, without being blind to the rest; do not review unrelated code "
    "in depth."
)
RESTARTED = "restarted"  # the answer that retires a question a restart of the review loop superseded
ADDED = frozenset({"ci", "pr-feedback", "integration", "person-check"})  # fixes added to reviewed work


def built(c: Change, r: StepResult | None, now: datetime) -> None:
    """After a build: the next round reviews it, unless its loop's latest round was the last.

    A final-review repair is done once built: the next final round reviews it with the whole Change. Work added to
    reviewed work gets no review of its own: the next round of the loop it joined reviews it (TD-215).
    """
    s = c.step
    task = next((t for t in c.plan.tasks if t.id == s.task), None) if c.plan else None
    if task is not None and (task.origin in ADDED or (task.origin == "review" and task.fixes is None)):
        task.done = True
        if nxt := open_task(c):
            go(c, StepKind.BUILD, nxt.id)
        else:
            go(c, StepKind.REVIEW, mode="final")
        return
    lp = loop_of(c, task) if task and task.origin == "review" else None
    if task is None or lp is None:
        go(c, StepKind.REVIEW, s.task)
        return
    final = lp.subject == FINAL
    if final:
        task.done, lp.batch = True, [task.id]
        lp.completion = Completion(head=r.head or "", criteria=criteria(c)) if lp.last and r else None
    reviewed = None if final else task.id
    limit = lp.policy.max_rounds + lp.extra
    if not lp.last:
        go(c, StepKind.REVIEW, reviewed, "final" if final else None)
    elif lp.found <= lp.policy.last_round_at and lp.round < limit and any(d.upheld is None for d in task.disputes):
        go(c, StepKind.REVIEW, reviewed, RECHECK)  # TD-218: the early last round's rejections are judged
    elif lp.round >= limit and lp.found >= lp.policy.ask_owner_at:
        ask(c, question(lp, task), now)
    else:
        end(c, lp, task)


def passed(c: Change) -> None:
    """A review passed: its loop ends clean, or by count when it only judged an early last round's rejections."""
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
    if (lp := loop_of(c, task)) is None or lp.ended:
        return
    judged = [task.id] if task else lp.batch
    lp.ended = "count" if judged and judged[-1] in lp.unreviewed else "clean"
    lp.batch = []


def end(c: Change, lp: RoundLoop, task: Task, ended: Ended = "") -> None:
    """The loop ends with this repair unreviewed; the Change goes to the next task, the final review or publishing."""
    lp.unreviewed.append(task.id)
    lp.ended = ended or ("count" if lp.found <= lp.policy.last_round_at else "max")
    if lp.subject == FINAL:
        go(c, StepKind.PUBLISH)  # the batch stays: a round added for new work judges its rejections
        return
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
    if lp.subject == FINAL:
        what, options = f"Final review round {lp.round}", FINAL_OPTIONS
        then = (
            "Another round reviews the whole Change again; Accept as done publishes it as it is, with these findings "
            "recorded as accepted by you."
        )
    else:
        what, options = f"Review round {lp.round} of task {lp.subject}", OPTIONS
        then = (
            "Another round reviews this repair; a retry rebuilds the task from its plan entry with a fresh builder, "
            "the rejected attempt archived on a branch."
        )
    text = f"{what} found {lp.found} new findings, and it was the last allowed round: {said}. {then}"
    return Question(step=StepKind.REVIEW, text=text, options=options, cause=f"{PREFIX}{lp.subject} {task.id}")


def _said(f: RoundFinding) -> str:
    why = f" ({' '.join(f.reason.split())})" if f.state == "rejected" else ""
    return f"{f.id} {HOW.get(f.state, f.state)}{why}: {f.text}"


def decided(c: Change, q: Question, target: str) -> None:
    """The owner's choice: one more round, a rebuild of the subject task (TD-210), or the final loop accepted."""
    subject, _, task_id = (q.cause or "").removeprefix(PREFIX).partition(" ")
    if (lp := c.loops.get(subject)) is None:
        return
    if target == RETRY:
        go(c, StepKind.BUILD, subject, RETRY)
    elif target == "accept":
        if task := next((t for t in c.plan.tasks if t.id == task_id), None) if c.plan else None:
            end(c, lp, task, "accepted")
    else:
        lp.extra, lp.completion = lp.extra + 1, None
        go(c, StepKind.REVIEW, None if subject == FINAL else task_id, "final" if subject == FINAL else None)


def review_lines(c: Change, task: Task | None) -> list[str]:
    """A final round's plan tasks, which its findings name (TD-216), and after new work its focus (TD-215)."""
    lp = c.loops.get(FINAL)
    if task is not None or lp is None or c.step.mode == RECHECK or c.plan is None:
        return []
    planned = [f"- {t.id}: {' '.join(t.title.split())[:200]}" for t in c.plan.tasks if t.origin == "plan"]
    lines = ["", "## Plan tasks", TASKS, *planned]
    if lp.reentry and lp.head:
        lines += ["", f"## New since the last round: `git diff {lp.head[:12]}..HEAD`", FOCUS]
    return lines


def restartable(c: Change) -> str:
    """Why the final review loop cannot restart now, else "": a live, unmerged Change at or after its final review."""
    lp, s = c.loops.get(FINAL), c.step
    if lp is None:
        return "the final review has not started"
    if c.finished_at or c.intent.abandoned_at or s.kind == StepKind.CLEANUP:
        return "the Change has ended"
    if c.stop or c.env is not None:
        return "the Change is stopped or runs your check's environment; settle that first"
    if s.kind == StepKind.MERGE and c.consent is not None:
        return "a merge is under way"
    at = s.kind in {StepKind.PUBLISH, StepKind.FOLLOW, StepKind.CHECK, StepKind.MERGE}
    repairing = any(t.id == s.task and t.fixes == FINAL for t in (c.plan.tasks if c.plan else []))
    return "" if at or (s.kind == StepKind.REVIEW and s.task is None) or repairing else "not at its final review yet"


def restart(c: Change, now: datetime) -> None:
    """A new attempt of the final loop from round 0, its history kept; superseded questions and consent go."""
    lp = c.loops[FINAL]
    old = lp.model_copy(update={"history": [], "ended": lp.ended or "restarted"})
    c.loops[FINAL] = RoundLoop(subject=FINAL, attempt=lp.attempt + 1, policy=lp.policy, history=[*lp.history, old])
    for t in c.plan.tasks if c.plan else []:
        t.done = t.done or t.fixes == FINAL  # an unbuilt repair of the old attempt retires
    for q in c.questions:
        if q.answer is None:
            q.answer = Answer(option=RESTARTED, text="the final review loop was restarted", at=now)
            q.effect_observed_at = now
    c.consent = c.outcome = None
    go(c, StepKind.REVIEW, mode="final")
