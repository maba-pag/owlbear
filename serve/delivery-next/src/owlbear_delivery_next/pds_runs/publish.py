"""A PDS update's way into ``main`` (#777): one commit and its pull request, and the merge gate on its head.

Only the candidate the challenger passed, or the one the owner accepted, is committed, and only once the audit and the
browser tests passed its pages and every follow-up was continued. Before the merge, once CI passed, the gate reads the
pull request's head: its pin, vendored tree and served files must be the candidate's, and pages that differ from what
was judged are audited, browser-tested and challenged again there; anything they find holds the merge for the owner.
A CI repair of the pages (``repair``) is pushed only once the candidate holding exactly its pages passed them again.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.impeccable_runs import pack_progress, pack_publish, pack_repair, pack_rounds, pack_run
from owlbear_delivery_next.impeccable_runs.pack_run import Stopped
from owlbear_delivery_next.pds_runs import browser, checks, repair, run, tree
from owlbear_delivery_next.pds_runs.context import CANDIDATE, HEAD, MARKER

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop
    from owlbear_delivery_next.pds_runs.context import Context
    from owlbear_delivery_next.pds_runs.job import Job


def publish(job: Job, ctx: Context, lp: RoundLoop) -> str | None:
    """Commit the judged candidate and take it into ``main``; the ending's words, or None while the owner decides.

    Raises:
        Stopped: The candidate is not what was judged or accepted, or a file is not UTF-8 text.
    """
    checking = ctx.repair.phase == "checking"  # an agent's repair of the pages, now judged as the candidate's were
    if ctx.publication is not None and ctx.publication.commit and not checking:
        return republish(job, ctx, lp)
    at = job.workspace / CANDIDATE
    pages = tree.digest(tree.source(at))
    expected = ctx.accepted or (lp.head if lp.ended == "clean" else "")
    if not expected or tree.identity(ctx.candidate, pages) != expected:
        msg = "the candidate is not what the challenger passed or you accepted; run the update again"
        raise Stopped(msg)
    if not ctx.audited == ctx.browsed == pages or not set(ctx.follow_ups) <= set(ctx.followed):
        msg = "the candidate's pages are not the ones the audit and browser tests passed; run the update again"
        raise Stopped(msg)
    if tree.digest(tree.protected(at)) != ctx.candidate:
        msg = "the candidate's release files changed; run the update again"
        raise Stopped(msg)
    if checking:
        return _repaired(job, ctx, lp, pages)
    if ctx.publication is None:
        ctx.source = pages
        ctx.publication = _publication(job, ctx, lp)
        job.keep(ctx, lp)
    edited = job.live.git(at, ["diff", "--name-only", ctx.checkout["base"], "--", *tree.SCOPE]).split()
    raw = tree.protected(at) | {p: (at / p).read_bytes() for p in edited}
    try:
        files: dict[str, str | None] = {p: d.decode("utf-8") for p, d in raw.items()}
    except UnicodeDecodeError as exc:
        msg = f"a file to commit is not UTF-8 text: {exc}; run the update again"
        raise Stopped(msg) from exc
    return _published(job, ctx, lp, files | dict.fromkeys(ctx.removed))


def _publication(job: Job, ctx: Context, lp: RoundLoop) -> pack_publish.Publication:
    """The pull request to be: its branch and a body that says what was changed, judged and decided."""
    judged = "You accepted it after rounds without a pass." if ctx.accepted else "The challenger passed it."
    followed = "; ".join(ctx.follow_ups[k] for k in sorted(ctx.follow_ups))
    said = [
        f"Porsche Design System {ctx.old} to {ctx.version}: the pin, the vendored tree and the served files.",
        f"The updater's sessions: {ctx.sessions}. The deprecation audit and the browser tests passed the pages.",
        f"{judged} {pack_rounds.summary(lp, owner=bool(ctx.accepted))}",
        *([f"You continued without changing these audit follow-ups: {followed}"] if followed else []),
    ]
    return pack_publish.Publication(
        root=ctx.checkout["root"], repository=ctx.checkout["repository"], base=ctx.checkout["base"],
        branch=f"pds/{job.state['run'][:12]}", body="\n\n".join(said),
    )  # fmt: skip


def republish(job: Job, ctx: Context, lp: RoundLoop) -> str | None:
    """Go on with a publication whose commit exists: GitHub first, never the candidate again."""
    return _published(job, ctx, lp, {})


def _repaired(job: Job, ctx: Context, lp: RoundLoop, pages: str) -> str | None:
    """Push the agent's checked repair, once the candidate holds exactly its commit's pages; then merge as before."""
    r = ctx.repair
    try:
        differ = repair.unlike(job, ctx)
    except pack_files.PackError as exc:
        differ = [str(exc)]
    if differ:
        r.laid = ""  # trying again lays it out and checks it again
        job.hold(ctx, f"the checked candidate is not the agent's repair {r.commit[:12]}: {', '.join(differ[:10])}")
        return None
    ctx.source = pages  # the head it is pushed to holds these pages: the merge gate judges them no more
    job.keep(ctx, lp)
    return _published(job, ctx, lp, {})


def _published(job: Job, ctx: Context, lp: RoundLoop, files: dict[str, str | None]) -> str | None:
    pub = ctx.publication
    try:
        pack_repair.repaired(job, ctx)
        merged = pack_publish.publish(job, pub, files, ctx.why, gate=lambda: _gates(job, ctx, lp), marker=MARKER)
    except pack_repair.Asked as exc:
        job.wait(ctx, None, [exc.question], "merge")
        return None
    except pack_repair.Recheck:  # its pages are laid into the candidate and judged again before it is pushed
        return run.advance(job, ctx, lp)
    except pack_publish.Held as exc:  # only CI that failed on its own pull request may be repaired
        ctx.repair.stop = pack_repair.failed(exc) if isinstance(exc, pack_publish.CiFailed) else None
        job.hold(ctx, str(exc))
        return None
    by = " by you after rounds without a pass" if ctx.accepted else ""
    return f"updated to PDS {ctx.version}{by}: merged into main as {merged[:12]} through {pub.url}"


def _gates(job: Job, ctx: Context, lp: RoundLoop) -> None:
    """Before the merge: the owner approved every page change the repairs made, then the head holds what was judged."""
    pack_repair.gate(job, ctx)
    gate(job, ctx, lp)


def gate(job: Job, ctx: Context, lp: RoundLoop) -> None:
    """Before the merge, once CI passed: the pull request's head holds the candidate's release and judged pages.

    Raises:
        pack_publish.Held: Its release files differ, or its changed pages fail the audit, the browser tests or the
            challenger, or a failing browser test does not pass on main either.
    """
    pub, live = ctx.publication, job.live
    root = Path(pub.root)
    head = live.github(root).read_pull_request(pub.repository, pub.number).head_sha
    at = job.workspace / HEAD
    try:
        live.git(root, ["fetch", "--quiet", "origin", f"refs/heads/{pub.branch}"])
        tree.worktree(root, at, head, live.git)
        if tree.digest(tree.protected(at)) != ctx.candidate:
            msg = f"the pull request's head {head[:12]} holds release files other than the candidate's; not merged"
            raise pack_publish.Held(msg)
        pages = tree.digest(tree.source(at))
        if pages == ctx.source:
            return
        _judged(job, ctx, lp, at, head)
        ctx.source = pages
        job.keep(ctx, lp)
    except (pack_files.PackError, browser.Unrunnable, Stopped) as exc:
        msg = f"the merge gate could not judge the head {head[:12]}: {exc}"
        raise pack_publish.Held(msg) from exc
    finally:
        tree.remove(root, at, live.git)


def _noted(job: Job, op: str, result: str, detail: str) -> None:
    """One of the merge gate's judgements, in the Publish phase: never over the candidate's own rounds."""
    job.note("merge", op, result, detail, at=pack_progress.PUBLISH)


def _judged(job: Job, ctx: Context, lp: RoundLoop, at: Path, head: str) -> None:
    """Audit, browser-test and challenge the head's changed pages, as the candidate's were; anything found holds.

    Raises:
        pack_publish.Held: One of them found something.
    """
    v = checks.audited(job, ctx, at)
    unseen = [checks.follow_up(f) for f in v.follow_ups if f.key not in ctx.followed]
    if v.outcome == "stop" or v.findings or unseen:
        said = v.reason if v.outcome == "stop" else "; ".join([*map(checks.finding, v.findings), *unseen])
        _noted(job, "audit", "findings", said[:600])
        msg = f"the pull request's head {head[:12]} changed pages, and the deprecation audit found: {said[:1500]}"
        raise pack_publish.Held(msg)
    _noted(job, "audit", "passed", f"the head {head[:12]}'s pages")
    r = checks.browsed(job, ctx, at)
    _noted(job, "browser", "passed" if r.passed else "findings", r.said())
    if not r.passed:
        msg = f"the pull request's head {head[:12]} changed pages, and the browser tests found: {r.said()}"
        raise pack_publish.Held(msg)
    found, _judged, _changes = pack_run._verdict(checks.challenged(job, ctx, at, lp))  # noqa: SLF001
    _noted(job, "pds-challenge", "findings" if found else "passed", "; ".join(found)[:600] or "no findings")
    if found:
        msg = f"the pull request's head {head[:12]} changed pages, and the challenger found: {'; '.join(found)}"
        raise pack_publish.Held(msg[:2000])
