"""Step moves: where a Change goes next, the questions it asks and the tasks it opens (D3 §3.3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.evidence import cover
from owlbear_delivery_next.models import Exit, Outcome, Step, StepKind

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change, Question, Task


def go(c: Change, kind: StepKind, task: str | None = None, mode: str | None = None) -> None:
    """Make *kind* the Change's current step."""
    c.step = Step(kind=kind, task=task, mode=mode)


def enter(c: Change, kind: StepKind, task: str | None = None) -> None:
    """Move to *kind*, keeping the task and the integrate caller the step needs."""
    s = c.step
    again = kind == s.kind == StepKind.CHECK  # an answer during a check returns to that same check
    keep = task or (s.task if kind in {StepKind.BUILD, StepKind.INTEGRATE} or again else None)
    caller = s.mode if s.kind == StepKind.INTEGRATE else str(s.kind)
    final = "final" if kind == StepKind.REVIEW and keep is None else None  # a review without a task is final
    go(c, kind, keep, caller if kind == StepKind.INTEGRATE else final)


def open_task(c: Change) -> Task | None:
    """The first unfinished plan task."""
    return next((t for t in c.plan.tasks if not t.done), None) if c.plan else None


def ask(c: Change, question: Question, now: datetime) -> None:
    """Record *question* from the current step and wait for the owner."""
    q = question.model_copy(update={"id": f"q{len(c.questions) + 1}", "step": c.step.kind})
    c.questions.append(q)
    c.outcome = Outcome(exit=Exit.ASK, cause=q.cause, reason=q.text, who="you", question=q.id, at=now)


def resolved(c: Change, task_id: str | None) -> set[str]:
    """The passed task and, transitively, each task whose review findings it fixed."""
    tasks = {t.id: t for t in c.plan.tasks} if c.plan else {}
    found: set[str] = set()
    while task_id and task_id not in found:
        found.add(task_id)
        task_id = tasks[task_id].fixes if task_id in tasks else None
    return found


def fix_task(c: Change, r: StepResult, fixes: str | None = None) -> str | None:
    """Add the result's repair task to the plan once and return its id."""
    if r.fix_task is None or c.plan is None:
        return None
    if any(t.id == r.fix_task.id for t in c.plan.tasks):
        return r.fix_task.id  # an unfinished task already in the plan is resumed, not duplicated
    c.plan.tasks.append(r.fix_task.model_copy(update={"fixes": fixes}))
    cover(c)
    return r.fix_task.id
