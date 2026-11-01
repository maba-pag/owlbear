"""A PDS update's resumable run (#777): the candidate, its gates and rounds, and the questions for the owner.

The candidate is a worktree of the pinned base with the release written in (``tree``). Its deprecation audit and
browser tests gate it: findings and the failures it caused go to a fresh updater, which edits a copy of the pages, and
both gates run again on its edits; neither is ever waived. A challenger then judges the release's evidence and every
page edit, in ``pack_rounds``' rounds. The audit's manual follow-ups go to the owner, never the updater. Each updater
session counts against the round policy. Publication goes through ``publish``. An agent's CI repair of the pages
(``repair``) is laid into the candidate and judged the same way, as one more round, before Delivery pushes it: nothing
goes to the updater then; an audit or browser test that does not pass drops the repair and gives the owner the CI stop
again, and challenger findings ask him whether to push it unreviewed.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import dispute_tools, tools
from owlbear_delivery_next.change_contracts.round_records import PDS, RoundLoop
from owlbear_delivery_next.impeccable import pack_files, pack_git
from owlbear_delivery_next.impeccable_runs import pack_activation, pack_publish, pack_repair, pack_rounds, pack_run
from owlbear_delivery_next.impeccable_runs.pack_run import Stopped
from owlbear_delivery_next.pds_runs import checks, diff, pin, publish, repair, sessions, tree
from owlbear_delivery_next.pds_runs.context import CANDIDATE, NEXT, UPDATER, Action, Context
from owlbear_delivery_next.settings import rounds
from owlbear_delivery_next.workflow_steps import sessions as step_sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.pds_runs.job import Job


class Dropped(Exception):  # noqa: N818 - how a repair's failed check gives the owner its CI stop again
    """The agent's CI repair did not pass the audit or the browser tests again: it is never pushed."""


def number(version: str) -> tuple[int, ...]:
    """A release version as numbers, to order two."""
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def notice(job: Job) -> str:
    """The latest release on npm, when newer than the installed pin.

    Raises:
        Stopped: npm was not reached or named no version, or the pin is current.
    """
    try:
        latest = json.loads(job.live.fetch(f"{pin.REGISTRY}/latest", pin.SECONDS))["version"]
    except OSError as exc:
        msg = f"npm was not reached for {pin.NAME}: {exc}; try again when online"
        raise Stopped(msg) from exc
    except (ValueError, KeyError, TypeError) as exc:
        msg = f"npm's answer for {pin.NAME} names no version"
        raise Stopped(msg) from exc
    if not (isinstance(latest, str) and pin.VERSION.fullmatch(latest)):
        msg = f"npm's answer names no version: {str(latest)[:60]}"
        raise Stopped(msg)
    installed = pin.read(job.live.package.resolve()).version
    if number(latest) <= number(installed):
        msg = f"up to date: PDS {installed} is npm's latest release"
        raise Stopped(msg, current=True)
    return latest


def candidate(job: Job) -> Path:
    """The run's candidate worktree."""
    return job.workspace / CANDIDATE


def identity(ctx: Context, at: Path) -> str:
    """The whole candidate's identity at *at*: its fixed ``C`` and its pages' ``S``."""
    return tree.identity(ctx.candidate, tree.digest(tree.source(at)))


