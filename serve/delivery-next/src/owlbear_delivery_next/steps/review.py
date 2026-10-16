"""Engine part of the review step: record the verdict with its inputs; findings become a repair task (P5)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import budgets, disputes, loop, tools
from owlbear_delivery_next.failures import signature
from owlbear_delivery_next.models import ErrorKind, Exit, Inputs, Review, Score, StepKind, Task
from owlbear_delivery_next.steps import reconsider, worktree

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Lock, Store


def lines(review: tools.ReviewResult) -> list[str]:
    """Every finding as one line, so a repair task can list it by key."""
    return [" ".join(f"- {f.place}: {f.problem} - fix: {f.fix}".split()) for f in review.findings]


def findings(review: tools.ReviewResult, limit: int = 4000) -> list[str]:
    """Every finding on its own line, packed into parts of at most *limit* characters; none is cut or dropped.

    A finding's bounded fields keep each line far below a task's detail limit.
    """
    return pack(lines(review), limit)


def pack(items: list[str], limit: int = 4000) -> list[str]:
    """Lines packed into parts of at most *limit* characters, in order; none is cut or dropped."""
    parts: list[str] = []
    for line in items:
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
    found = lines(p)
    fixes = repair(change, task, found)
    update = {"review": review, "fix_task": fixes[0], "more_fixes": fixes[1:]}
    return result.model_copy(update=update | {"score": score(found, change.step.kind)})


def score(found: list[str], kind: str) -> Score:
    """The failing findings, each known by its place and problem and not its fix, so rounds compare progress."""
    ids = {signature(ErrorKind.REVIEW, kind, line.removeprefix("- ").rsplit(" - fix: ", 1)[0]) for line in found}
    return Score(failing=len(found), findings=sorted(ids))


def repair(change: Change, task: Task | None, found: list[str], kept: Mapping[str, str] | None = None) -> list[Task]:
    """The repair task carrying every finding line, in parts that each fit a task's details.

    Each part records the review round that found its findings, and which of them the owner decided to fix (*kept*:
    finding line to the owner's note).
    """
    kept = kept or {}
    n = len(change.plan.tasks) + 1 if change.plan else 1
    task = task or (change.plan.tasks[-1] if change.plan and change.plan.tasks else None)
    scope, checks = (task.scope, task.checks) if task else ([], [])
    of = f"task {change.step.task}" if change.step.task else "the final review"
    title = f"Fix {len(found)} review finding(s) of {of}"
    item = task.item if task and change.step.task else None  # a conversation task's repair answers the same item
    parts, round_, tasks = pack(found) or [""], budgets.review_round(change), []
    for i, part in enumerate(parts):
        mine = {f"F{j}": line for j, line in enumerate(part.splitlines(), 1) if line in kept}
        tasks.append(
            Task(
                id=f"t{n + i}",
                title=title + (f" (part {i + 1} of {len(parts)})" if len(parts) > 1 else ""),
                scope=scope,
                checks=checks,
                origin="review",
                detail=part,
                item=item,
                found_in=round_,
                settled=list(mine),
                notes={k: kept[line] for k, line in mine.items() if kept[line]},
            )
        )
    return tasks


def completed(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """A review whose disputed findings the owner decided completes from its held verdict, without a review session.

    A finding the owner sent back with a note is reconsidered first (TD-193).
    """
    if reconsider.judged(store, lock, change, repo):
        return True
    if (result := disputed(change)) is None:
        return False
    now = datetime.now(UTC)
    event = {"event": "step", "at": now.isoformat(timespec="seconds"), "kind": StepKind.REVIEW, "exit": result.exit}
    store.log(lock, change.slug, event | {"reason": result.reason, "disputed": True})
    store.write(lock, loop.apply(change, result, now))
    return True


def disputed(change: Change) -> StepResult | None:
    """A review whose disputed findings the owner decided: its held verdict plus the findings kept to fix (TD-176).

    A repair round is counted only when something is left to fix; the recheck itself never counts one. A finding the
    owner decided to fix passes the round gate once (TD-193).
    """
    s = change.step
    if s.kind != StepKind.REVIEW or s.mode != disputes.DISPUTED:
        return None
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    held = next((v for v in reversed(change.reviews) if v.task == s.task), None)
    kept = disputes.kept(task)
    found = [*(held.findings if held and held.verdict == "fix" else []), *kept]
    if not found:
        return loop.StepResult(exit=Exit.DONE, reason="the owner settled each disputed finding")
    fixes = repair(change, task, found, kept)
    reason = f"{len(found)} finding(s) to fix"
    return loop.StepResult(
        exit=Exit.RETRY,
        reason=reason,
        fix_task=fixes[0],
        more_fixes=fixes[1:],
        score=score(found, s.kind),
        authorised=disputes.authorised(task),
    )
