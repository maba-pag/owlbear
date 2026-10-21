"""Publishing decision files without letting Git combine two versions of one (TD-424, TD-419 slice 3).

Every function runs under the data repository's lock. Before a write the checkout catches up with its remote, so an
expected revision is checked against the remote's file. A rejected push is rebased only when the remote changed no
decision file this checkout changed too; when the remote changed a file just committed, the expected revision was
stale: that commit is taken back and the save reported stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionFileError
from owlbear_decisions.storage import DECISIONS_DIR, parse

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

UPSTREAM = "@{upstream}"


@dataclass(frozen=True)
class Sent:
    """What became of one commit and push; `stale` when the remote had changed a committed file first."""

    stale: bool = False
    notice: str = ""


def _decision_file(rel: str) -> bool:
    parts = rel.split("/")
    return len(parts) > 1 and parts[-2] == DECISIONS_DIR and rel.endswith(".md")


def _rev(shared: DataRepo, ref: str, until: float) -> str:
    said = shared.git("rev-parse", "--verify", "-q", ref, until=until)
    return "" if said.returncode else said.stdout.strip()


def _changed(shared: DataRepo, base: str, tip: str, until: float) -> set[str] | None:
    said = shared.git("diff", "--name-only", "--no-renames", base, tip, "--", until=until)
    return None if said.returncode else {r for r in said.stdout.splitlines() if _decision_file(r)}


def _diverged(shared: DataRepo, until: float) -> tuple[set[str], set[str]] | None:
    """The decision files changed here and on the fetched remote since they parted; None when Git cannot tell."""
    if not (base := _merge_base(shared, until)):
        return None
    ours, theirs = _changed(shared, base, "HEAD", until), _changed(shared, base, UPSTREAM, until)
    return None if ours is None or theirs is None else (ours, theirs)


def _merge_base(shared: DataRepo, until: float) -> str:
    said = shared.git("merge-base", "HEAD", UPSTREAM, until=until)
    return "" if said.returncode else said.stdout.strip()


def rebase(shared: DataRepo, until: float) -> str:
    """Rebase on the fetched remote unless both sides changed one decision file; why it did not, else nothing."""
    if (sides := _diverged(shared, until)) is None:
        return "Git cannot compare the checkout with its remote"
    if both := sides[0] & sides[1]:
        return f"{', '.join(sorted(both))} changed here and on the remote; the owner resolves it"
    return shared.rebase(until)


def catch_up(shared: DataRepo, until: float) -> str:
    """Fetch, and when the checkout is behind its remote and clean, rebase on it; why it did not, else nothing."""
    fetched = shared.git("fetch", "-q", until=until)
    if fetched.returncode:
        return fetched.stderr.strip()[:200] or "git fetch failed"
    behind = shared.git("rev-list", "--count", f"HEAD..{UPSTREAM}", until=until)
    if behind.returncode:
        return "the checkout's branch follows no remote branch"
    if behind.stdout.strip() == "0":
        return ""
    status = shared.git("status", "--porcelain", "--untracked-files=no", until=until)
    if status.returncode or status.stdout.strip():
        return "the checkout has uncommitted files"
    return rebase(shared, until)


def publish(shared: DataRepo, paths: list[Path], message: str, until: float) -> Sent:
    """Commit *paths* alone and push; a rejected push never rebases over a remote change of a decision file here."""
    before = _rev(shared, "HEAD", until)
    if failed := shared.commit(paths, message, until):
        return Sent(notice=failed)
    rels = {p.relative_to(shared.root).as_posix() for p in paths}
    made = _ours(shared, before, rels, until)
    pushed = shared.git("push", "-q", until=until)
    if pushed.returncode == 0:
        return Sent()
    return _rejected(shared, rels, (before, made), pushed.stderr, until)


def _ours(shared: DataRepo, before: str, rels: set[str], until: float) -> str:
    """HEAD when it is the commit this call made: child of *before*, changing only files of *rels*; else nothing.

    A batch may name a file it did not change (a rule kept as it is, guarding its revision); the commit then holds
    only the others, and is still this call's own.
    """
    after = _rev(shared, "HEAD", until)
    if not after or after == before or _rev(shared, f"{after}~1", until) != before:
        return ""  # no commit, or a hook added another one: never ours to take back
    said = shared.git("diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", after, until=until)
    changed = set(said.stdout.splitlines())
    return after if not said.returncode and changed and changed <= rels else ""


def _rejected(shared: DataRepo, rels: set[str], commits: tuple[str, str], why: str, until: float) -> Sent:
    where = f"saved and committed in {shared.root}"
    if shared.git("fetch", "-q", until=until).returncode or (sides := _diverged(shared, until)) is None:
        return Sent(notice=f"{where}, but the push failed: {why.strip()[:200]}")
    ours, theirs = sides
    if stale := theirs & rels:
        return _take_back(shared, commits, stale, rels, until)
    if both := ours & theirs:
        listed = ", ".join(sorted(both))
        return Sent(notice=f"{where}, but not published: {listed} changed here and on the remote; the owner decides")
    if failed := shared.rebase(until):
        return Sent(notice=f"{where}, but it could not be rebased on the remote: {failed}; push it by hand")
    sent = shared.git("push", "-q", until=until)
    if sent.returncode:
        return Sent(notice=f"{where}, but the push failed: {sent.stderr.strip()[:200]}")
    return Sent()


def _take_back(shared: DataRepo, commits: tuple[str, str], stale: set[str], rels: set[str], until: float) -> Sent:
    """Undo the verified commit this call made (only that one, every file of it), then rebase: a revision was stale."""
    before, made = commits
    ids = ", ".join(sorted(Path(r).stem for r in stale))
    notice = f"another checkout changed {ids} first, so this save was taken back; reload it and save again"
    if not made and _rev(shared, "HEAD", until) != before:
        return Sent(stale=True, notice=f"another checkout changed {ids} first; this save's commit is not provably "
                    "its own, so it stays unpublished: fix by hand")  # fmt: skip
    if made:  # the branch moves back only if it still points at our commit; our files return to their parent's
        moved = shared.git("update-ref", "-m", "owlbear: take back a stale decision save", "HEAD", before, made,
                           until=until)  # fmt: skip
        if moved.returncode:
            return Sent(stale=True, notice=f"{notice}; its commit {made[:9]} stays: {moved.stderr.strip()[:200]}")
        shared.git("restore", f"--source={before}", "--staged", "--worktree", "--", *sorted(rels), until=until)
    if failed := rebase(shared, until):
        notice += f"; not rebased on the remote: {failed}"
    return Sent(stale=True, notice=notice)


def revision_at(shared: DataRepo, ref: str, rel: str, until: float) -> str:
    """The revision of the decision file *rel* at *ref*; nothing when Git holds no valid one there."""
    shown = shared.git("show", f"{ref}:{rel}", until=until)
    if shown.returncode:
        return ""
    try:
        return parse(shown.stdout).revision
    except DecisionFileError:
        return ""


def last_commit(shared: DataRepo, rel: str, until: float) -> str:
    """The commit that last changed *rel* on `HEAD`."""
    return shared.git("log", "-1", "--format=%H", "HEAD", "--", rel, until=until).stdout.strip()
