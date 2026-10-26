"""Publishing decision files without letting Git combine two versions of one (TD-424, TD-419 slice 3).

Every function runs under the data repository's lock. Before a write the checkout catches up with its remote, so an
expected revision is checked against the remote's file. A rejected push is rebased only when the remote changed no
decision file this checkout changed too; when the remote changed a file just committed, the expected revision was
stale: the commit stays in Git unpublished and the save is reported stale. Nothing here undoes Git history or the index.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionFileError
from owlbear_decisions.storage import DECISIONS_DIR, parse
from owlbear_delivery_next.local_system.data_repo import Committed, DataRepoError
from owlbear_delivery_next.state_store import decision_batch
from owlbear_delivery_next.state_store.decision_target import Continuation, Target, push_commit, target

if TYPE_CHECKING:
    from collections.abc import Callable

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
    # The commit HEAD must be for the batch to land: the one this publication proved and sent, or kept local when the
    # push failed; "" when none is known. Completion proves that very commit, never a later one at HEAD.
    commit: str = ""
    goal: Target | None = None  # the target *commit* went to: a continuation goes only there, never re-read


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


def _on_remote(shared: DataRepo, head: str, until: float, tracking: str = UPSTREAM) -> bool:
    """Whether the fetched remote branch (*tracking*) descends from *head*; unknown counts as not."""
    return not shared.git("merge-base", "--is-ancestor", head, tracking, until=until).returncode


def proved(shared: DataRepo, head: str, until: float, cont: Continuation | None = None) -> bool:
    """Whether *head* is on the remote, pushing *head* itself first when it is HEAD's ancestor and the remote lacks it.

    Only *head*'s own commit is sent (`push_commit`), never HEAD: a commit made after it, a batch's or an owner's,
    is not published by proving the head it grew from. It goes to the remote branch the checkout followed when this
    began, read once, or, for a continuation (*cont*), to the one its publication went to, never read again. The push
    is never forced: a remote that moved on refuses it and nothing is proved.
    """
    goal = cont.goal if cont else target(shared, until)
    tracking = goal.tracking if goal else UPSTREAM
    if shared.git("fetch", "-q", until=until).returncode:
        return False
    if _on_remote(shared, head, until, tracking):
        return True
    current = _rev(shared, "HEAD", until)
    if current is None or shared.git("merge-base", "--is-ancestor", head, current, until=until).returncode:
        return False
    if push_commit(shared, head, goal, until) or shared.git("fetch", "-q", until=until).returncode:
        return False
    return _on_remote(shared, head, until, tracking)


def rebase(shared: DataRepo, until: float, guard: Callable[[], str] | None = None) -> str:
    """Rebase on the fetched remote unless both sides changed one decision file; why it did not, else nothing.

    *guard*, a continuation's, runs after every probe and immediately before the rebase: what it refuses, nothing
    is rebased.
    """
    if (sides := _diverged(shared, until)) is None:
        return "Git cannot compare the checkout with its remote"
    if both := sides[0] & sides[1]:
        return f"{', '.join(sorted(both))} changed here and on the remote; the owner resolves it"
    if guard is not None and (why := guard()):
        return why
    return shared.rebase(until)


def catch_up(shared: DataRepo, until: float, guard: Callable[[], str] | None = None) -> str:
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
    return rebase(shared, until, guard)


def _ahead(shared: DataRepo, until: float) -> bool:
    """Whether the remote branch holds commits the checkout lacks; a checkout with no remote branch is not behind."""
    behind = shared.git("rev-list", "--count", f"HEAD..{UPSTREAM}", until=until)
    return not behind.returncode and behind.stdout.strip() != "0"


def behind_unproved(shared: DataRepo, head: str, until: float, cont: Continuation | None = None) -> bool:
    """Whether *head* is not on the remote and the remote is ahead, so only a rebase could put a batch on it."""
    return not proved(shared, head, until, cont) and _ahead(shared, until)


def prepare(shared: DataRepo, until: float, cont: Continuation | None = None) -> tuple[str, str]:
    """Catch up, then prove HEAD on the remote, before any batch is journalled; every writer runs this first.

    Returns the head to journal and a notice about the catch-up. The head is "" when HEAD is not known, or when the
    remote moved on again before HEAD could be proved; nothing may be written then. When the remote is unreachable
    and not known to be ahead, the head is returned unproved: its commit then stays unpublished, as before.

    *cont*, for a continuation of a publication, is the commit it landed and the target it went to: before the
    catch-up, immediately before its rebase and when HEAD is read, the checkout must still follow that target and
    HEAD be that commit or one already on its remote branch. An owner's commit, or a branch checked out since, even at
    the same commit, is then never rebased, pushed to or built on; nothing is written, and nothing is undone.
    """
    try:
        if shared.rebasing(until):
            return (
                "",
                "a rebase is in progress in the checkout, so nothing was written; the owner finishes or aborts it",
            )
    except DataRepoError as exc:  # unknown is not "no rebase": nothing is written
        return "", f"{exc}, so nothing was written"
    notice, guard = "", (lambda: _stray(shared, cont, until)[1]) if cont else None
    for _ in range(PREPARE_TRIES):
        if guard and (stray := guard()):
            return "", stray
        notice = catch_up(shared, until, guard)
        head, stray = _stray(shared, cont, until) if cont else (_rev(shared, "HEAD", until), "")
        if head is None or stray:
            return "", stray or "HEAD is not known, so nothing was written"
        if not behind_unproved(shared, head, until, cont):
            return head, (f"not checked against the remote: {notice}" if notice else "")
    return "", "the remote moved on again before HEAD was proved, so nothing was written; save again"


def _stray(shared: DataRepo, cont: Continuation, until: float) -> tuple[str | None, str]:
    """HEAD, read after the target, and why a continuation goes no further; "" when it may go on.

    It goes no further when the checkout left its target, or HEAD is neither its commit nor on that target's remote
    branch as last fetched, or is unknown.
    """
    if target(shared, until) != cont.goal:
        notice = f"the checkout left the branch {cont.own[:12]} was published from, so nothing more was written"
        return None, f"{notice}; check it"
    head, tracking = _rev(shared, "HEAD", until), cont.goal.tracking if cont.goal else UPSTREAM
    if head and (head == cont.own or _on_remote(shared, head, until, tracking)):
        return head, ""
    notice = f"HEAD moved past this save's commit {cont.own[:12]} to one not its own, so nothing more was written"
    return head, f"{notice}; check it"


def _ready(shared: DataRepo, until: float) -> tuple[str, Sent | None]:
    """HEAD to commit on; else why nothing is committed: HEAD is unknown, or a rebase is active or unknown.

    An active rebase is ambiguous too: the owner may have committed the batch while the rebase was paused, so "no
    commit by us" proves nothing about HEAD or the index. The batch stays interrupted for the owner to settle.
    """
    if (head := _rev(shared, "HEAD", until)) is None:
        return "", Sent(notice="HEAD is not known, so nothing was committed", ambiguous=True)
    try:
        if shared.rebasing(until):
            return "", Sent(notice="a rebase is in progress, so nothing was rolled back", ambiguous=True)
    except DataRepoError as exc:
        return "", Sent(notice=f"{exc}, so nothing was committed", ambiguous=True)
    return head, None


def publish(  # noqa: PLR0913, PLR0917 - a flag round's publication also carries its save's continuation
    shared: DataRepo, paths: list[Path], message: str, until: float, head: str, cont: Continuation | None = None
) -> Sent:
    """Commit *paths* alone and push; a rejected push never rebases over a remote change of a decision file here.

    *head* is the batch's journalled head, proved on the remote by `prepare` before anything was written. A rebase
    refuses to run unless it is on the remote, so a rebase never rewrites a commit the batch's proof depends on. A
    failed commit is known only when HEAD did not move; when it moved, the commit is accepted only if it is provably
    this call's own and holds the batch, so a lost commit is never guessed from a moved head.

    Within a journalled batch nothing incomplete reaches the remote, which other clones read with no journal of their
    own: every file the journal names must hold its after image before the commit, and the commit pushed, the one
    made or the one a rebase made of it, must hold every after image too, checked on that pinned commit before its
    push. Otherwise the commit, if made, stays local and unpushed and the batch stays interrupted; nothing is undone.
    A continuation's publication (*cont*) goes only to its save's target: a checkout following another is refused.
    """
    goal = target(shared, until)  # where this goes, read with its proof: a later checkout never retargets it
    if cont is not None and goal != cont.goal:
        notice = "the checkout left the branch this save was published from, so nothing more is committed; check it"
        return Sent(notice=notice, ambiguous=True)
    before, busy = _ready(shared, until)
    rels = {p.relative_to(shared.root).as_posix() for p in paths}
    # nothing is committed unless HEAD is read, never while a rebase is active or unknown, nor before the batch is whole
    rows, refused = (None, busy) if busy is not None else _journalled(shared, rels, before)
    if refused is not None:
        return refused
    said = shared.commit(paths, message, until)
    failed, created = str(said), said.commit if isinstance(said, Committed) else ""  # no identity: none is trusted
    created = None if getattr(said, "unnamed", False) else created  # a commit made that Git did not name
    now = _rev(shared, "HEAD", until)
    made = _ours(shared, before, rels, until)
    if stop := _failed(shared, (failed, before, now, made, created)) or _unproved(shared, now, rows, paths, until):
        return stop
    pushed = push_commit(shared, now, goal, until) if now else "HEAD is not known"  # `_unproved` refused that
    if not pushed:
        return Sent(commit=now, goal=goal)
    if refused := _rejected(shared, rels, pushed, until, own=bool(made)):
        return _bound(refused, now, goal)
    return _rebase_push(shared, head, until, (rows, paths, rels, made, now, goal))


def _bound(sent: Sent, commit: str | None, goal: Target | None) -> Sent:
    """*sent*, naming *commit* and its *goal* as what the batch lands on, unless it is a refusal of the batch."""
    good = not (sent.stale or sent.ambiguous or sent.uncommitted) and commit
    return replace(sent, commit=commit, goal=goal) if good else sent


type Rows = dict[str, bytes] | None  # the batch's after images by path, or None outside a journalled batch


def _failed(shared: DataRepo, commit: tuple[str, str, str | None, str, str | None]) -> Sent | None:
    """Why the commit is not pushed, with HEAD proved to be this call's own commit or the head it began on.

    A failed commit is known only when HEAD did not move; when it moved, nothing names the commit made, if any, so
    nothing is pushed, however much a commit there looks like this call's. A commit that succeeded names the commit it
    made (`Committed.commit`): when it made none, HEAD must still be the head it began on; when it made one, HEAD must
    be that very commit, also proved this call's own; when Git did not name it, nothing is pushed. An owner's commit
    made meanwhile, even one keeping every file, is never pushed.
    """
    failed, before, now, made, created = commit
    if failed and now is not None and now == before:
        return Sent(notice=failed, uncommitted=True)
    if failed:
        return Sent(notice=f"{failed}; HEAD moved meanwhile, so nothing is pushed; check it", ambiguous=True)
    if created is None:
        notice = f"saved and committed in {shared.root}, but Git did not name the commit it made, so nothing is pushed"
        return Sent(notice=f"{notice}; check it", ambiguous=True)
    if now is not None and now in ({before} if not created else {created} & {made}):
        return None
    notice = f"saved in {shared.root}, but HEAD moved past this save's commit to one not provably its own, so nothing"
    return Sent(notice=f"{notice} is pushed; check it", ambiguous=True)


def _journalled(shared: DataRepo, rels: set[str], before: str) -> tuple[Rows, Sent | None]:
    """The pending batch's after images, once every one of them is in its file; else why nothing is committed.

    Outside a batch there is nothing journalled to hold. A path the journal does not name is never committed for it.
    Within one, *before*, HEAD as `_ready` read it, must still be the batch's journalled head: a commit the owner made
    since, even one holding every after image, is never adopted as this batch's base or pushed with it.
    """
    batch = decision_batch.pending(shared)  # a journal that cannot be read raises: unknown is never "no batch"
    if batch is None:
        return None, None
    rows = {rel: after for rel, _, after in batch.files}
    if before != batch.head:
        notice = f"HEAD moved past the batch's head {batch.head[:12]}, so nothing was committed or pushed; check it"
        return rows, Sent(notice=notice, ambiguous=True)
    if not rels <= rows.keys():
        notice = "a file to commit is not in the batch's journal, so nothing was committed"
        return rows, Sent(notice=notice, ambiguous=True)
    root = shared.root
    held = all(
        decision_batch.plain_in_checkout(root, root / rel) and _bytes(root / rel) == data for rel, data in rows.items()
    )
    if held and decision_batch.still_plain(root, [root / rel for rel in rows]):
        return rows, None
    notice = "not every file of the batch holds its journalled image, so nothing was committed or pushed"
    return rows, Sent(notice=notice, ambiguous=True)


def _bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _holds(shared: DataRepo, commit: str, rows: Rows, paths: list[Path], until: float) -> bool:
    """Whether *commit* holds every after image of the batch; outside a batch, each of *paths* as the worktree does."""
    by_path = {p.relative_to(shared.root).as_posix(): _bytes(p) for p in paths}
    expected = by_path if rows is None else dict(rows)
    for rel, data in expected.items():
        said = shared.git("show", f"{commit}:{rel}", until=until)
        if (None if said.returncode else said.stdout.encode("utf-8")) != data:
            return False
    return True


def _unproved(shared: DataRepo, commit: str | None, rows: Rows, paths: list[Path], until: float) -> Sent | None:
    """Why *commit* is not pushed: it does not hold the batch, or HEAD already moved from it; else nothing.

    The push then names *commit* itself (`push_commit`), so what is sent is exactly the commit checked here, even if
    HEAD moves after this; HEAD having moved already is refused only so that a moved checkout is reported.
    """
    where = f"saved and committed in {shared.root}"
    if commit is None or not _holds(shared, commit, rows, paths, until):
        notice = f"{where}, but the commit does not hold the batch as journalled, so it is not pushed; check it"
        return Sent(notice=notice, ambiguous=True)
    if _rev(shared, "HEAD", until) != commit:
        return Sent(notice=f"{where}, but HEAD moved before the push, so it is not pushed; check it", ambiguous=True)
    return None


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


def _not_rebased(
    shared: DataRepo, where: str, head: str, refused: tuple[str | None, Target | None], until: float
) -> Sent | None:
    """Why nothing is rebased; then an owner's commit or branch switch made meanwhile is never replayed or rewritten.

    *refused* is the commit whose push was refused and the target it went to. The batch's *head* must be on that
    target's remote branch, or a rebase would rewrite it; the checkout must still be on the target's branch, following
    the same remote branch; and HEAD, read after those probes and immediately before the rebase, must still be that
    commit.
    """
    sent, goal = refused
    if goal is None or not _on_remote(shared, head, until, goal.tracking):
        notice = f"{where}, but {head[:12]} is not on the remote, so it is not rebased; the owner resolves it"
        return Sent(notice=notice, ambiguous=True)
    if target(shared, until) != goal:
        notice = f"{where}, but the checkout left the branch it was published from, so nothing is rebased; check it"
        return Sent(notice=notice, ambiguous=True)
    if sent is None or _rev(shared, "HEAD", until) != sent:
        notice = f"{where}, but HEAD moved past the commit whose push was refused, so nothing is rebased; check it"
        return Sent(notice=notice, ambiguous=True)
    return None


def _rebase_push(
    shared: DataRepo,
    head: str,
    until: float,
    batch: tuple[Rows, list[Path], set[str], str, str | None, Target | None],
) -> Sent:
    """Rebase on the remote and push again; a rebase that would rewrite *head*, the batch's proof, is refused.

    HEAD must still be the commit whose push was refused, on the branch the publication began on, read after the remote
    probes and immediately before the rebase: an owner's commit or branch switch made meanwhile is never replayed or
    rewritten. Afterwards the rebased commit must be provably this save's own: its one commit replayed directly on the
    remote branch the publication began with and changing only the batch's files, or, for a save that committed
    nothing, that remote branch itself. It is checked to hold the batch, and that very commit is what is pushed, to
    that same remote branch. An owner's commit made after the rebase is never pushed.
    """
    where = f"saved and committed in {shared.root}"
    rows, paths, rels, made, sent, goal = batch
    if refused := _not_rebased(shared, where, head, (sent, goal), until):
        return refused
    if failed := shared.rebase(until):
        return _bound(_rebase_failed(shared, where, failed, until), sent, goal)  # never aborted: HEAD must be *sent*
    rebased, upstream = _rev(shared, "HEAD", until), _rev(shared, goal.tracking, until) if goal else None
    own = _ours(shared, upstream, rels, until) if made and upstream else ""
    if rebased is None or rebased not in {own or upstream, upstream}:  # upstream itself: nothing of ours left to send
        notice = f"{where}, but after the rebase HEAD is not provably this save's commit, so it is not pushed"
        return Sent(notice=f"{notice}; check it", ambiguous=True)
    if unproved := _unproved(shared, rebased, rows, paths, until):
        return unproved
    if failed := push_commit(shared, rebased, goal, until):
        return Sent(notice=f"{where}, but the push failed: {failed}", commit=rebased, goal=goal)
    return Sent(commit=rebased, goal=goal)


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
