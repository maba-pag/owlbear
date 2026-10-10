"""Engine part of the review step: record the verdict with its inputs; findings become a repair task (P5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next import tools
from owlbear_delivery_next.models import Inputs, Review, Task
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.sdk_adapter import Run


def recorded(change: Change, task: Task | None, run: Run, path: Path, result: StepResult) -> StepResult:
    """Attach the review record (criteria and covered-path fingerprints) and, for ``fix``, the repair task."""
    p = run.payload
    if not (isinstance(p, tools.ReviewResult) and run.head):
        return result
    criteria = {c.id: c.version for c in change.brief.criteria}
    inputs = Inputs(criteria=criteria, paths=worktree.fingerprints(path, p.covered_paths))
    review = Review(task=change.step.task, commit=run.head, inputs=inputs, verdict=p.verdict)
    if p.verdict == "pass":
        return result.model_copy(update={"review": review})
    n = len(change.plan.tasks) + 1 if change.plan else 1
    task = task or (change.plan.tasks[-1] if change.plan and change.plan.tasks else None)
    scope, checks = (task.scope, task.checks) if task else ([], [])
    fix = Task(id=f"t{n}", title=f"Fix review findings: {result.reason}", scope=scope, checks=checks, origin="review")
    return result.model_copy(update={"review": review, "fix_task": fix})
