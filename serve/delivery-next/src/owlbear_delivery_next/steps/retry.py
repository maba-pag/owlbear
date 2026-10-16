"""A rejected task attempt before its fresh build (TD-210, TD-214): archived on a branch, then undone forward.

The attempt's own commits since the task's base are reverted in one commit, made in a scratch worktree and promoted
by a fast-forward only while the Change head is still the archived one; target merges stay. A restart finds a
promoted undo by its message. Any failure asks the owner: another round on the kept work, or a pause.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.git_files import git_common_dir
from owlbear_delivery_next.models import Option, Question, StepKind
from owlbear_delivery_next.moves import ask, go, open_task, subject_of
from owlbear_delivery_next.round_flow import PREFIX, RETRY
from owlbear_delivery_next.round_records import RoundLoop
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.models import Change, Task
    from owlbear_delivery_next.store import Lock, Store

UNDO = "Undo attempt {attempt} of task {task}, rejected by the owner for a fresh build (TD-210)"
OPTIONS = [
    Option(id="another", label="Another round on the kept work", next="another"),
    Option(id="pause", label="Pause this Change", next="pause"),
]


def archive(slug: str, subject: str, attempt: int) -> str:
    """The branch that keeps a rejected attempt; nothing deletes it."""
    return f"refs/heads/owlbear/archive/{slug}/{subject}/a{attempt}"


def undone(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """Archive and undo the rejected attempt of a task being retried; whether this run was used for it."""
    s = change.step
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    lp = change.loops.get(s.task or "")
    if s.kind != StepKind.BUILD or s.mode != RETRY or task is None or lp is None:
        return False
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    try:
        why = _undo(path, archive(change.slug, task.id, lp.attempt), task, lp.attempt)
    except (OSError, subprocess.SubprocessError) as exc:
        why = " ".join(str(getattr(exc, "stderr", "") or exc).split())[:300]
    now = datetime.now(UTC)
    event = {"event": "undo", "at": now.isoformat(timespec="seconds"), "task": task.id, "attempt": lp.attempt}
    store.log(lock, change.slug, event | ({"error": why} if why else {}))
    if why:
        ask(change, _question(change, task, lp, why), now)
    else:
        _rotated(change, task, lp)
    store.write(lock, change)
    return True


def _undo(path: Path, ref: str, task: Task, attempt: int) -> str:
    """Keep the head on *ref*, then promote one commit reverting the attempt's commits; why not, else ""."""
    head, message = worktree.head(path), UNDO.format(attempt=attempt, task=task.id)
    kept = _rev(path, ref)
    if kept and head != kept:  # promoted by an earlier run that stopped before its record was written
        last = worktree.git(path, "log", "-1", "--format=%s").strip()
        return "" if _rev(path, "HEAD^") == kept and last == message else f"the branch moved from {kept[:12]}"
    if worktree.git(path, "status", "--porcelain").strip():
        return "the worktree has uncommitted edits"
    if task.base is None:
        return "the commit the task's first build started from is unknown"
    if kept is None:
        worktree.git(path, "update-ref", "-m", message, ref, head, "")
    commits = worktree.git(path, "rev-list", "--first-parent", "--no-merges", f"{task.base}..{head}").split()
    if commits:
        worktree.git(path, "merge", "--ff-only", "--quiet", _reverted(path, head, commits, message))
    return ""


def _rev(path: Path, ref: str) -> str | None:
    found = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [worktree.GIT, "rev-parse", "--verify", "--quiet", ref], cwd=path, capture_output=True, text=True, check=False
    )
    return found.stdout.strip() if found.returncode == 0 else None


def _reverted(path: Path, head: str, commits: list[str], message: str) -> str:
    """The undo commit on *head*, newest commit reverted first, made where the Change's worktree stays untouched."""
    scratch = path.parent / f".undo-{path.name}"
    _remove(path, scratch)
    worktree.git(path, "worktree", "add", "--quiet", "--detach", str(scratch), head)
    try:
        for commit in commits:
            worktree.git(scratch, "revert", "--no-commit", commit)
        if not worktree.git(scratch, "status", "--porcelain").strip():
            return head  # the commits cancel out: nothing to undo
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


def _rotated(c: Change, task: Task, lp: RoundLoop) -> None:
    """The undone attempt goes to the loop's history and its repairs retire; a fresh builder starts the task."""
    old = lp.model_copy(update={"history": [], "ended": "retried"})
    c.loops[task.id] = RoundLoop(subject=task.id, attempt=lp.attempt + 1, policy=lp.policy, history=[*lp.history, old])
    for t in c.plan.tasks if c.plan else []:
        if t.fixes and subject_of(c, t) == task.id:
            t.done = True
    task.base, task.built_by, task.earlier = None, "", ""
    go(c, StepKind.BUILD, task.id)
