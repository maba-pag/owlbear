"""A stuck step's throwaway copy: its baseline, the repair's delta, and the fix's way onto the Change's branch (#1066).

The copy holds the step worktree's whole state, its unfinished and untracked edits included, committed as a baseline
through a private index, so the step worktree's own index stays as it was. What the repairer changes is measured
against that baseline. A proven fix reaches the branch by a commit Delivery makes on a clean copy of the branch head,
then the step worktree moves to it as a pull-back does; a fix touching a path that holds the step's unfinished edits,
or needing them, is never applied.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.workflow_steps import check_weakening, pullback_replay

SHOWN = 20000  # characters of a diff the owner is shown; a longer one is never applied from his answer


class RepairError(Exception):
    """A copy, a delta or an application failed; the message says what and where, whole."""


def git(at: Path, args: list[str], env: dict[str, str] | None = None, stdin: str | None = None) -> str:
    """Run one Git command in *at*; its output, or ``RepairError`` with everything Git said."""
    done = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector
        [worktree.GIT, *args], cwd=at, capture_output=True, text=True, check=False, timeout=300, env=env, input=stdin
    )
    if done.returncode:
        said = (done.stderr.strip() or done.stdout.strip() or f"exit {done.returncode}").strip()
        msg = f"git {' '.join(args)} in {at} failed: {said}"
        raise RepairError(msg)
    if args[0] == "show" or (args[0] == "diff" and "--binary" in args):
        return done.stdout  # source blobs and binary patches need their exact whitespace
    return done.stdout.rstrip("\n")  # leading blanks are data: `git status` starts " M path"


def copy(step: Path, at: Path) -> str:
    """A detached copy at *at* of the step worktree's whole state; the baseline commit it starts from."""
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ | {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git(step, ["read-tree", "HEAD"], env)
        git(step, ["add", "--all"], env)
        tree = git(step, ["write-tree"], env)
    base = git(step, ["commit-tree", tree, "-p", "HEAD", "-m", "owlbear repair: the stuck step's state"])
    drop(step, at)
    at.parent.mkdir(parents=True, exist_ok=True)
    git(step, ["worktree", "add", "--quiet", "--detach", str(at), base])
    return base


def drop(step: Path, at: Path) -> None:
    """Remove the copy, if any."""
    if at.exists():
        subprocess.run([worktree.GIT, "worktree", "remove", "--force", str(at)], cwd=step, check=False)  # noqa: S603
    shutil.rmtree(at, ignore_errors=True)
    subprocess.run([worktree.GIT, "worktree", "prune"], cwd=step, check=False)  # noqa: S603


def changed(at: Path, base: str) -> list[tuple[str, str]]:
    """What the repairer changed in the copy against its baseline, staged: each path with its new mode and status.

    Python bytecode its check runs wrote is no part of the fix, where the repository does not ignore it.
    """
    found = check_weakening.staged(git, at, base)
    if cache := [p for p, _ in found if "__pycache__/" in p or p.endswith(".pyc")]:
        git(at, ["reset", "--quiet", "--", *cache])
    return [(p, how) for p, how in found if p not in cache]


def commit(at: Path, message: str) -> str:
    """Delivery's commit of the staged change in *at*."""
    git(at, ["commit", "--quiet", "-m", message])
    return git(at, ["rev-parse", "HEAD"])


def shown(step: Path, base: str, fix: str, paths: list[str]) -> tuple[str, bool]:
    """The diff of *paths* between the baseline and the fix, and whether it is too long or binary to show whole."""
    text = git(step, ["diff", base, fix, "--", *paths])
    binary = "Binary files" in text
    return text[:SHOWN], len(text) > SHOWN or binary


def apply(step: Path, branch: str, base: str, fix: str, message: str) -> str:
    """Bring the fix (*base*..*fix*) onto *branch*, checked out in the step worktree; the new branch head.

    Raises:
        RepairError: It touches a path holding the step's unfinished edits, needs them, or Git refused.
    """
    paths = pullback_replay.changed(step, base, fix)
    status = git(step, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    unfinished = {line[len("XY ") :] for line in status.split("\0") if line[len("XY ") :]}
    if overlap := sorted(set(paths) & unfinished):
        msg = f"the fix changes {', '.join(overlap)}, which hold the step's unfinished edits; nothing was applied"
        raise RepairError(msg)
    head, ref = git(step, ["rev-parse", "HEAD"]), f"refs/heads/{branch}"
    clean = step.parent / f".{step.name}-repair-apply"
    drop(step, clean)
    git(step, ["worktree", "add", "--quiet", "--detach", str(clean), head])
    try:
        delta = git(step, ["diff", "--binary", base, fix])
        try:
            git(clean, ["apply", "--index", "--whitespace=nowarn", "-"], stdin=delta)
        except RepairError as exc:
            msg = f"the fix does not apply on {head[:12]} without the step's unfinished edits: {exc}"
            raise RepairError(msg) from exc
        new = commit(clean, message)
    finally:
        drop(step, clean)

    def guard(_paths: list[str]) -> pullback_replay.Local:
        return {}  # the overlap was refused above

    try:
        pullback_replay.apply(step, ref, head, new, guard)
    except pullback_replay.BehindError as exc:
        msg = f"the fix {new[:12]} was not brought onto {branch}: {exc}"
        raise RepairError(msg) from exc
    return new
