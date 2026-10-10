"""Cleanup: preserve unmerged commits and uncommitted files, verify both, then remove the worktree (D3, D4 §3.2)."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import briefs, profile
from owlbear_delivery_next.git.remote_git import run_remote_git
from owlbear_delivery_next.github.provider import classify_checks
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import Episode, ErrorKind, Exit, Stop, Waiting
from owlbear_delivery_next.steps import engine, pullback, worktree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.steps.engine import Ctx


class PreservationError(Exception):
    """A bundle or archive could not be verified; the workspace stays untouched."""


# Ignored directories a build or install recreates; never preserved.
REGENERABLE = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".next",
        "coverage",
        ".tox",
    }
)
LARGE = 50 * 1024 * 1024  # ignored files above this keep the workspace instead of archiving them


@dataclass(frozen=True)
class Inventory:
    """What removing the worktree would lose: commits outside *keep*, and dirty, staged, untracked, conflicted paths."""

    commits: tuple[str, ...]
    dirty: tuple[str, ...]
    ignored: tuple[str, ...] = ()  # ignored files outside regenerable directories


def _bytes(path: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, check=True, timeout=120
    ).stdout


def _ignored(path: Path, name: str) -> list[str]:
    """The regular files of one ignored entry (a file or a directory), outside regenerable directories."""
    full = path / name.rstrip("/")
    files = [full] if full.is_file() else sorted(full.rglob("*")) if full.is_dir() and not full.is_symlink() else []
    rels = [p.relative_to(path) for p in files if p.is_file() and not p.is_symlink()]
    return [r.as_posix() for r in rels if not REGENERABLE & set(r.parts)]


def inventory(path: Path, branch: str, keep: Sequence[str]) -> Inventory:
    """Commits outside every kept ref, every path ``git status`` reports, and ignored files worth keeping."""
    kept = [k for k in keep if engine.git_ok(path, "rev-parse", "--verify", "--quiet", f"{k}^{{commit}}")]
    commits = worktree.git(path, "rev-list", f"refs/heads/{branch}", "--not", *kept, "--").split()
    args = ("status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=all")
    dirty, ignored, entries = [], [], iter(_bytes(path, *args).split(b"\0"))
    for entry in entries:
        if entry[:3] == b"!! ":
            ignored += _ignored(path, entry[3:].decode(errors="surrogateescape"))
        elif entry:
            dirty.append(entry[3:].decode(errors="surrogateescape"))
            if entry[:1] in {b"R", b"C"}:
                next(entries, None)  # the rename's source path
    return Inventory(tuple(commits), tuple(dirty), tuple(ignored))


def large(path: Path, inv: Inventory) -> bool:
    """Whether the ignored files are too large to archive."""
    return sum((path / p).stat().st_size for p in inv.ignored) > LARGE


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parts(path: Path, dirty: Sequence[str], ignored: Sequence[str] = ()) -> tuple[dict[str, bytes], dict[str, str]]:
    """Archive parts: both diffs, the index listing, each index blob (conflict stages too), dirty and ignored files.

    Returns the parts and, for each index blob, the object id its bytes must hash to.
    """
    index = _bytes(path, "ls-files", "--stage", "-z", "--", *dirty) if dirty else b""
    blobs = {}
    for entry in filter(None, index.split(b"\0")):
        meta, name = entry.split(b"\t", 1)
        mode, oid, stage = meta.decode().split()
        if mode != "160000":  # a submodule entry names a commit, not a blob
            blobs[f"index/{stage}/{name.decode(errors='surrogateescape')}"] = oid
    parts = {
        "changes.diff": _bytes(path, "diff", "--binary", "HEAD"),
        "staged.diff": _bytes(path, "diff", "--binary", "--cached"),
        "index.txt": index.replace(b"\0", b"\n"),
    }
    parts |= {name: _bytes(path, "cat-file", "blob", oid) for name, oid in blobs.items()}
    parts |= {f"files/{p}": (path / p).read_bytes() for p in dirty if (path / p).is_file()}
    parts |= {f"files/{p}": (path / p).read_bytes() for p in ignored}
    return parts, blobs


def _oid(algorithm: str, data: bytes) -> str:
    return hashlib.new(algorithm, b"blob %d\0" % len(data) + data).hexdigest()


def preserve(path: Path, branch: str, inv: Inventory, dest: Path, stem: str) -> list[Path]:
    """Bundle the named branch and archive the uncommitted work; raise unless both read back exactly.

    Index blobs read back to their object ids, so a staged version the working tree replaced is restorable.

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
    if inv.dirty or inv.ignored:
        archive, expected = dest / f"{stem}.tar", {}
        parts, blobs = _parts(path, inv.dirty, inv.ignored)
        algorithm = worktree.git(path, "rev-parse", "--show-object-format").strip()
        with tarfile.open(archive, "w") as tar:
            for name, data in parts.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                expected[name] = _digest(data)
        with tarfile.open(archive) as tar:
            for name, digest in expected.items():
                member = tar.extractfile(name)
                data = member.read() if member else b""
                blob = name in blobs and blobs[name] != _oid(algorithm, data)
                if member is None or _digest(data) != digest or blob:
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


