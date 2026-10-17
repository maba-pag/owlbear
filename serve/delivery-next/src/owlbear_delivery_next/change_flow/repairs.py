"""Repair chances of the findings loop (TD-123, TD-175): which session repairs, and what a fresh one is told."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import Exit, StepKind
from owlbear_delivery_next.change_contracts.round_records import FINAL

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Task
    from owlbear_delivery_next.change_flow.loop import StepResult

EARLIER = (
    "\n\n## The earlier session's work (from Delivery's records; its session could not be resumed)\n\n{}\n\n"
    "That session built the work these findings are about; you take over its repair."
)


def _producer(c: Change, fixes: str | None) -> Task | None:
    """The task whose session gets the repair chance: the reviewed task, or a final review's previous repair."""
    tasks = c.plan.tasks if c.plan else []
    if fixes and fixes != FINAL:
        return next((t for t in tasks if t.id == fixes), None)
    return next((t for t in reversed(tasks) if t.origin == "review" and t.fixes in {None, FINAL} and t.built_by), None)


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
    """The session a step resumes for its one repair chance: a fix task's producer, or the challenged planner.

    The planner's chance stays in flight, and a replay resumes it again, until its plan is accepted (``bind``).
    """
    s, o = change.step, change.outcome
    if s.kind == StepKind.BUILD and task and task.resume and not task.built_by:
        return task.resume
    if s.kind != StepKind.PLAN:
        return ""
    challenged = o and o.exit == Exit.RETRY and o.challenged
    if not s.repair and challenged and s.session and s.resumed != s.session:
        s.repair = s.session
    return s.repair


def bind(change: Change, task: Task | None, session: str, payload: object, result: StepResult) -> None:
    """Bind an accepted build to the session that made it and what it made; an accepted plan uses up its chance."""
    s = change.step
    if s.kind == StepKind.PLAN and s.repair and result.exit == Exit.DONE:
        s.resumed, s.repair = s.repair, ""
    if s.kind == StepKind.BUILD and task and result.exit == Exit.DONE and isinstance(p := payload, tools.BuildResult):
        task.built_by, task.earlier = session, f"{p.summary} Changed: {', '.join(p.changed_paths)}"[:2000]


def fallback(task: Task | None) -> str:
    """What a fresh session taking over a repair chance is told about the earlier session's work."""
    return EARLIER.format(task.earlier) if task and task.earlier else ""
