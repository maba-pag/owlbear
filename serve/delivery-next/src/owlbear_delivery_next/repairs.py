"""Repair chances of the findings loop (TD-123, TD-175): which session repairs, and what a fresh one is told."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next import tools
from owlbear_delivery_next.models import Exit, StepKind

if TYPE_CHECKING:
    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change, Task
    from owlbear_delivery_next.session_result import Run

EARLIER = (
    "\n\n## The earlier session's work (from Delivery's records; its session could not be resumed)\n\n{}\n\n"
    "That session built the work these findings are about; you take over its repair."
)


def _producer(c: Change, fixes: str | None) -> Task | None:
    """The task whose session gets the repair chance: the reviewed task, or a final review's previous repair."""
    tasks = c.plan.tasks if c.plan else []
    if fixes:
        return next((t for t in tasks if t.id == fixes), None)
    return next((t for t in reversed(tasks) if t.origin == "review" and t.fixes is None and t.built_by), None)


def lineage(c: Change, fixes: str | None, origin: str) -> dict[str, str | None]:
    """A new repair's lineage: the task it fixes and, once per producing session, the session to resume.

    A session that already had its repair chance, and a final review's first repair, start fresh.
    """
    found: dict[str, str | None] = {"fixes": fixes}
    made = _producer(c, fixes) if origin == "review" else None
    if made and made.built_by and not any(t.resume == made.built_by for t in (c.plan.tasks if c.plan else [])):
        found |= {"resume": made.built_by, "earlier": made.earlier}
    return found


def session(change: Change, task: Task | None) -> str:
    """The session a step resumes for its one repair chance: a fix task's producer, or the challenged planner."""
    s, o = change.step, change.outcome
    if s.kind == StepKind.BUILD and task and task.resume and not task.built_by:
        return task.resume
    challenged = o and o.exit == Exit.RETRY and o.reason.startswith("plan challenge:")
    if s.kind == StepKind.PLAN and challenged and s.session and s.resumed != s.session:
        s.resumed = s.session
        return s.session
    return ""


def bind(task: Task | None, run: Run, result: StepResult) -> None:
    """Bind an accepted build to the session that made it and what it made, for a later repair chance."""
    if task and result.exit == Exit.DONE and isinstance(p := run.payload, tools.BuildResult):
        task.built_by, task.earlier = run.session_id, f"{p.summary} Changed: {', '.join(p.changed_paths)}"[:2000]


def fallback(task: Task | None) -> str:
    """What a fresh session taking over a repair chance is told about the earlier session's work."""
    return EARLIER.format(task.earlier) if task and task.earlier else ""