def fix_change(ctx: Ctx, c: Change, check: str, sha: str, url: str) -> None:
    """Draft one fix Change for a check the merged result fails, once per target, check and merge commit."""
    target = c.names.target
    key = f"{target}:{check}:{sha}"
    if any(e.get("key") == key for e in ctx.events(c.slug, "fix-drafted")):
        return
    draft = {
        "title": f"Fix {check} on {target} after {c.slug}"[:100],
        "outcome": f"{check} passes on {target}. Failing run: {url or sha}",
        "criteria": [f"The {check} check passes on {target}"],
        "scope": ["."],
    }
    code, out = briefs.save_brief(ctx.store, draft)
    if code != 200:  # noqa: PLR2004 - HTTP OK
        ctx.log(c.slug, "fix-draft-failed", key=key, errors=out.get("errors", []))
        return
    ctx.log(c.slug, "fix-drafted", key=key, fix=out["slug"], change=out["change"], url=url)


def target_check(ctx: Ctx, c: Change, pr: PullRequest | None) -> tuple[Change, StepResult | None]:
    """Watch the required and declared checks on the merge commit within the window; a failure drafts a fix Change."""
    sha = pr.merge_commit_sha if pr and pr.merged else None
    if not sha or c.step.mode == "abandon":
        return c, None
    declared, required = profile.names(ctx.profile, profile.DECLARED), profile.names(ctx.profile, profile.REQUIRED)
    state = classify_checks(ctx.gh.observe_commit_checks(ctx.repository, sha), declared, required)
    target = c.names.target
    for failed in state.failed:
        fix_change(ctx, c, failed.name, sha, failed.url or "")
    if state.failed:
        c.missing = None
        return c, None
    if state.running or state.missing:
        if c.missing is None or c.missing.head != sha:
            c.missing = Episode(head=sha, since=ctx.now)
        window = timedelta(seconds=int(profile.value(ctx.profile, profile.WINDOW, "300")))
        if ctx.now - c.missing.since < window:
            reason = f"{len(state.running) + len(state.missing)} of {state.expected} checks running on {target}"
            return c, engine.pending(Waiting.CI, reason, ctx.poll())
        ctx.log(c.slug, "target-checks-unfinished", sha=sha, running=[*state.running, *state.missing])
    c.missing = None
    return c, None


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:
    """Check the merged result, close an abandoned PR, preserve what the worktree alone holds, remove it, pull back."""
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr) if c.names.pr else None
    c, held = target_check(ctx, c, pr)
    if held is not None:
        return c, held
    if c.step.mode == "abandon" and pr and pr.state == "open":
        ctx.gh.close_pull_request(ctx.repository, pr.number)
    path, saved, kept = Path(c.names.worktree), [], False
    if c.names.worktree and (path / ".git").exists():
        inv = inventory(path, c.names.branch, _keep(ctx, path, c, pr))
        if kept := large(path, inv):
            ctx.log(c.slug, "workspace-kept", path=str(path), reason="large ignored files")
        else:
            saved, stopped = _retire(ctx, c, path, inv)
            if stopped is not None:
                return c, stopped
    if pr and pr.merged and profile.value(ctx.profile, profile.DELETE) == "yes":
        ctx.gh.delete_branch(ctx.repository, c.names.branch)
    line = {"slug": c.slug, "at": ctx.now.isoformat(), "pr": c.names.pr, "merged": bool(pr and pr.merged)}
    line |= {"merge": pr.merge_commit_sha if pr else None, "preserved": [str(s) for s in saved]}
    line |= {"kept": str(path)} if kept else {}
    with (ctx.store.root / "history.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    if pr and pr.merged and c.step.mode != "abandon":
        c.pullback = pullback.run(ctx.repo, c.names.target, ctx.now)
        ctx.log(c.slug, "pullback", **c.pullback.model_dump(mode="json", exclude={"at"}))
    reason = f"worktree removed; {len(saved)} preservation file(s)"
    reason = f"workspace kept: large ignored files ({path})" if kept else reason
    return c, StepResult(exit=Exit.DONE, reason=reason, preserved=[str(s) for s in saved])


def _retire(ctx: Ctx, c: Change, path: Path, inv: Inventory) -> tuple[list[Path], StepResult | None]:
    """Preserve and verify what the worktree alone holds, then remove it; a failed verification stops untouched."""
    dest = ctx.store.root / "changes" / c.slug / "preserved"
    try:
        saved = preserve(path, c.names.branch, inv, dest, f"{c.slug}-{len(c.names.preserved) + 1}")
    except (PreservationError, subprocess.CalledProcessError, OSError, tarfile.TarError) as exc:
        reason = f"could not save {path}: {exc}"
        action = f"Copy or delete {path}; Delivery left it untouched"
        stop = Stop(kind=ErrorKind.STATE, reason=reason, action=action, resume=f"{path} clean or gone", at=ctx.now)
        return [], StepResult(exit=Exit.STOP, reason=reason, stop=stop)
    dirty, ignored = list(inv.dirty)[:50], list(inv.ignored)[:50]
    saved_paths = [str(s) for s in saved]
    ctx.log(c.slug, "preserved", commits=len(inv.commits), dirty=dirty, ignored=ignored, saved=saved_paths)
    worktree.git(ctx.repo, "worktree", "remove", "--force", str(path))
    worktree.git(ctx.repo, "worktree", "prune")
    return saved, None
