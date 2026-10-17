"""A rejected task attempt before its fresh build (TD-210, TD-214): archived on a branch, then undone forward.

The attempt's own commits, what its build sessions made, are reverted in one commit, made in a scratch worktree and
promoted by a fast-forward; target merges and commits made between sessions stay. An attempt with another task's
build inside it (an integration) is not undone. The head an undo starts from is recorded before anything is promoted:
a restart finds the undo on the branch and never repeats it, and a branch that moved without it stops the undo. Each
retried head keeps its own archive. Any failure asks the owner: another round on the kept work, or a pause.

The final review's retry (TD-217) undoes the ticked plan tasks' commits the same way (the tasks `rebuilds` picks), or,
for a plan from a clean state, sets the tree back to the target's at the merge base in one commit.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import Option, Question, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import FINAL
from owlbear_delivery_next.change_flow import rebuilds, round_flow, worktree
from owlbear_delivery_next.change_flow.moves import ask, go, open_task, subject_of
from owlbear_delivery_next.change_flow.round_flow import CLEAN, PREFIX, RETRY
from owlbear_delivery_next.local_system.git_files import git_common_dir

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Task
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop
    from owlbear_delivery_next.state_store.store import Lock, Store

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
        why = _undo(path, change, task, lp, _start(store, lock, change, lp, path))
    except (OSError, subprocess.SubprocessError) as exc:
        why = _failure(exc)
    lp.undo = ""
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


def _start(store: Store, lock: Lock, change: Change, lp: RoundLoop, path: Path) -> str:
    """The head the undo starts from, recorded before anything is promoted, so that a restart never repeats it."""
    if not lp.undo:
        lp.undo = worktree.head(path)
        store.write(lock, change)
    return lp.undo


def _landed(path: Path, start: str, message: str) -> bool | None:
    """Whether the undo from *start* is on the branch: False while HEAD is still *start*, None if it moved without."""
    if worktree.head(path) == start:
        return False
    lines = worktree.git(path, "rev-list", "--first-parent", "--parents", f"{start}..HEAD").splitlines()
    first = next((line.split()[0] for line in lines if line.split()[1:2] == [start]), None)
    return True if first and worktree.git(path, "log", "-1", "--format=%s", first).strip() == message else None


def _ready(path: Path, start: str, message: str) -> str | None:
    """Why the undo cannot run now, "" when it already landed, or None when it runs now."""
    landed = _landed(path, start, message)
    if landed is not False:
        return "" if landed else "the branch moved since the undo started, without it"
    return "the worktree has uncommitted edits" if worktree.git(path, "status", "--porcelain").strip() else None


def _undo(path: Path, c: Change, task: Task, lp: RoundLoop, start: str) -> str:
    """Archive *start*, then promote one commit reverting the attempt's own commits; why not, else ""."""
    message = UNDO.format(attempt=lp.attempt, task=task.id)
    if (why := _ready(path, start, message)) is not None:
        return why
    inside = [t.id for t in (c.plan.tasks if c.plan else [])[lp.since :] if t.base and subject_of(c, t) != task.id]
    if inside:
        return f"task {', '.join(inside)} was built during this attempt, so the attempt's own commits are unclear"
    tasks = [t for t in (c.plan.tasks if c.plan else []) if (t.base or t.spans) and subject_of(c, t) == task.id]
    commits, why = _commits(path, tasks, start)
    if why:
        return why
    _archived(path, archive(c.slug, task.id, lp.attempt, start), start, message)
    if commits:
        worktree.git(path, "merge", "--ff-only", "--quiet", _reverted(path, start, commits, message))
    return ""


def _commits(path: Path, tasks: list[Task], head: str) -> tuple[list[str], str]:
    """The tasks' own commits, newest first: what their build sessions made, never what came between them."""
    if unknown := [t.id for t in tasks if not t.spans or any(s.endswith("..") for s in t.spans)]:
        return [], f"the commits of task {unknown[0]} are not recorded"
    spans = [span.split("..") for t in tasks for span in t.spans]
    own = {x for start, end in spans for x in _range(path, start, end)}
    line = max((_range(path, start, head) for start, _ in spans), key=len, default=[])
    return [x for x in line if x in own], ""


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
        if not why:
            start = _start(store, lock, change, lp, path)
            why = _cleaned(path, change, lp, start) if clean else _taken(path, change, lp, undo, start)
    except (OSError, subprocess.SubprocessError) as exc:
        why = _failure(exc)
    lp.undo = ""
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
        rebuilds.rotated(change, lp, undo, store.read_profile() or Profile())
    store.write(lock, change)
    return True


def _taken(path: Path, c: Change, lp: RoundLoop, undo: list[Task], start: str) -> str:
    """Archive *start*, then promote one commit reverting the undone tasks' own commits; why not, else ""."""
    message = REBUILD.format(tasks=", ".join(lp.rebuild), attempt=lp.attempt)
    if (why := _ready(path, start, message)) is not None:
        return why
    commits, why = _commits(path, undo, start)
    if why:
        return why
    _archived(path, archive(c.slug, FINAL, lp.attempt, start), start, message)
    if commits:
        worktree.git(path, "merge", "--ff-only", "--quiet", _reverted(path, start, commits, message))
    return ""


def _cleaned(path: Path, c: Change, lp: RoundLoop, start: str) -> str:
    """Archive *start*, then promote one commit setting the tree back to the target's at the merge base."""
    message = CLEAN_UNDO.format(n=lp.attempt)
    if (why := _ready(path, start, message)) is not None:
        return why
    base = worktree.git(path, "merge-base", "HEAD", worktree.tracking(path, c.names.target)).strip()
    _archived(path, archive(c.slug, FINAL, lp.attempt, start), start, message)
    reset = _scratch(path, start, message, lambda scratch: worktree.git(scratch, "read-tree", "-u", "--reset", base))
    worktree.git(path, "merge", "--ff-only", "--quiet", reset)
    return ""
