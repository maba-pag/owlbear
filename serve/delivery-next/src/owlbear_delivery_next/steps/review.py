"""Engine part of the review step: record the verdict with its inputs; findings become a repair task (P5)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import disputes, loop, round_records, rounds, tools
from owlbear_delivery_next.failures import signature
from owlbear_delivery_next.models import ErrorKind, Exit, Inputs, Review, Score, StepKind, Task
from owlbear_delivery_next.moves import loop_of, subject_of
from owlbear_delivery_next.round_records import FINAL, RECHECK
from owlbear_delivery_next.steps import reconsider, retry, worktree

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from owlbear_delivery_next.config import Settings
    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.round_records import RoundLoop
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Lock, Store


def started(c: Change, task: Task | None, path: Path, settings: Settings) -> None:
    """Before a session: a build opens its span, a task's first build records its base, a plan task's starts its loop.

    A task built before its loop existed (a Change from before TD-208) stays on the earlier rules to its end. A span a
    session left open stays open: its end is unknown, so no undo takes that task's work.
    """
    if c.step.kind == StepKind.REVIEW and task is None:
        _final(c, settings)
    if c.step.kind != StepKind.BUILD or task is None:
        return
    head = worktree.head(path)
    task.spans.append(f"{head}..")
    if task.base is not None:
        return
    task.base = head
    if _subject(c, task) == task.id and task.id not in c.loops:
        rounds.loop(c, task.id, settings).since = len(c.plan.tasks) if c.plan else 0


def _final(c: Change, settings: Settings) -> None:
    """The final loop starts with the first final review; new work after it ended adds one round (TD-215).

    That round also judges the rejections its former last round left unjudged.
    """
    lp = c.loops.get(FINAL)
    if lp is None and not any(v.task is None for v in c.reviews):  # an earlier final review keeps the old rules
        rounds.loop(c, FINAL, settings)
    elif lp is not None and lp.ended:
        lp.ended, lp.last, lp.reentry, lp.completion = "", False, True, None
        lp.extra = max(lp.extra, lp.round + 1 - lp.policy.max_rounds)


def _subject(c: Change, task: Task) -> str | None:
    """The plan task whose loop a review of *task* counts in; none for CI or PR tasks."""
    subject = subject_of(c, task)
    root = next((t for t in c.plan.tasks if t.id == subject), None) if c.plan else None
    return subject if root and root.origin == "plan" else None


def looped(c: Change, task: Task | None) -> RoundLoop | None:
    """The challenge loop a review counts in: its plan task's, or for no task the final review's."""
    return loop_of(c, task)


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
    if change.step.kind == StepKind.BUILD and task and task.spans and task.spans[-1].endswith(".."):
        task.spans[-1] += run.head or _head(path)  # the session's own commits end here, whatever its exit
    if change.step.kind == StepKind.BUILD and result.exit == Exit.DONE and run.head:
        return result.model_copy(update={"head": run.head})  # what a final loop's completion binds (TD-208)
    if not (isinstance(p, tools.ReviewResult) and run.head):
        return result
    criteria = {c.id: c.version for c in change.brief.criteria}
    since = task.base if task and change.step.task else None
    covered = worktree.observe(path, change.names.target, since).changed
    inputs = Inputs(criteria=criteria, paths=worktree.fingerprints(path, covered, run.head))
    tree = worktree.tree(path, run.head)
    found = lines(p)
    if (lp := looped(change, task)) is not None and result.cause is None:
        found = _counted(change, lp, p, task, run.head)
    review = Review(task=change.step.task, commit=run.head, inputs=inputs, verdict=p.verdict, tree=tree, findings=found)
    if p.verdict == "pass":
        return result.model_copy(update={"review": review})
    fixes = repair(change, task, found)
    update = {"review": review, "fix_task": fixes[0], "more_fixes": fixes[1:], "ungated": lp is not None}
    return result.model_copy(update=update | {"score": score(found, change.step.kind)})


def _head(path: Path) -> str:
    """The worktree's HEAD when a session ended without reporting one, or "" (its span stays open)."""
    try:
        return worktree.head(path)
    except OSError, subprocess.SubprocessError:
        return ""


def _counted(c: Change, lp: RoundLoop, p: tools.ReviewResult, task: Task | None, head: str) -> list[str]:
    """Count one verdict and give its new findings their IDs; whether this round is the last is decided now."""
    lp.round += 1
    new = lp.raise_findings([line.removeprefix("- ") for line in lines(p)], [f.tasks for f in p.findings])
    lp.found, lp.head, lp.reentry = len(new), head, False
    recheck = c.step.mode == RECHECK
    lp.last = recheck or lp.found <= lp.policy.last_round_at or lp.round >= lp.policy.max_rounds + lp.extra
    if recheck:
        lp.unreviewed += [task.id] if task else lp.batch  # the check judged its rejections, never its fixes
    elif task is None:
        lp.unreviewed = []  # a full final round reviews the whole Change, every earlier repair included
    return [f.line for f in new]


def score(found: list[str], kind: str) -> Score:
    """The failing findings, each known by its place and problem and not its fix, so rounds compare progress."""
    text = [(round_records.parse(line) or ("", line.removeprefix("- ")))[1] for line in found]
    ids = {signature(ErrorKind.REVIEW, kind, t.rsplit(" - fix: ", 1)[0]) for t in text}
    return Score(failing=len(found), findings=sorted(ids))


def repair(change: Change, task: Task | None, found: list[str], kept: Mapping[str, str] | None = None) -> list[Task]:
    """The repair task carrying every finding line: one task for a looped batch, else parts that fit a task.

    *kept* maps the findings the owner decided to fix to the owner's note; the builder never rejects those.
    """
    kept = kept or {}
    n = len(change.plan.tasks) + 1 if change.plan else 1
    whole = looped(change, task) is not None
    task = task or (change.plan.tasks[-1] if change.plan and change.plan.tasks else None)
    scope, checks = (task.scope, task.checks) if task else ([], [])
    of = f"task {change.step.task}" if change.step.task else "the final review"
    title = f"Fix {len(found)} review finding(s) of {of}"
    item = task.item if task and change.step.task else None  # a conversation task's repair answers the same item
    parts, tasks = (["\n".join(found)] if whole else pack(found)) or [""], []
    for i, part in enumerate(parts):
        fix = Task(
            id=f"t{n + i}",
            title=title + (f" (part {i + 1} of {len(parts)})" if len(parts) > 1 else ""),
            scope=scope,
            checks=checks,
            origin="review",
            detail=part,
            item=item,
        )
        listed = dict(zip(disputes.keyed(fix), [ln for ln in part.splitlines() if ln.startswith("- ")], strict=True))
        fix.settled = [k for k, line in listed.items() if line in kept]
        fix.notes = {k: kept[listed[k]] for k in fix.settled if kept[listed[k]]}
        tasks.append(fix)
    return tasks


def completed(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """A review whose disputed findings the owner decided completes from its held verdict, without a review session.

    A finding the owner sent back with a note is reconsidered first (TD-193); a retry's undo runs before its build.
    """
    if retry.undone(store, lock, change, repo) or reconsider.judged(store, lock, change, repo):
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
    judged = disputes.target(change, task)
    held = next((v for v in reversed(change.reviews) if v.task == s.task), None)
    kept = disputes.kept(judged)
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
        ungated=looped(change, task) is not None or disputes.authorised(judged),
    )