def prepare(job: Job, version: str) -> tuple[Context, pin.Release, bytes | None]:
    """The candidate: a worktree of the pinned base with *version* written in; its context, release and old evidence.

    Raises:
        Stopped: The base already pins *version* or newer, or the written files differ from their pin.
        pack_files.PackError: The checkout cannot publish, or a git command failed.
        pin.PinError: The release was not downloaded or failed its checks.
    """
    live = job.live
    src = pack_git.source(live.package.resolve(), live.git)  # before any download: a checkout that cannot publish stops
    pack_publish.preflight(live.github(src.root), src.repository)
    release = pin.release(version, live.fetch)
    job.workspace.mkdir(parents=True, exist_ok=True)
    at = tree.worktree(src.root, candidate(job), src.base, live.git)
    package = at / pin.PREFIX
    old = pin.read(package)
    if number(old.version) >= number(version):
        msg = f"up to date: main already pins PDS {old.version}"
        raise Stopped(msg, current=True)
    evidence = package / pin.TREE / diff.DEPRECATIONS
    before = evidence.read_bytes() if evidence.is_file() else None
    files = release.files(old)
    tree.lay(at, files)
    if differs := pin.verify(package):
        msg = f"the candidate's files differ from their pin: {'; '.join(differs[:5])}"
        raise Stopped(msg)
    ctx = Context(
        version=version, old=old.version, why=f"PDS: {old.version} to {version}", diff="",
        checkout={"root": str(src.root), "repository": src.repository, "base": src.base},
        candidate=tree.digest(tree.protected(at)), removed=sorted(p for p, d in files.items() if d is None),
        vendored=_vendored(old.files, release.pin().files),
    )  # fmt: skip
    return ctx, release, before


def _vendored(old: dict[str, str], new: dict[str, str]) -> str:
    """The pinned files the release adds, changes and removes, by package path."""
    rows = [
        f"{'added' if p not in old else 'removed' if p not in new else 'changed'}: {p}"
        for p in sorted(old.keys() | new.keys())
        if old.get(p) != new.get(p)
    ]
    return "\n".join(rows[:400]) + (f"\n… and {len(rows) - 400} more" if len(rows) > 400 else "")  # noqa: PLR2004


def begin(job: Job, ctx: Context) -> str | None:
    """Pin the run's loop and run from the audit; the ending's words, or None while waiting."""
    lp = RoundLoop(subject=PDS, policy=rounds.policy(job.store.settings(), PDS, "updater"))
    job.keep(ctx, lp)
    return advance(job, ctx, lp)


def unchanged(job: Job, ctx: Context) -> None:
    """Check that the waiting run's candidate is still there with its release as made.

    Raises:
        Stopped: It is gone or its pin, vendored tree or served files changed.
    """
    at = candidate(job)
    if not (at / pin.PREFIX / pin.PIN).is_file() or tree.digest(tree.protected(at)) != ctx.candidate:
        msg = "the run's candidate is gone or its release files changed; run the update again"
        raise Stopped(msg)


def advance(job: Job, ctx: Context, lp: RoundLoop) -> str | None:
    """Run the actions from the context's next one until the owner is asked or the update is merged.

    Raises:
        Stopped: An action ended the run.
    """
    while True:
        if (r := ctx.repair).phase == "checking" and r.laid != r.commit and not _laid(job, ctx, lp):
            return None  # a repair is judged only on its own pages, laid out again after a host stop
        if ctx.next == "wait":
            asked, stage = _asked(job, ctx, lp)
            job.wait(ctx, lp, pack_activation.repairing(ctx, asked), stage)
            return None
        if ctx.next == "publish":
            return publish.publish(job, ctx, lp)
        try:
            ctx.next = _step(job, ctx, lp)
        except Dropped as exc:
            job.hold(ctx, str(exc))
            return None
        job.keep(ctx, lp)


def _step(job: Job, ctx: Context, lp: RoundLoop) -> Action:
    """The context's next action short of the owner and publication; what follows it.

    Raises:
        Stopped: The action ended the run.
        Dropped: A checked repair failed its audit or browser tests.
    """
    match ctx.next:
        case "audit":
            return _gated(ctx, lambda: _audit(job, ctx))
        case "browser":
            return _gated(ctx, lambda: _browser(job, ctx))
        case "update":  # a repair's challenger findings go to the owner, never the updater
            return "wait" if ctx.repair.phase == "checking" else _update(job, ctx, lp)
        case "challenge" | "recheck":
            return _challenge(job, ctx, lp, recheck=ctx.next == "recheck")
        case "reconsider":
            return _reconsider(job, ctx, lp)
        case other:
            msg = f"the run's next action {other!r} is unknown; run the update again"
            raise Stopped(msg)


