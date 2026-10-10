"""Cleanup: preserve unmerged commits and uncommitted files, verify both, then remove the worktree (D3, D4 §3.2)."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import profile
from owlbear_delivery_next.git.remote_git import run_remote_git
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, Stop
from owlbear_delivery_next.steps import engine, worktree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.steps.engine import Ctx


class PreservationError(Exception):
    """A bundle or archive could not be verified; the workspace stays untouched."""


@dataclass(frozen=True)
class Inventory:
    """What removing the worktree would lose: commits outside *keep*, and dirty, staged, untracked, conflicted paths."""

    commits: tuple[str, ...]
    dirty: tuple[str, ...]


def _bytes(path: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, check=True, timeout=120
    ).stdout


def inventory(path: Path, branch: str, keep: Sequence[str]) -> Inventory:
    """Commits on the branch outside every kept ref, and every path ``git status`` reports, untracked included."""
    kept = [k for k in keep if engine.git_ok(path, "rev-parse", "--verify", "--quiet", f"{k}^{{commit}}")]
    commits = worktree.git(path, "rev-list", f"refs/heads/{branch}", "--not", *kept, "--").split()
    dirty, entries = [], iter(_bytes(path, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\0"))
    for entry in entries:
        if entry:
            dirty.append(entry[3:].decode(errors="surrogateescape"))
            if entry[:1] in {b"R", b"C"}:
                next(entries, None)  # the rename's source path
    return Inventory(tuple(commits), tuple(dirty))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def preserve(path: Path, branch: str, inv: Inventory, dest: Path, stem: str) -> list[Path]:
    """Bundle the named branch and archive the dirty files; raise unless both read back exactly.

    Raises:
        PreservationError: A bundle or archive did not verify.
    """
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    saved: list[Path] = []
    if inv.commits:
        bundle = dest / f"{stem}.bundle"
        _bytes(path, "bundle", "create", str(bundle), f"refs/heads/{branch}")
        if not engine.git_ok(path, "bundle", "verify", "--quiet", str(bundle)):
            raise PreservationError(bundle)
        saved.append(bundle)
    if inv.dirty:
        archive, expected = dest / f"{stem}.tar", {}
        parts = {
            "changes.diff": _bytes(path, "diff", "--binary", "HEAD"),
            "index.txt": _bytes(path, "ls-files", "--stage", "--", *inv.dirty),
        }
        parts |= {f"files/{p}": (path / p).read_bytes() for p in inv.dirty if (path / p).is_file()}
        with tarfile.open(archive, "w") as tar:
            for name, data in parts.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                expected[name] = _digest(data)
        with tarfile.open(archive) as tar:
            for name, digest in expected.items():
                member = tar.extractfile(name)
                if member is None or _digest(member.read()) != digest:
                    raise PreservationError(archive, name)
        saved.append(archive)
    return saved


def _keep(ctx: Ctx, path: Path, c: Change, pr: PullRequest | None) -> list[str]:
    engine.fetch(path, c.names.target)
    keep = [f"origin/{c.names.target}"]
    if pr and pr.merged:
        if not engine.git_ok(path, "cat-file", "-e", f"{pr.head_sha}^{{commit}}"):
            run_remote_git(
                path, ("fetch", "--quiet", "--no-tags", "origin", f"refs/pull/{pr.number}/head"), kind="read"
            )
        keep.append(pr.head_sha)
    ctx.log(c.slug, "inventory", keep=keep)
    return keep


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:
    """Close an abandoned PR, preserve what the worktree alone holds, remove it, and write the history line."""
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr) if c.names.pr else None
    if c.step.mode == "abandon" and pr and pr.state == "open":
        ctx.gh.close_pull_request(ctx.repository, pr.number)
    path, saved = Path(c.names.worktree), []
    if c.names.worktree and (path / ".git").exists():
        inv = inventory(path, c.names.branch, _keep(ctx, path, c, pr))
        dest = ctx.store.root / "changes" / c.slug / "preserved"
        try:
            saved = preserve(path, c.names.branch, inv, dest, f"{c.slug}-{len(c.names.preserved) + 1}")
        except (PreservationError, subprocess.CalledProcessError, OSError, tarfile.TarError) as exc:
            reason = f"could not save {path}: {exc}"
            action = f"Copy or delete {path}; Delivery left it untouched"
            stop = Stop(kind=ErrorKind.STATE, reason=reason, action=action, resume=f"{path} clean or gone", at=ctx.now)
            return c, StepResult(exit=Exit.STOP, reason=reason, stop=stop)
        ctx.log(
            c.slug, "preserved", commits=len(inv.commits), dirty=list(inv.dirty)[:50], saved=[str(s) for s in saved]
        )
        worktree.git(ctx.repo, "worktree", "remove", "--force", str(path))
        worktree.git(ctx.repo, "worktree", "prune")
    if pr and pr.merged and profile.value(ctx.profile, profile.DELETE) == "yes":
        ctx.gh.delete_branch(ctx.repository, c.names.branch)
    line = {"slug": c.slug, "at": ctx.now.isoformat(), "pr": c.names.pr, "merged": bool(pr and pr.merged)}
    line |= {"merge": pr.merge_commit_sha if pr else None, "preserved": [str(s) for s in saved]}
    with (ctx.store.root / "history.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    reason = f"worktree removed; {len(saved)} preservation file(s)"
    return c, StepResult(exit=Exit.DONE, reason=reason, preserved=[str(s) for s in saved])
