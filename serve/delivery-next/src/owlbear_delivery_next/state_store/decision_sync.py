"""Publishing decision files without letting Git combine two versions of one (TD-424, TD-419 slice 3).

Every function runs under the data repository's lock. Before a write the checkout catches up with its remote, so an
expected revision is checked against the remote's file. A rejected push is rebased only when the remote changed no
decision file this checkout changed too; when the remote changed a file just committed, the expected revision was
stale: the commit stays in Git unpublished and the save is reported stale. Nothing here undoes Git history or the index.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionFileError
from owlbear_decisions.storage import DECISIONS_DIR, parse
from owlbear_delivery_next.local_system.data_repo import DataRepoError

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

UPSTREAM = "@{upstream}"
PREPARE_TRIES = 2  # a remote that moves once more between catch-up and proof is caught up with once more


@dataclass(frozen=True)
class Sent:
    """What became of one commit and push; `stale` when the remote had changed a committed file first.

    A stale commit stays in Git, its index and worktree as they are, unpublished; the batch stays interrupted.
    """

    stale: bool = False
    notice: str = ""
    uncommitted: bool = False  # the commit failed and `HEAD` did not move: nothing of the batch is in Git
    ambiguous: bool = False  # the outcome cannot be proven from here: the batch stays interrupted until owner recovery


def _decision_file(rel: str) -> bool:
    parts = rel.split("/")
    return len(parts) > 1 and parts[-2] == DECISIONS_DIR and rel.endswith(".md")


def _rev(shared: DataRepo, ref: str, until: float) -> str | None:
    """The commit *ref* names; None when Git could not say, including an unborn or empty answer."""
    said = shared.git("rev-parse", "--verify", "-q", ref, until=until)
    if said.returncode or not said.stdout.strip():
        return None
    return said.stdout.strip()


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


def _on_remote(shared: DataRepo, head: str, until: float) -> bool:
    """Whether the fetched remote branch descends from *head*; unknown counts as not."""
    return not shared.git("merge-base", "--is-ancestor", head, UPSTREAM, until=until).returncode


def proved(shared: DataRepo, head: str, until: float) -> bool:
    """Whether *head* is on the remote, pushing HEAD first when *head* is its ancestor and the remote lacks it.

    The push is never forced: a remote that moved on refuses it and nothing is proved.
    """
    if shared.git("fetch", "-q", until=until).returncode:
        return False
    if _on_remote(shared, head, until):
        return True
    current = _rev(shared, "HEAD", until)
    if current is None or shared.git("merge-base", "--is-ancestor", head, current, until=until).returncode:
        return False
    if shared.git("push", "-q", until=until).returncode or shared.git("fetch", "-q", until=until).returncode:
        return False
    return _on_remote(shared, head, until)


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


def _ahead(shared: DataRepo, until: float) -> bool:
    """Whether the remote branch holds commits the checkout lacks; a checkout with no remote branch is not behind."""
    behind = shared.git("rev-list", "--count", f"HEAD..{UPSTREAM}", until=until)
    return not behind.returncode and behind.stdout.strip() != "0"


def behind_unproved(shared: DataRepo, head: str, until: float) -> bool:
    """Whether *head* is not on the remote and the remote is ahead, so only a rebase could put a batch on it."""
    return not proved(shared, head, until) and _ahead(shared, until)


def prepare(shared: DataRepo, until: float) -> tuple[str, str]:
    """Catch up, then prove HEAD on the remote, before any batch is journalled; every writer runs this first.

    Returns the head to journal and a notice about the catch-up. The head is "" when HEAD is not known, or when the
    remote moved on again before HEAD could be proved; nothing may be written then. When the remote is unreachable
    and not known to be ahead, the head is returned unproved: its commit then stays unpublished, as before.
    """
    try:
        if shared.rebasing(until):
            return (
                "",
                "a rebase is in progress in the checkout, so nothing was written; the owner finishes or aborts it",
            )
    except DataRepoError as exc:  # unknown is not "no rebase": nothing is written
        return "", f"{exc}, so nothing was written"
    notice = ""
    for _ in range(PREPARE_TRIES):
        notice = catch_up(shared, until)
        if (head := _rev(shared, "HEAD", until)) is None:
            return "", "HEAD is not known, so nothing was written"
        if not behind_unproved(shared, head, until):
            return head, (f"not checked against the remote: {notice}" if notice else "")
    return "", "the remote moved on again before HEAD was proved, so nothing was written; save again"


def _ready(shared: DataRepo, until: float) -> tuple[str, Sent | None]:
    """HEAD to commit on; else why nothing is committed: HEAD is unknown, or a rebase is active or unknown.

    An unknown rebase is not "no rebase", so it leaves the batch interrupted rather than uncommitted.
    """
    if (head := _rev(shared, "HEAD", until)) is None:
        return "", Sent(notice="HEAD is not known, so nothing was committed", ambiguous=True)
    try:
        if shared.rebasing(until):
            return "", Sent(notice="a rebase is in progress, so nothing was committed", uncommitted=True)
    except DataRepoError as exc:
        return "", Sent(notice=f"{exc}, so nothing was committed", ambiguous=True)
    return head, None


def publish(shared: DataRepo, paths: list[Path], message: str, until: float, head: str) -> Sent:
    """Commit *paths* alone and push; a rejected push never rebases over a remote change of a decision file here.

    *head* is the batch's journalled head, proved on the remote by `prepare` before anything was written. A rebase
    refuses to run unless it is on the remote, so a rebase never rewrites a commit the batch's proof depends on. A
    failed commit is known only when HEAD did not move; when it moved, the commit is accepted only if it is provably
    this call's own and holds the files as they are, so a lost commit is never guessed from a moved head.
    """
    before, busy = _ready(shared, until)
    if busy is not None:  # nothing is committed unless HEAD is read, and never while a rebase is active or unknown
        return busy
    rels = {p.relative_to(shared.root).as_posix() for p in paths}
    failed = shared.commit(paths, message, until)
    now = _rev(shared, "HEAD", until)
    if failed and now is not None and now == before:
        return Sent(notice=failed, uncommitted=True)
    made = _ours(shared, before, rels, until)
    if failed and not (made and _in_head(shared, paths, until)):
        return Sent(notice=failed, ambiguous=True)
    pushed = shared.git("push", "-q", until=until)
    if pushed.returncode == 0:
        return Sent()
    if refused := _rejected(shared, rels, pushed.stderr, until, own=bool(made)):
        return refused
    return _rebase_push(shared, head, until)


def _in_head(shared: DataRepo, paths: list[Path], until: float) -> bool:
    """Whether HEAD holds each of *paths* exactly as the worktree does, a file missing from both included."""
    for path in paths:
        said = shared.git("show", f"HEAD:{path.relative_to(shared.root).as_posix()}", until=until)
        held = None if said.returncode else said.stdout.encode("utf-8")
        if held != (path.read_bytes() if path.exists() else None):
            return False
    return True


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


def _rebase_failed(shared: DataRepo, where: str, failed: str, until: float) -> Sent:
    try:
        left = shared.rebasing(until)
    except DataRepoError as exc:  # unknown whether Git is mid-rebase: ambiguous, never "no rebase"
        return Sent(notice=f"{where}, but it could not be rebased on the remote: {failed}; {exc}", ambiguous=True)
    return Sent(notice=f"{where}, but it could not be rebased on the remote: {failed}; push it by hand", ambiguous=left)


def _rejected(shared: DataRepo, rels: set[str], why: str, until: float, *, own: bool) -> Sent | None:
    """The outcome of a refused push that cannot be rebased over; None when the remote can be rebased on."""
    where = f"saved and committed in {shared.root}"
    if shared.git("fetch", "-q", until=until).returncode or (sides := _diverged(shared, until)) is None:
        return Sent(notice=f"{where}, but the push failed: {why.strip()[:200]}")
    ours, theirs = sides
    if stale := theirs & rels:
        ids = ", ".join(sorted(Path(r).stem for r in stale))
        notice = (
            f"another checkout changed {ids} first, so this save is stale: its commit stays in Git unpublished, "
            "and nothing in Git or the index is undone; the batch stays interrupted for the owner to finish or abandon"
        )
        if not own:
            notice += "; HEAD moved past this save's commit, which is not provably its own: fix by hand"
        return Sent(stale=True, notice=notice)
    if both := ours & theirs:
        listed = ", ".join(sorted(both))
        return Sent(notice=f"{where}, but not published: {listed} changed here and on the remote; the owner decides")
    return None


def _rebase_push(shared: DataRepo, head: str, until: float) -> Sent:
    """Rebase on the remote and push again; a rebase that would rewrite *head*, the batch's proof, is refused."""
    where = f"saved and committed in {shared.root}"
    if not _on_remote(shared, head, until):  # a rebase would rewrite the batch's head: refused, the batch stays
        return Sent(
            notice=f"{where}, but {head[:12]} is not on the remote, so it is not rebased; the owner resolves it",
            ambiguous=True,
        )
    if failed := shared.rebase(until):
        return _rebase_failed(shared, where, failed, until)
    sent = shared.git("push", "-q", until=until)
    if sent.returncode:
        return Sent(notice=f"{where}, but the push failed: {sent.stderr.strip()[:200]}")
    return Sent()


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