def _laid(job: Job, ctx: Context, lp: RoundLoop) -> bool:
    """Lay the repair's pages, as its commit holds them, into the candidate for their check; False when it waits."""
    r = ctx.repair
    try:
        repair.lay(job, ctx)
    except pack_files.PackError as exc:
        job.hold(ctx, f"the agent's repair {r.commit[:12]} could not be laid out for its check: {exc}")
        return False
    note = f"Then an agent repaired the pull request's failed CI: {r.summary}"
    ctx.summary = ctx.summary if note in ctx.summary else f"{ctx.summary}\n\n{note}"
    ctx.accepted, lp.ended, ctx.after, ctx.next = "", "", "challenge", "audit"  # no earlier verdict stands for it
    ctx.audited = ctx.browsed = ""
    r.laid = r.commit
    job.identified(identity(ctx, candidate(job)))
    job.keep(ctx, lp)
    return True


def _gated(ctx: Context, action: Callable[[], Action]) -> Action:
    """The audit or the browser tests; while a repair is checked, anything but their pass drops it.

    Raises:
        Dropped: They found something in the repair's pages, or stopped on them.
    """
    if ctx.repair.phase != "checking":
        return action()
    try:
        then = action()
    except Stopped as exc:
        raise Dropped(_dropped(ctx, str(exc))) from exc
    if then == "update":
        found = ctx.findings or [f.removeprefix("- ") for f in ctx.failures if f.startswith("- ")]
        raise Dropped(_dropped(ctx, "; ".join(found)))
    return then


def _dropped(ctx: Context, why: str) -> str:
    """Drop the checked repair, never pushed; the owner's words, with the CI stop it started from."""
    r = ctx.repair
    made, ctx.findings, ctx.failures = r.commit[:12], [], []
    r.phase, r.commit, r.laid = "", "", ""
    stop = f"CI failed at {r.stop.head[:12]}: {', '.join(c['name'] for c in r.stop.failed)}; " if r.stop else ""
    more = "have an agent try again, " if pack_repair.offered(ctx) else ""
    said = f"the agent's repair {made} failed its check and was not pushed: {why[:1500]}"
    return f"{stop}{said}. Try again, {more}or discard"


def _audit(job: Job, ctx: Context) -> Action:
    """The deprecation audit of the candidate's pages: findings to the updater, follow-ups to the owner.

    Raises:
        Stopped: The audit stopped: no usable report, a gap it disclosed or another release.
    """
    at = candidate(job)

    def work() -> Any:  # noqa: ANN401 - audit.Verdict
        v = checks.audited(job, ctx, at)
        if v.outcome == "stop":
            msg = f"audit: {v.reason}"
            raise Stopped(msg)
        return v

    v = job.do(
        "audit", work, lambda v: f"{len(v.findings)} finding(s)" if v.findings else v.outcome, op="audit",
        identity=identity(ctx, at), judged=lambda v: "passed" if v.outcome == "pass" else "findings",
    )  # fmt: skip
    ctx.findings = [checks.finding(f) for f in v.findings]
    ctx.follow_ups = {f.key: checks.follow_up(f) for f in v.follow_ups}
    if v.outcome == "findings":
        ctx.audited = ""
        return "update"
    ctx.audited = tree.digest(tree.source(at))
    return "browser" if set(ctx.follow_ups) <= set(ctx.followed) else "wait"


