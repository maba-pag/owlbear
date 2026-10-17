"""A rejected task attempt before its fresh build (TD-210, TD-214): archived on a branch, then undone forward.

The attempt's own commits since the task's base are reverted in one commit, made in a scratch worktree and promoted
by a fast-forward; target merges stay. An attempt whose range also holds another task's build (an integration) is
not undone: its commits cannot be told apart. Each retried head keeps its own archive, so a retry after another round
archives again; a restart finds a promoted undo by its message and archive. Any failure asks the owner: another
round on the kept work, or a pause.

The final review's retry (TD-217) undoes the ticked plan tasks' commits the same way (the task ranges `rebuilds` picks,
without any other task's build inside them), or, for a plan from a clean state, sets the tree back to the target's at
the merge base in one commit.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import rebuilds, round_flow
from owlbear_delivery_next.git_files import git_common_dir
from owlbear_delivery_next.models import Option, Question, StepKind
from owlbear_delivery_next.moves import ask, go, open_task, subject_of
from owlbear_delivery_next.round_flow import CLEAN, PREFIX, RETRY
from owlbear_delivery_next.round_records import FINAL
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.models import Change, Task
    from owlbear_delivery_next.round_records import RoundLoop
    from owlbear_delivery_next.store import Lock, Store

UNDO = "Undo attempt {attempt} of task {task}, rejected by the owner for a fresh build (TD-210)"
REBUILD = "Undo tasks {tasks} for their fresh build, rejected by the owner at final review attempt {attempt} (TD-210)"
CLEAN_UNDO = "Undo the Change's work for a new plan from a clean state, the owner's choice at final review attempt {n}"
OPTIONS = [
    Option(id="another", label="Another round on the kept work", next="another"),
    Option(id="pause", label="Pause this Change", next="pause"),
]


def archive(slug: str, subject: str, attempt: int, head: str) -> str:
    """The branch that keeps a rejected attempt at *head*; nothing deletes it."""
    return f"refs/heads/owlbear/archive/{slug}/{subject}/a{attempt}-{head[:12]}"


def undone(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """Archive and undo the rejected attempt of a task being retried; whether this run was used for it."""
    s = change.step
    if s.kind == StepKind.REVIEW and s.task is None and s.mode in {RETRY, CLEAN} and FINAL in change.loops:
        return _final(store, lock, change, repo)
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    lp = change.loops.get(s.task or "")
    if s.kind != StepKind.BUILD or s.mode != RETRY or task is None or lp is None:
        return False
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    try:
        why = _undo(path, change, task, lp)
    except (OSError, subprocess.SubprocessError) as exc:
        why = _failure(exc)
    now = datetime.now(UTC)
    event = {"event": "undo", "at": now.isoformat(timespec="seconds"), "task": task.id, "attempt": lp.attempt}
    store.log(lock, change.slug, event | ({"error": why} if why else {}))
    if why:
        ask(change, _question(change, task, lp, why), now)
    else:
        rebuilds.fresh(change, task)
        go(change, StepKind.BUILD, task.id)
    store.write(lock, change)
    return True


def _failure(exc: OSError | subprocess.SubprocessError) -> str:
    return " ".join(str(getattr(exc, "stderr", "") or exc).split())[:300]


def _undo(path: Path, c: Change, task: Task, lp: RoundLoop) -> str:
    """Archive the head, then promote one commit reverting the attempt's commits; why not, else ""."""
    head, message = worktree.head(path), UNDO.format(attempt=lp.attempt, task=task.id)
    if _promoted(path, archive(c.slug, task.id, lp.attempt, ""), message):
        return ""  # promoted by an earlier run that stopped before its record was written
    if worktree.git(path, "status", "--porcelain").strip():
        return "the worktree has uncommitted edits"
    if task.base is None:
        return "the commit the task's first build started from is unknown"
    inside = [t.id for t in (c.plan.tasks if c.plan else [])[lp.since :] if t.base and subject_of(c, t) != task.id]
    if inside:
        return f"task {', '.join(inside)} was built during this attempt, so the attempt's own commits are unclear"
    _archived(path, archive(c.slug, task.id, lp.attempt, head), head, message)
    commits = _range(path, task.base, head)
    if commits:
        worktree.git(path, "merge", "--ff-only", "--quiet", _reverted(path, head, commits, message))
    return ""


def _promoted(path: Path, prefix: str, message: str) -> bool:
    """Whether HEAD is this undo, promoted onto the head archived under *prefix*."""
    if worktree.git(path, "log", "-1", "--format=%s").strip() != message:
        return False
    parent = _rev(path, "HEAD^")
    return bool(parent) and _rev(path, prefix + parent[:12]) == parent


def _archived(path: Path, ref: str, head: str, message: str) -> None:
    if _rev(path, ref) is None:
        worktree.git(path, "update-ref", "-m", message, ref, head, "")


def _range(path: Path, base: str, head: str) -> list[str]:
    """The non-merge commits on the first-parent line after *base* up to *head*, newest first."""
    return worktree.git(path, "rev-list", "--first-parent", "--no-merges", f"{base}..{head}").split()


def _rev(path: Path, ref: str) -> str | None:
    found = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [worktree.GIT, "rev-parse", "--verify", "--quiet", ref], cwd=path, capture_output=True, text=True, check=False
    )
    return found.stdout.strip() if found.returncode == 0 else None


def _reverted(path: Path, head: str, commits: list[str], message: str) -> str:
    """The undo commit on *head*, newest commit reverted first; *head* when the commits cancel out."""

    def revert(scratch: Path) -> None:
        for commit in commits:
            worktree.git(scratch, "revert", "--no-commit", commit)

    return _scratch(path, head, message, revert)


