"""After a looped repair build (TD-208, TD-330): the next round, a rejections-only check, the owner or the end.

The final review's loop also reaches its reviewer's prompt (the plan tasks to name, the focus of a re-entry),
restarts on the owner's request (TD-215, TD-216) and starts a new attempt when the owner has it planned again (TD-210).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.evidence import criteria
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.merge_records import QUEUE_UNSEEN
from owlbear_delivery_next.change_contracts.models import Answer, ErrorKind, Exit, Option, Outcome, Question, StepKind
from owlbear_delivery_next.change_contracts.round_records import BRIEF, FINAL, PLAN, RECHECK, Completion, RoundLoop
from owlbear_delivery_next.change_flow.moves import ask, go, loop_of, open_task, resolved, subject_of
from owlbear_delivery_next.change_flow.round_marks import unmet

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change, Task
    from owlbear_delivery_next.change_contracts.round_records import Ended, RoundFinding
    from owlbear_delivery_next.change_flow.loop import StepResult

PREFIX = cause_key(ErrorKind.REVIEW, StepKind.REVIEW, "round ")
RETRY = "rebuild"  # a build step's mode while its rejected attempt is undone before a fresh build (TD-210)
CLEAN = "clean"  # the final review step's mode while the Change's work is undone for a plan from a clean state
OPTIONS = [
    Option(id="another", label="Another round", next="another"),
    Option(id="retry", label="Reject the work and retry it", next=RETRY),
]
FINAL_OPTIONS = [  # TD-217: every retry of the final review is a rebuild of tasks or a new plan (TD-210)
    Option(id="rebuild", label="Rebuild the ticked tasks", next=RETRY),
    Option(id="accept", label="Accept as done", next="accept"),
    Option(id="another", label="Another round", next="another"),
    Option(id="replan", label="Plan again from the brief on the existing code", next=RETRY),
    Option(id=CLEAN, label="Plan again from the brief from a clean state", next=RETRY),
]
HOW = {
    "fixed": "fixed, not re-reviewed",
    "standing": "rejected; the reviewer accepted that",
    "owner-fix": "you decided to fix it",
    "owner-drop": "you dropped it",
}
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
    root = next((t for t in c.plan.tasks if t.id == subject_of(c, task)), None) if task and c.plan else None
    if root is not None and (root.origin in ADDED or (root.origin == "review" and root.fixes is None)):
        if any(d.upheld is None for d in task.disputes):
            go(c, StepKind.REVIEW, task.id, RECHECK)  # its rejections are judged, never its work twice (TD-235)
            return
        done = resolved(c, task.id)
        for t in c.plan.tasks:
            t.done = t.done or t.id in done
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
    if not lp.last:
        go(c, StepKind.REVIEW, reviewed, "final" if final else None)
    elif any(d.upheld is None for d in task.disputes):
        go(c, StepKind.REVIEW, reviewed, RECHECK)  # TD-330: the last round's rejections are judged first
    elif lp.many():
        ask(c, question(lp, task), now)
    else:
        end(c, lp, task)


def passed(c: Change, now: datetime) -> bool:
    """A review passed: its loop ends clean, or as its last round ended when it only judged that round's rejections.

    After the check of a last allowed round that found many, the owner chooses instead (TD-208, TD-330).

    Returns:
        Whether the owner was asked.
    """
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
    if (lp := loop_of(c, task)) is None or lp.ended:
        return False
    judged = [task.id] if task else lp.batch
    if c.step.mode == RECHECK and lp.many() and judged:
        ask(c, question(lp, next(t for t in c.plan.tasks if t.id == judged[-1])), now)
        return True
    lp.ended = lp.ending() if judged and judged[-1] in lp.unreviewed else "clean"
    lp.batch = []
    return False


def end(c: Change, lp: RoundLoop, task: Task, ended: Ended = "") -> None:
    """The loop ends with this repair unreviewed; the Change goes to the next task, the final review or publishing."""
    lp.unreviewed.append(task.id)
    lp.ended = ended or lp.ending()
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
            "Rebuild undoes the ticked plan tasks' work and has fresh builders build them again, the rejected work "
            "archived on a branch; with none ticked, Accept as done publishes the Change as it is, with these findings "
            "recorded as accepted by you. Another round reviews the whole Change again; Plan again from the brief "
            "makes a new plan, on the existing code or from a clean state."
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
    why = f" ({' '.join(f.reason.split())})" if f.state in {"rejected", "standing"} else ""
    return f"{f.id} {HOW.get(f.state, f.state)}{why}: {f.text}"


def decided(c: Change, q: Question, target: str) -> None:
    """The owner's choice: one more round, a retry (TD-210), or the final loop accepted.

    A task's retry rebuilds it from its plan entry. The final review's rebuilds the ticked plan tasks once their work is
    undone (TD-217), or plans again from the brief on the existing code or from a clean state.
    """
    subject, _, task_id = (q.cause or "").removeprefix(PREFIX).partition(" ")
    if (lp := c.loops.get(subject)) is None:
        return
    said = q.answer
    if target == RETRY and subject != FINAL:
        go(c, StepKind.BUILD, subject, RETRY)
    elif target == RETRY and said and said.option == "replan":
        replan(c, lp, why(lp, "on the existing code"), said.at)
    elif target == RETRY and said:
        lp.rebuild = [] if said.option == CLEAN else picked(c, said.tasks)
        go(c, StepKind.REVIEW, None, CLEAN if said.option == CLEAN else RETRY)  # the work is undone first
    elif target == "accept":
        if subject == FINAL:  # TD-341: the criteria its open findings report unmet, accepted as the owner's decision
            c.waived |= {k.id: k.text for k in unmet(c, lp)}
        if task := next((t for t in c.plan.tasks if t.id == task_id), None) if c.plan else None:
            end(c, lp, task, "accepted")
    else:
        lp.extra, lp.completion, lp.rebuild = lp.extra + 1, None, []
        go(c, StepKind.REVIEW, None if subject == FINAL else task_id, "final" if subject == FINAL else None)


def picked(c: Change, tasks: list[str]) -> list[str]:
    """The named plan tasks, in plan order: what a final retry rebuilds."""
    return [t.id for t in c.plan.tasks if t.origin == "plan" and t.id in tasks] if c.plan else []


def why(lp: RoundLoop, how: str) -> str:
    """What the planner is told when the owner asks for a new plan after the final review's last round."""
    said = "; ".join(f"{f.id}: {f.text}" for f in lp.findings if f.raised == lp.round)
    return (
        f"The owner rejected the work after final review round {lp.round} and asked for a new plan from the brief, "
        f"{how}. That round's findings: {said}"
    )