def _browser(job: Job, ctx: Context) -> Action:
    """The browser tests on the candidate, once per page identity: failures it caused go to the updater.

    A failure passing a rerun on main and on the candidate is a flake: the gate passes and names it.

    Raises:
        Stopped: They cannot run, ran nothing, failed otherwise, or a failing test fails on main as well.
    """
    at = candidate(job)
    pages, ident = tree.digest(tree.source(at)), identity(ctx, at)
    if ctx.browsed == pages:
        job.note("browser", "browser", "reused", "the pages are as the browser tests passed them", ident)
        return ctx.after

    r = job.do("browser", lambda: checks.browsed(job, ctx, at), lambda r: r.said(), op="browser", identity=ident,
               judged=lambda r: "passed" if r.passed else "findings")  # fmt: skip
    if r.passed:
        ctx.browsed, ctx.failures = pages, []
        return ctx.after
    ctx.browsed = ""
    head, said = ("What the report says of them:", r.told) if r.told else ("Their output's tail:", r.output[-6000:])
    ctx.failures = [f"- {i}" for i in r.failed] + ["", head, "```", said, "```"]
    return "update"


def _update(job: Job, ctx: Context, lp: RoundLoop) -> Action:
    """One fresh updater session on a copy of the candidate's pages; its page edits taken back, then the audit again.

    Raises:
        Stopped: The sessions the round policy allows are spent, or the updater changed what it may not.
    """
    allowed = lp.policy.max_rounds + lp.extra
    if ctx.sessions >= allowed:
        left = [*ctx.findings, *ctx.failures[:8], *(f"{f.id}: {f.text}" for f in pack_rounds.addressing(lp))]
        msg = f"the update spent its {allowed} updater session(s) with these still open: {'; '.join(left)}"
        raise Stopped(msg[:2000])
    at, cand = job.workspace / UPDATER, candidate(job)
    start = tree.copy(cand, at, job.live.git)
    answering = bool(pack_rounds.addressing(lp))
    text = sessions.update_message(
        ctx.version, ctx.old, findings=ctx.findings, failures=ctx.failures, rounds=pack_rounds.updater_lines(lp),
        earlier=ctx.summary, evidence=ctx.diff,
    )  # fmt: skip
    cfg = sessions.updater(
        job.store.settings(), at, checks.skills(cand), text, memory=step_sessions.memory(job.store),
        keys=(pack_rounds.rejectable(lp), pack_rounds.settled(lp)),
    )  # fmt: skip
    result = job.do(
        "update", lambda: sessions.updated(job.live.session(job.store, cfg)), lambda r: r.summary, op="pds-update",
        round_=lp.round + 1, judged=lambda _r: "completed",
    )  # fmt: skip
    ctx.sessions += 1
    ctx.summary = f"{ctx.summary}\n\n{result.summary}".strip()
    try:
        tree.taken(at, start, cand)
    except tree.Outside as exc:
        raise Stopped(str(exc)) from exc
    ident = identity(ctx, cand)
    job.identified(ident)
    if answering:  # it answered the challenger's findings: the rounds go on from them
        ctx.after = NEXT[pack_rounds.revised(lp, {r.finding: r.reason for r in result.rejected}, ident)]
    ctx.findings, ctx.failures = [], []
    return "audit"


def _challenge(job: Job, ctx: Context, lp: RoundLoop, *, recheck: bool) -> Action:
    """One challenger round on the whole candidate, or a check of the updater's rejections only."""
    at = candidate(job)
    ident = identity(ctx, at)

    def challenge() -> tuple[list[str], str]:
        said = checks.challenged(job, ctx, at, lp, recheck=recheck)
        found, judged, _changes = pack_run._verdict(said)  # noqa: SLF001
        return found, pack_rounds.counted(lp, found, judged, ident, recheck=recheck)

    def judgement(v: tuple[list[str], str]) -> str:
        return "passed" if v[1] == "pass" else "findings" if v[0] else "completed"

    _found, then = job.do(
        "challenger", challenge, lambda v: f"{len(v[0])} new finding(s)" if v[0] else judgement(v),
        op="rejection-recheck" if recheck else "pds-challenge", round_=lp.round + 1, identity=ident,
        judged=judgement,
    )  # fmt: skip
    if then != "pass":
        said = "; ".join(f"{f.id}: {f.text}" for f in lp.findings if f.raised == lp.round - 1) or "rejections judged"
        job.stage("challenger", "returned" if then == "update" else "waiting", said)
    return NEXT[then]