def _scratch(path: Path, head: str, message: str, change: Callable[[Path], object]) -> str:
    """The commit *change* makes on *head*, made where the Change's worktree stays untouched; *head* if none."""
    scratch = path.parent / f".undo-{path.name}"
    _remove(path, scratch)
    worktree.git(path, "worktree", "add", "--quiet", "--detach", str(scratch), head)
    try:
        change(scratch)
        if not worktree.git(scratch, "status", "--porcelain").strip():
            return head
        worktree.git(scratch, "commit", "--quiet", "-m", message)
        return worktree.head(scratch)
    finally:
        _remove(path, scratch)


def _remove(path: Path, scratch: Path) -> None:
    for step in (
        lambda: worktree.git(path, "worktree", "remove", "--force", "--force", str(scratch)),
        lambda: shutil.rmtree(scratch, ignore_errors=True),
        lambda: worktree.git(path, "worktree", "prune"),
    ):
        with contextlib.suppress(subprocess.SubprocessError, OSError):
            step()


def _question(c: Change, task: Task, lp: RoundLoop, why: str) -> Question:
    """The owner's way on when the undo fails: the last repair is reviewed again, or the Change pauses."""
    repair = open_task(c)
    text = (
        f"Delivery could not undo attempt {lp.attempt} of task {task.id} for its fresh build: {why}. Nothing was "
        "undone. Another round reviews the last repair of the kept work; a pause lets you fix the branch first."
    )
    cause = f"{PREFIX}{task.id} {repair.id if repair else task.id}"
    return Question(step=StepKind.BUILD, text=text, options=OPTIONS, cause=cause)


def _final(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """Undo the ticked tasks' work before their fresh builds, or all the Change's work before a clean plan."""
    lp, clean = change.loops[FINAL], change.step.mode == CLEAN
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    undo, why = ([], "") if clean else rebuilds.undoing(change, lp)
    try:
        why = why or (_cleaned(path, change, lp) if clean else _taken(path, change, lp, undo))
    except (OSError, subprocess.SubprocessError) as exc:
        why = _failure(exc)
    now = datetime.now(UTC)
    event = {"event": "undo", "at": now.isoformat(timespec="seconds"), "task": FINAL, "attempt": lp.attempt}
    store.log(lock, change.slug, event | {"tasks": lp.rebuild, "clean": clean} | ({"error": why} if why else {}))
    if why:
        text = (
            f"Delivery could not undo the work you rejected at final review attempt {lp.attempt}: {why}. Nothing was "
            "undone. Another round reviews the kept work again; a pause lets you fix the branch first."
        )
        repair = next((t.id for t in reversed(change.plan.tasks) if t.fixes == FINAL), FINAL) if change.plan else FINAL
        ask(change, Question(step=StepKind.REVIEW, text=text, options=OPTIONS, cause=f"{PREFIX}{FINAL} {repair}"), now)
    elif clean:
        how = "from a clean state: Delivery undid the Change's earlier work, which stays archived on a branch"
        round_flow.replan(change, lp, round_flow.why(lp, how), now)
    else:
        rebuilds.rotated(change, lp, undo)
    store.write(lock, change)
    return True


def _taken(path: Path, c: Change, lp: RoundLoop, undo: list[Task]) -> str:
    """Archive the head, then promote one commit reverting the undone tasks' own commits; why not, else ""."""
    head, message = worktree.head(path), REBUILD.format(tasks=", ".join(lp.rebuild), attempt=lp.attempt)
    if _promoted(path, archive(c.slug, FINAL, lp.attempt, ""), message):
        return ""
    if worktree.git(path, "status", "--porcelain").strip():
        return "the worktree has uncommitted edits"
    commits, why = _commits(path, c, undo, head)
    if why:
        return why
    _archived(path, archive(c.slug, FINAL, lp.attempt, head), head, message)
    if commits:
        worktree.git(path, "merge", "--ff-only", "--quiet", _reverted(path, head, commits, message))
    return ""


def _commits(path: Path, c: Change, undo: list[Task], head: str) -> tuple[list[str], str]:
    """The undone tasks' own commits, newest first: their ranges less every other task's build inside them."""
    tasks, ids = c.plan.tasks if c.plan else [], {t.id for t in undo}
    ranges = {t.id: _range(path, t.base, t.head) for t in tasks if t.base and t.head}
    spans = {t.id: worktree.git(path, "rev-list", "--first-parent", f"{t.base}..{t.head}").split() for t in undo}
    for t in tasks:  # a build that started inside an undone range and was never accepted has no known end
        if t.base and not t.head and t.id not in ids and any(t.base in spans[u.id] and t.base != u.head for u in undo):
            return [], f"task {t.id} was built inside the undone work and its commits are not recorded"
    mine = {x for t in undo for x in ranges[t.id]}
    take = mine - {x for k, r in ranges.items() if k not in ids for x in r}
    line = max((_range(path, t.base, head) for t in undo if t.base), key=len, default=[])
    return [x for x in line if x in take], ""


def _cleaned(path: Path, c: Change, lp: RoundLoop) -> str:
    """Archive the head, then promote one commit setting the tree back to the target's at the merge base."""
    head, message = worktree.head(path), CLEAN_UNDO.format(n=lp.attempt)
    if _promoted(path, archive(c.slug, FINAL, lp.attempt, ""), message):
        return ""
    if worktree.git(path, "status", "--porcelain").strip():
        return "the worktree has uncommitted edits"
    base = worktree.git(path, "merge-base", "HEAD", worktree.tracking(path, c.names.target)).strip()
    _archived(path, archive(c.slug, FINAL, lp.attempt, head), head, message)
    reset = _scratch(path, head, message, lambda scratch: worktree.git(scratch, "read-tree", "-u", "--reset", base))
    worktree.git(path, "merge", "--ff-only", "--quiet", reset)
    return ""
