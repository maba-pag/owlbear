"""A design pack update's way into ``main`` after its rounds (``pack_run``): its activation and a CI repair's check.

The activation takes exactly the pack the last verdict passed, or the one the owner accepted, with the evidence and
code he approved, into one commit and its pull request (``pack_publish``). An agent's CI repair of that pull request
that changes protected pack content (``pack_repair``) is laid into the candidate, its whole protected content as its
commit holds it (``pack_repair_content``), and checked as the update was, from the golden pages on, before Delivery
pushes it; its findings go to the owner, never back to the updater.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.pack_runs import (
    pack_candidate,
    pack_gates,
    pack_publish,
    pack_repair,
    pack_repair_content,
    pack_rounds,
    pack_run,
    pack_updater,
)
from owlbear_delivery_next.pack_runs.pack_gates import CODE, GOLDEN

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop
    from owlbear_delivery_next.pack_runs.pack_job import Job
    from owlbear_delivery_next.pack_runs.pack_run import Context


def activate(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> str | None:
    """Take exactly the pack the last verdict passed, or the one the owner accepted (TD-256), into ``main``.

    Its changed evidence must be what the owner accepted; a code change waits for his approval first (TD-414). The
    run waits for the owner (None) when publication stops; trying again goes on from where it got.
    """
    package, at = job.live.package.resolve(), job.workspace
    if ctx.repair.phase == "checking" and not _alike(job, c, ctx):
        return None
    edits = pack_run.updater_edits(job, ctx)
    expected = ctx.accepted or (lp.head if lp.ended == "clean" else "")
    if not expected or pack_gates.identity(c, edits) != expected:
        msg = "the candidate is not what the challenger passed or you accepted; run the update again"
        raise pack_run.Stopped(msg)
    if pack_updater.outside(at, ctx.start, c.pins["skills"]) or pack_run.unaccepted(job, ctx):
        msg = "the candidate holds changes you did not accept; run the update again"
        raise pack_run.Stopped(msg)
    if (mark := pack_gates.digest(edits, CODE)) and mark != ctx.code:
        shown = pack_gates.diffs(c, at, package, edits)
        diff = "\n".join(s for p, s in shown.items() if p.startswith(CODE))
        job.wait(ctx, lp, repairing(ctx, [pack_gates.code(job.state["run"], diff, mark)]), "commit")
        return None
    root = Path(ctx.checkout["root"]).resolve()
    edited = [
        n
        for n in c.pins["skills"]
        if pack_run.sha(pack_updater.skill(c, n).read_bytes()) != ctx.baseline[pack_run.skill_path(n)]
    ]
    if ctx.publication is None:  # the edited files join the one commit, checked against the package just before
        job.do(
            "commit", lambda: pack_run.unchanged(package, ctx),
            lambda _o: "the package's files are as the update found", op="unchanged-check",
        )  # fmt: skip
        ctx.publication = _publication(job, ctx, lp, root, [*edited, *edits])
        job.keep(ctx, lp)
    files: dict[str, str | None] = {
        str((package / pack_candidate.MANIFEST).relative_to(root)): c.manifest,
        str((package / pack_candidate.NOTICE).relative_to(root)): c.notice,
    }
    files |= {
        str((package / pack_run.skill_path(n)).relative_to(root)): pack_updater.skill(c, n).read_text("utf-8")
        for n in edited
    }
    files |= {
        str((package / pack_gates.package_path(p)).relative_to(root)): None if d is None else d.decode("utf-8")
        for p, d in edits.items()
    }
    return _published(job, ctx, lp, files)


def _publication(job: Job, ctx: Context, lp: RoundLoop, root: Path, changed: list[str]) -> pack_publish.Publication:
    """The pull request to be: its branch and its body, which says what was changed, judged and decided."""
    edits = pack_run.updater_edits(job, ctx)
    said = f"The updater changed {', '.join(changed)}." if changed else "The updater changed nothing."
    said += " You accepted the changed golden evidence." if pack_gates.digest(edits, GOLDEN) else ""
    said += " You approved the glue's diff, checked with the running code (TD-414)." if ctx.code else ""
    passed = "" if ctx.accepted else " The challenger passed."
    rounds_ = pack_rounds.summary(lp, owner=bool(ctx.accepted))
    listed = ["", "", "Changed files, as the last full round judged them:", *(f"- {x}" for x in ctx.changes)]
    return pack_publish.Publication(
        root=str(root), repository=ctx.checkout["repository"], base=ctx.checkout["base"],
        branch=f"pack/{job.state['run'][:12]}",
        body=f"Golden pages {ctx.golden}. Calibration replay: {ctx.replayed}. {said}{passed} {rounds_}"
        + ("\n".join(listed) if ctx.changes else ""),
    )  # fmt: skip


def republish(job: Job, ctx: Context, lp: RoundLoop) -> str | None:
    """Go on with a publication whose commit exists: GitHub first, never the candidate again (its base moved on).

    A CI repair the owner asked for runs first, and one a host stop interrupted after its commit is pushed once.
    """
    return _published(job, ctx, lp, {})


def _published(job: Job, ctx: Context, lp: RoundLoop, files: dict[str, str | None]) -> str | None:
    pub = ctx.publication
    try:
        pack_repair.repaired(job, ctx)
        merged = pack_publish.publish(job, pub, files, ctx.why, gate=lambda: pack_repair.gate(job, ctx))
    except pack_repair.Asked as exc:
        job.wait(ctx, None, [exc.question], "merge")
        return None
    except pack_repair.Recheck:
        return _rechecked(job, ctx, lp)
    except pack_publish.Held as exc:  # only CI that failed on its own pull request may be repaired
        ctx.repair.stop = pack_repair.failed(exc) if isinstance(exc, pack_publish.CiFailed) else None
        job.hold(ctx, str(exc))
        return None
    by = " by you after rounds without a pass" if ctx.accepted else ""
    return f"activated{by}: merged into main as {merged[:12]} through {pub.url}"


def _rechecked(job: Job, ctx: Context, lp: RoundLoop) -> str | None:
    """Check the agent's committed repair of protected pack content as the update was, from the golden pages on.

    Its new identity passes the golden pages, the replay (reused while the skills are unchanged), a challenger round
    on the whole pack and the owner's gates; only an activation of that identity lets the repair be pushed.
    """
    return pack_run.advance(job, pack_run.rebuilt(job, ctx), ctx, lp)  # its snapshot is laid out first


def laid(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> bool:
    """Lay the repair's whole protected content, as its commit holds it, into the candidate; False when it waits."""
    r, at = ctx.repair, job.workspace
    try:
        snap = pack_repair_content.snapshot(job, ctx, c)
    except design_pack.PackError as exc:
        job.hold(ctx, f"the agent's repair {r.commit[:12]} could not be laid out for its check: {exc}")
        return False
    pack_repair_content.lay(at, snap)
    pack_updater.taken(at, c)
    note = f"Then an agent repaired the pull request's failed CI: {r.summary}"
    ctx.summary = ctx.summary if note in ctx.summary else f"{ctx.summary}\n\n{note}"
    ctx.accepted, lp.ended, ctx.after, ctx.next = "", "", "challenge", "golden"  # no earlier verdict stands for it
    r.laid = r.commit
    job.keep(ctx, lp)
    return True


def _alike(job: Job, c: pack_candidate.Candidate, ctx: Context) -> bool:
    """Whether the checked candidate holds exactly the repair's protected content; else it is laid out again."""
    r = ctx.repair
    try:
        differ = pack_repair_content.unlike(job.workspace, c, pack_repair_content.snapshot(job, ctx, c))
    except design_pack.PackError as exc:
        differ = [str(exc)]
    if differ:
        r.laid = ""  # trying again lays it out and checks it again
        job.hold(ctx, f"the checked candidate is not the agent's repair {r.commit[:12]}: {', '.join(differ[:10])}")
    return not differ


def repairing(ctx: Context, asked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The owner's questions; while a repair is checked, without an undo (no updater follows) and with a discard."""
    if ctx.repair.phase != "checking":
        return asked
    for q in asked:
        kept = [o["id"] for o in q["options"] if o["id"] != pack_rounds.UNDO]
        kept += [pack_rounds.DISCARD] * (pack_rounds.DISCARD not in kept)
        q["options"] = pack_rounds.published(kept, opened=True)
    return asked