def replan(c: Change, lp: RoundLoop, reason: str, now: datetime) -> None:
    """Plan again from the brief (TD-210): a new attempt of the final loop, the old plan's loops in its history.

    The new plan's tasks replace the old ones once it is accepted; a merge consent no longer counts.
    """
    old = lp.model_copy(update={"history": [], "ended": "replanned", "rebuild": [], "undo": ""})
    tasks = [x for k, x in c.loops.items() if k not in {FINAL, PLAN, BRIEF}]
    history = [*lp.history, old, *tasks]
    kept = {k: c.loops[k] for k in (PLAN, BRIEF) if k in c.loops}  # the planner's and the brief's own loops
    c.loops = {FINAL: RoundLoop(subject=FINAL, attempt=lp.attempt + 1, policy=lp.policy, history=history), **kept}
    c.consent = None
    go(c, StepKind.PLAN)
    c.outcome = Outcome(exit=Exit.BACK, reason=reason, at=now)  # the planner sees why it plans again


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
    if any(q.cause == QUEUE_UNSEEN and q.answer is None for q in c.questions):
        return "answer the merge-queue question first"  # a restart would retire it while an enqueue may land
    if (
        s.kind == StepKind.MERGE
        and c.consent is not None
        and c.queue is None
        and not (c.outcome and c.outcome.exit == Exit.ASK)
    ):
        return "a merge is under way"  # a queued PR is taken out first by the fold's barrier (TD-226)
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
