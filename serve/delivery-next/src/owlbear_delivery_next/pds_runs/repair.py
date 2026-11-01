"""A PDS update's CI repair (#777): what it checks again and never pushes, and its pages laid out for that check.

The repair is the pack run's (``pack_repair``) with this ``Kind``. Its protected content is the pages: everything under
``web/`` but the served PDS files, and ``project_host/pages.py``. A repair that changes them is laid into the candidate
whole, as its commit holds them, and audited, browser-tested and challenged again as one more counted round before
Delivery pushes it (``run``); the merge then waits for the owner's approval of those changes. The pin, the vendored
tree and the served files only an update may change: a repair that changes them is never pushed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.impeccable_runs.pack_repair_content import CHECKS, PUSH, Kind
from owlbear_delivery_next.pds_runs import checks, sessions, tree
from owlbear_delivery_next.pds_runs.context import CANDIDATE, HEAD

if TYPE_CHECKING:
    from owlbear_delivery_next.pds_runs.context import Context
    from owlbear_delivery_next.pds_runs.job import Job


def protected(_package: str, path: str) -> bool:
    """Whether the repository *path* is one of the pages a repair's check covers."""
    return path == tree.PAGES or (path.startswith(tree.WEB) and not path.startswith(tree.SERVED))


def refused(_package: str, path: str, _kept: bool, _skills: list[str]) -> bool:  # noqa: FBT001 - Kind.refused's shape
    """Whether the repository *path* is the pin, the vendored tree or a served file, which only an update may change."""
    return path == tree.PIN or path.startswith((tree.TREE, tree.SERVED))


PDS = Kind(
    rules=(
        "This session is not a PDS update: the update's rules on the audit's findings do not apply. "
        f"{CHECKS} A change to the pages under `web/` or to `project_host/pages.py` is audited, browser-tested and "
        "challenged again before it is pushed and needs the owner's approval; never change `pds.json`, the vendored "
        f"`pds/` tree or the served files under `web/pds/`. {PUSH}"
    ),
    label=sessions.UPDATE, content="the pages", changes="the pages", refusal="PDS files only an update may change",
    protected=protected, refused=refused, recheck="audit", publish="publish",
    run=lambda job, cfg: job.live.session(job.store, cfg), job=sessions.UPDATE, skills=checks.skills,
)  # fmt: skip


def _pages(at: Path) -> dict[str, bytes]:
    """The repair's protected files in the tree at *at*, by repository path."""
    pages = {p: d for p, d in tree.files(at, tree.WEB).items() if not p.startswith(tree.SERVED)}
    return pages | ({tree.PAGES: (at / tree.PAGES).read_bytes()} if (at / tree.PAGES).is_file() else {})


def snapshot(job: Job, ctx: Context) -> dict[str, bytes]:
    """The repair commit's pages, read from the commit itself, never from what an earlier repair left.

    Raises:
        pack_files.PackError: Git could not read it, or its pin, vendored tree or served files are not the candidate's.
    """
    r, git, root, at = ctx.repair, job.live.git, Path(ctx.checkout["root"]), job.workspace / HEAD
    try:
        tree.worktree(root, at, r.commit, git)
        if tree.digest(tree.protected(at)) != ctx.candidate:
            msg = f"the repair {r.commit[:12]} holds release files other than the candidate's"
            raise pack_files.PackError(msg)
        return _pages(at)
    finally:
        tree.remove(root, at, git)


def lay(job: Job, ctx: Context) -> None:
    """Make the candidate's pages exactly the repair commit's, whatever they were before.

    Raises:
        pack_files.PackError: The commit could not be read, or it holds another release.
    """
    snap, at = snapshot(job, ctx), job.workspace / CANDIDATE
    tree.lay(at, dict.fromkeys(_pages(at)) | snap)


def unlike(job: Job, ctx: Context) -> list[str]:
    """The pages whose bytes in the candidate are not the repair commit's; empty when alike.

    Raises:
        pack_files.PackError: The commit could not be read, or it holds another release.
    """
    snap, now = snapshot(job, ctx), _pages(job.workspace / CANDIDATE)
    return sorted(p for p in snap.keys() | now.keys() if snap.get(p) != now.get(p))
