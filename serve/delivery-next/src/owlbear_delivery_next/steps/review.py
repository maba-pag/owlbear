"""Engine part of the review step: record the verdict with its inputs; findings become a repair task (P5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next import tools
from owlbear_delivery_next.failures import signature
from owlbear_delivery_next.models import ErrorKind, Inputs, Review, Score, Task
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.session_result import Run


def lines(review: tools.ReviewResult) -> list[str]:
    """Every finding as one line."""
    return [f"- {f.place}: {f.problem} - fix: {f.fix}" for f in review.findings]


def findings(review: tools.ReviewResult, limit: int = 4000) -> list[str]:
    """Every finding on its own line, packed into parts of at most *limit* characters; none is cut or dropped.

    A finding's bounded fields keep each line far below a task's detail limit.
    """
    parts: list[str] = []
    for line in lines(review):
        if parts and len(parts[-1]) + 1 + len(line) <= limit:
            parts[-1] += "\n" + line
        else:
            parts.append(line)
    return parts


def recorded(change: Change, task: Task | None, run: Run, path: Path, result: StepResult) -> StepResult:
    """Attach the review record and, for ``fix``, the repair task(s) carrying every finding.

    The covered paths are the engine's own diff of the reviewed range (both rename ends) and nothing the
    reviewer listed. The record binds their git fingerprints and the head's tree, so a later head keeps the
    review only with identical covered content.
    """
    p = run.payload
    if not (isinstance(p, tools.ReviewResult) and run.head):
        return result
    criteria = {c.id: c.version for c in change.brief.criteria}
    since = task.base if task and change.step.task else None
    covered = worktree.observe(path, change.names.target, since).changed
    inputs = Inputs(criteria=criteria, paths=worktree.fingerprints(path, covered, run.head))
    tree = worktree.tree(path, run.head)
    review = Review(
        task=change.step.task, commit=run.head, inputs=inputs, verdict=p.verdict, tree=tree, findings=lines(p)
    )
    if p.verdict == "pass":
        return result.model_copy(update={"review": review})
    kind = change.step.kind
    found = sorted({signature(ErrorKind.REVIEW, kind, f"{f.place} {f.problem}") for f in p.findings})
    score = Score(failing=len(p.findings), findings=found)
    n = len(change.plan.tasks) + 1 if change.plan else 1
    task = task or (change.plan.tasks[-1] if change.plan and change.plan.tasks else None)
    scope, checks = (task.scope, task.checks) if task else ([], [])
    of = f"task {change.step.task}" if change.step.task else "the final review"
    title = f"Fix {len(p.findings)} review finding(s) of {of}"
    item = task.item if task and change.step.task else None  # a conversation task's repair answers the same item
    parts = findings(p) or [""]
    fixes = [
        Task(
            id=f"t{n + i}",
            title=title + (f" (part {i + 1} of {len(parts)})" if len(parts) > 1 else ""),
            scope=scope,
            checks=checks,
            origin="review",
            detail=part,
            item=item,
        )
        for i, part in enumerate(parts)
    ]
    return result.model_copy(update={"review": review, "fix_task": fixes[0], "more_fixes": fixes[1:], "score": score})