def _reconsider(job: Job, ctx: Context, lp: RoundLoop) -> Action:
    """A fresh challenger reconsiders the findings the owner sent back with a note."""
    at, keys = candidate(job), tuple(f.id for f in pack_rounds.due(lp))
    text = sessions.reconsider_message(ctx.version, ctx.old, pack_rounds.reconsider_lines(lp))

    def reconsider() -> dict[str, tuple[str, str]]:
        cfg = sessions.challenger(
            job.store.settings(), at, checks.skills(at), text, rechecks=keys, submit=dispute_tools.SUBMIT,
            memory=step_sessions.memory(job.store),
        )  # fmt: skip
        run = job.live.session(job.store, cfg)
        p = run.payload
        if not (run.termination and run.termination.confirmed):
            msg = f"the challenger {run.session_id} may still be running; stop it before updating again"
            raise pack_files.PackError(msg)
        if run.ending == "premise" and isinstance(p, tools.WrongPremise):
            return dict.fromkeys(keys, ("unsure", f"premise: {p.reason}"))
        if run.ending != "result" or not isinstance(p, dispute_tools.ReconsiderResult):
            msg = f"the challenger ended with {run.ending}: {run.detail or 'no verdict'}"
            raise pack_files.PackError(msg[:600])
        return {r.finding: (r.verdict, r.text if r.verdict == "clarified" else r.reason) for r in p.reconsidered}

    said = job.do("challenger", reconsider, lambda v: f"reconsidered {', '.join(v)}", op="reconsideration",
                  judged=lambda _v: "completed")  # fmt: skip
    pack_rounds.reconsidered(lp, said)
    return NEXT[pack_rounds.after(lp)]


def _asked(job: Job, ctx: Context, lp: RoundLoop) -> tuple[list[dict[str, Any]], str]:
    """The owner's open questions and the stage they hold: the audit's follow-ups first, then the rounds'."""
    run = job.state["run"]
    if open_ := [k for k in sorted(ctx.follow_ups) if k not in ctx.followed]:
        listed = "; ".join(ctx.follow_ups[k] for k in open_)
        text = (
            f"The deprecation audit left these for a person: {listed}. They are not given to the updater. Continue "
            "without changing them, or discard the update?"
        )
        mark = hashlib.sha256("\n".join(sorted(ctx.follow_ups)).encode()).hexdigest()[:12]
        options = [pack_rounds.CONTINUE, pack_rounds.DISCARD]
        return [pack_rounds.question(f"{run}:follow-ups:{mark}", "follow-ups", text, options,
                                     keys=sorted(ctx.follow_ups))], "audit"  # fmt: skip
    return pack_rounds.questions(lp, run, identity(ctx, candidate(job))), "challenger"


def decided(  # noqa: PLR0913 - the open questions, the answered one, the answer and what it changes
    asked: list[dict[str, Any]], q: dict[str, Any], option: str, *, note: str, ctx: Context, lp: RoundLoop
) -> list[dict[str, Any]]:
    """Record one answer; the questions still open. The last dispute answer sets what the run does next."""
    if q["kind"] == "dispute":
        pack_rounds.decided(lp, q["finding"], option, note)
        left = [x for x in asked if x["id"] != q["id"]]
        if not left:
            ctx.next = NEXT[pack_rounds.after(lp)]
        return left
    if q["kind"] in {"publish", *pack_repair.KINDS}:  # trying again reconciles with GitHub before anything is repeated
        pack_repair.decided(q, option, ctx, repair.PDS)
    elif q["kind"] == "follow-ups":
        ctx.followed, ctx.next = list(q["keys"]), "browser"
    elif option == pack_rounds.ANOTHER:
        lp.extra, lp.ended, ctx.next = lp.extra + 1, "", "challenge"
    else:
        ctx.accepted, ctx.next = q["identity"], "publish"
    return []
