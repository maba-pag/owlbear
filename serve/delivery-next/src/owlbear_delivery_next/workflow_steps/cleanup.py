"""Cleanup: preserve unmerged commits and uncommitted files, verify both, then remove the worktree (D3, D4 §3.2)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import failures
from owlbear_delivery_next.change_contracts.models import Episode, ErrorKind, Exit, Option, StepKind, Stop, Waiting
from owlbear_delivery_next.change_flow import budgets, worktree
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.git.remote_git import RemoteGitError, run_remote_git
from owlbear_delivery_next.github.provider import BranchState, classify_checks
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import briefs, change_record, decision_fixes, project_home
from owlbear_delivery_next.state_store.backlog import Backlog, BacklogError
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.workflow_steps import disposable, engine, pullback

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.workflow_steps.engine import Ctx


class PreservationError(Exception):
    """Preservation cannot represent or verify an entry; the workspace stays untouched."""


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
    ignored: tuple[str, ...] = ()  # ignored files and links outside regenerable directories


def _bytes(path: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, check=True, timeout=120
    ).stdout


def _present(path: Path) -> bool:
    return path.is_symlink() or path.exists()


def _kind(full: Path) -> str:
    try:
        mode = full.lstat().st_mode
    except FileNotFoundError, NotADirectoryError:
        return "gone"
    if stat.S_ISLNK(mode):
        return "link"
    if stat.S_ISREG(mode):
        return "file"
    msg = f"{full} is not a regular file or a symlink; keep it in the workspace"
    raise PreservationError(msg)


def _linked(path: Path, branch: str) -> None:
    out = _bytes(path, "rev-parse", "--git-dir", "--git-common-dir", "--symbolic-full-name", "HEAD")
    git_dir, common, head = out.decode().splitlines()
    if (path / git_dir).resolve() == (path / common).resolve() or head != f"refs/heads/{branch}":
        msg = f"{path} is not a linked worktree on the expected branch {branch}"
        raise PreservationError(msg)


def _ignored(path: Path, rel: str) -> list[str]:
    """Inventory ignored entries without following links or silently skipping nested repositories."""
    if REGENERABLE & set(Path(rel).parts):
        return []
    full = path / rel
    if full.is_symlink() or not full.is_dir():
        _kind(full)
        return [rel]
    if _present(full / ".git"):
        msg = f"{full} is a nested repository; keep it in the workspace"
        raise PreservationError(msg)
    children = sorted(full.iterdir())
    if not children:
        msg = f"{full} is an empty directory that the archive cannot represent"
        raise PreservationError(msg)
    return [kept for child in children for kept in _ignored(path, f"{rel}/{child.name}")]


def inventory(path: Path, branch: str, keep: Sequence[str]) -> Inventory:
    """Commits outside every kept ref, every path ``git status`` reports, and ignored files worth keeping."""
    _linked(path, branch)
    kept = [k for k in keep if engine.git_ok(path, "rev-parse", "--verify", "--quiet", f"{k}^{{commit}}")]
    commits = worktree.git(path, "rev-list", f"refs/heads/{branch}", "--not", *kept, "--").split()
    args = ("status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=all")
    dirty, ignored, entries = [], [], iter(_bytes(path, *args).split(b"\0"))
    for entry in entries:
        if entry[:3] == b"!! ":
            ignored += _ignored(path, entry[3:].decode(errors="surrogateescape").rstrip("/"))
        elif entry:
            dirty.append(entry[3:].decode(errors="surrogateescape"))
            if entry[:1] in {b"R", b"C"}:
                next(entries, None)  # the rename's source path
    for rel in dirty:
        _kind(path / rel)
    return Inventory(tuple(commits), tuple(dirty), tuple(ignored))


def large(path: Path, inv: Inventory) -> bool:
    """Whether the ignored files are too large to archive."""
    return sum((path / p).lstat().st_size for p in inv.ignored) > LARGE


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _regular(name: str, data: bytes, mode: int = 0o644) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size, info.mode = len(data), mode
    return info


def _parent(directory: int, name: str) -> int | None:
    """Open a no-follow parent; absent or regular-file replacements mean its old children were deleted."""
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        try:
            mode = os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode
        except FileNotFoundError:
            return None
        if stat.S_ISREG(mode):
            return None
        raise


def _worktree_member(path: Path, rel: str) -> tuple[tarfile.TarInfo, bytes] | None:
    """Read a leaf entry through no-follow directory descriptors, retaining links and file modes."""
    name = Path(rel)
    if name.is_absolute() or ".." in name.parts or not name.parts:
        raise PreservationError(rel)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(path, flags)
    try:
        for part in name.parts[:-1]:
            child = _parent(directory, part)
            if child is None:
                return None
            os.close(directory)
            directory = child
        leaf = name.parts[-1]
        try:
            mode = os.stat(leaf, dir_fd=directory, follow_symlinks=False).st_mode
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(mode):
            info = tarfile.TarInfo(f"files/{rel}")
            info.type = tarfile.SYMTYPE
            info.linkname = os.readlink(leaf, dir_fd=directory)
            return info, b""
        if not stat.S_ISREG(mode):
            raise PreservationError(path / rel)
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as handle:
            mode = os.fstat(handle.fileno()).st_mode
            if not stat.S_ISREG(mode):
                raise PreservationError(path / rel)
            data = handle.read()
        return _regular(f"files/{rel}", data, stat.S_IMODE(mode)), data
    finally:
        os.close(directory)


def _parts(
    path: Path, dirty: Sequence[str], ignored: Sequence[str] = ()
) -> tuple[list[tuple[tarfile.TarInfo, bytes]], dict[str, str]]:
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
    members = [(_regular(name, data), data) for name, data in parts.items()]
    members.extend(member for rel in dict.fromkeys([*dirty, *ignored]) if (member := _worktree_member(path, rel)))
    return members, blobs


def _oid(algorithm: str, data: bytes) -> str:
    return hashlib.new(algorithm, b"blob %d\0" % len(data) + data).hexdigest()


def preserve(path: Path, branch: str, inv: Inventory, dest: Path, stem: str) -> list[Path]:
    """Bundle the named branch and archive the uncommitted work; raise unless both read back exactly.

    Index blobs read back to their object ids, so a staged version the working tree replaced is restorable.

    Raises:
        PreservationError: A bundle or archive did not verify.
    """
    members, blobs = _parts(path, inv.dirty, inv.ignored)
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    saved: list[Path] = []
    if inv.commits:
        bundle = dest / f"{stem}.bundle"
        _bytes(path, "bundle", "create", str(bundle), f"refs/heads/{branch}")
        if not engine.git_ok(path, "bundle", "verify", "--quiet", str(bundle)):
            raise PreservationError(bundle)
        saved.append(bundle)
    if inv.dirty or inv.ignored:
        archive = dest / f"{stem}.tar"
        algorithm = worktree.git(path, "rev-parse", "--show-object-format").strip()
        with tarfile.open(archive, "w") as tar:
            for info, data in members:
                tar.addfile(info, io.BytesIO(data))
        with tarfile.open(archive) as tar:
            read = {m.name: m for m in tar.getmembers()}
            for info, data in members:
                back = read.get(info.name)
                if back is None or (back.type, back.mode, back.linkname) != (info.type, info.mode, info.linkname):
                    raise PreservationError(archive, info.name)
                reader = tar.extractfile(back) if back.isreg() else None
                body = reader.read() if reader is not None else b""
                blob = info.name in blobs and blobs[info.name] != _oid(algorithm, body)
                if _digest(body) != _digest(data) or blob:
                    raise PreservationError(archive, info.name)
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
    """Watch the required and declared checks on the merge commit; a failure, however late, drafts a fix Change.

    Running checks keep cleanup pending with a growing poll and no deadline, failed ones or not; the start window
    applies only to checks that never started.
    """
    sha = pr.merge_commit_sha if pr and pr.merged else None
    if not sha or c.step.mode == "abandon":
        return c, None
    declared, required = profile.names(ctx.profile, profile.DECLARED), profile.names(ctx.profile, profile.REQUIRED)
    state = classify_checks(ctx.gh.observe_commit_checks(ctx.repository, sha), declared, required)
    target = c.names.target
    for failed in state.failed:
        fix_change(ctx, c, failed.name, sha, failed.url or "")
    if state.running or state.missing:
        if c.missing is None or c.missing.head != sha:
            c.missing = Episode(head=sha, since=ctx.now)
        window = timedelta(seconds=int(profile.value(ctx.profile, profile.WINDOW, "300")))
        elapsed = ctx.now - c.missing.since
        if state.running or elapsed < window:
            if state.running:
                reason = f"{len(state.running)} of {state.expected} checks running on {target}"
            else:
                reason = f"waiting up to {window.seconds // 60} min for {', '.join(state.missing)} to start on {target}"
            wake = ctx.now + max(ctx.poll() - ctx.now, min(elapsed / 2, budgets.PAUSE_CAP))
            return c, engine.pending(Waiting.CI, reason, wake)
        ctx.log(c.slug, "target-checks-unfinished", sha=sha, missing=list(state.missing))
    c.missing = None
    return c, None


def _retire_branch(ctx: Ctx, c: Change, pr: PullRequest | None) -> StepResult | None:
    if not pr or not pr.merged or profile.value(ctx.profile, profile.DELETE) != "yes":
        return None
    branch = c.names.branch
    retired = ctx.gh.delete_branch(ctx.repository, branch, pr.head_sha)
    if retired.state is not BranchState.MOVED:
        ctx.log(c.slug, "branch-retired", branch=branch, result=retired.state)
        return None
    cause = failures.cause_key(
        ErrorKind.STATE,
        StepKind.CLEANUP,
        [f"pr-{pr.number}", f"merged-{pr.head_sha}", f"current-{retired.head}", "branch-moved"],
    )
    ctx.log(c.slug, "branch-kept", branch=branch, head=retired.head, merged=pr.head_sha)
    if any(q.cause == cause and q.answer and q.answer.option == "keep" for q in c.questions):
        return None
    text = (
        f"origin/{branch} now points to {retired.head[:12]}, not the merged head {pr.head_sha[:12]}. "
        "Delivery kept it rather than risk other work. Keep that branch and finish cleanup, or pause."
    )
    return engine.ask(
        StepKind.CLEANUP,
        text,
        cause,
        [
            Option(id="keep", label="Keep the remote branch and finish cleanup", next="retry"),
            Option(id="pause", label="Pause", next="pause"),
        ],
    )


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:
    """Check the merged result, close an abandoned PR, preserve what the worktree alone holds, remove it, pull back."""
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr) if c.names.pr else None
    c, held = target_check(ctx, c, pr)
    if held is not None:
        return c, held
    if retired := _retire_branch(ctx, c, pr):
        return c, retired
    if c.step.mode == "abandon" and pr and pr.state == "open":
        ctx.gh.close_pull_request(ctx.repository, pr.number)
    path, saved, kept = Path(c.names.worktree), [], False
    if c.names.worktree and (path / ".git").exists():
        saved, kept, stopped = _workspace(ctx, c, path, pr)
        if stopped is not None:
            return c, stopped
    if not kept and (why := disposable.remove(ctx.repo, ctx.store, c.slug)):
        ctx.log(c.slug, "read-only-kept", why=why)
    line = {"slug": c.slug, "at": ctx.now.isoformat(), "pr": c.names.pr, "merged": bool(pr and pr.merged)}
    line |= {"merge": pr.merge_commit_sha if pr else None, "preserved": [str(s) for s in saved]}
    line |= {"kept": str(path)} if kept else {}
    with (ctx.store.root / "history.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    if notice := change_record.save(ctx.store, c, pr, ctx.now):
        ctx.log(c.slug, "change-record", notice=notice)
    fixes(ctx, c, pr)
    if pr and pr.merged and c.step.mode != "abandon":
        c.pullback = pullback.run(ctx.repo, c.names.target, ctx.now)
        ctx.log(c.slug, "pullback", **c.pullback.model_dump(mode="json", exclude={"at"}))
    reason = f"worktree removed; {len(saved)} preservation file(s)"
    reason = f"workspace kept: large ignored files ({path})" if kept else reason
    return c, StepResult(exit=Exit.DONE, reason=reason, preserved=[str(s) for s in saved])


def merged_files(repo: Path, target: str, sha: str) -> frozenset[str]:
    """The files the merge commit changed against its first parent; the target is fetched when it is missing."""
    if not engine.git_ok(repo, "cat-file", "-e", f"{sha}^{{commit}}"):
        engine.fetch(repo, target)
    out = _bytes(repo, "diff", "--name-only", "--no-renames", "-z", f"{sha}^1", sha)
    return frozenset(p.decode(errors="surrogateescape") for p in out.split(b"\0") if p)


def fixes(ctx: Ctx, c: Change, pr: PullRequest | None) -> None:
    """Settle the decision fix entries that went into *c* (TD-428); a failure is a logged notice, never a stop."""
    if ctx.store.shared is None:
        return
    # an abandoning Change credits nothing, even when its PR merged before cleanup read it: it reopens its entries
    sha = pr.merge_commit_sha if pr and pr.merged and c.step.mode != "abandon" else None
    try:
        files = merged_files(ctx.repo, c.names.target, sha) if sha else None
        clone = project_home.clone_id(project_home.clone_dir(ctx.repo))
        decision_fixes.verified(Backlog.of(ctx.store), c.slug, clone, files, pr.url if pr and sha else "")
    except (BacklogError, DataRepoError, RemoteGitError, StoreError, OSError, subprocess.SubprocessError) as exc:
        ctx.log(c.slug, "decision-fixes", notice=f"the decision fixes of {c.slug} were not updated: {exc}"[:300])


def _workspace(ctx: Ctx, c: Change, path: Path, pr: PullRequest | None) -> tuple[list[Path], bool, StepResult | None]:
    keep = _keep(ctx, path, c, pr)
    try:
        inv = inventory(path, c.names.branch, keep)
        kept = large(path, inv)
    except (PreservationError, OSError, subprocess.SubprocessError) as exc:
        return [], False, _stopped(ctx, path, f"could not inventory {path}: {exc}")
    if kept:
        ctx.log(c.slug, "workspace-kept", path=str(path), reason="large ignored files")
        return [], True, None
    saved, stopped = _retire(ctx, c, path, inv)
    return saved, False, stopped


def _stopped(ctx: Ctx, path: Path, reason: str) -> StepResult:
    action = f"Copy or delete {path}; Delivery left it untouched"
    stop = Stop(kind=ErrorKind.STATE, reason=reason, action=action, resume=f"{path} clean or gone", at=ctx.now)
    return StepResult(exit=Exit.STOP, reason=reason, stop=stop)


def _retire(ctx: Ctx, c: Change, path: Path, inv: Inventory) -> tuple[list[Path], StepResult | None]:
    """Preserve and verify what the worktree alone holds, then remove it; a failed verification stops untouched."""
    dest = ctx.store.root / "changes" / c.slug / "preserved"
    try:
        saved = preserve(path, c.names.branch, inv, dest, f"{c.slug}-{len(c.names.preserved) + 1}")
    except (PreservationError, subprocess.CalledProcessError, OSError, tarfile.TarError) as exc:
        return [], _stopped(ctx, path, f"could not save {path}: {exc}")
    dirty, ignored = list(inv.dirty)[:50], list(inv.ignored)[:50]
    saved_paths = [str(s) for s in saved]
    ctx.log(c.slug, "preserved", commits=len(inv.commits), dirty=dirty, ignored=ignored, saved=saved_paths)
    worktree.git(ctx.repo, "worktree", "remove", "--force", str(path))
    worktree.git(ctx.repo, "worktree", "prune")
    return saved, None
