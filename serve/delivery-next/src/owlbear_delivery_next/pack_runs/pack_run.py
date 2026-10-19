"""A design pack update's resumable run (TD-208, TD-220, TD-256): its context, its next action and its sessions.

After the golden pages the run is a loop of actions: the updater, the replay when the skills changed, the challenger's
rounds, a reconsideration, the owner and the activation. The context, the loop and the owner's questions are kept in
the job's state file, and the updater's repository and the candidate's skills under the store, so a run that waits
for the owner survives a host restart. A session that fails ends the run, as before.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.change_contracts import dispute_tools, tools
from owlbear_delivery_next.change_contracts.round_records import PACK, RoundLoop
from owlbear_delivery_next.design_packs import design_pack, pack_git
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.pack_runs import pack_candidate, pack_rounds, pack_updater
from owlbear_delivery_next.settings import rounds

if TYPE_CHECKING:
    from owlbear_delivery_next.pack_runs.pack_job import Job
    from owlbear_delivery_next.runtimes.session_result import Run

type Action = Literal["update", "challenge", "recheck", "reconsider", "wait", "activate"]
CANDIDATE = "design-pack-candidate"  # the run's candidate skills, under the store
UPDATER = "design-pack-updater"  # the updater's repository, under the store
NEXT: dict[str, Action] = {
    "challenge": "challenge", "recheck": "recheck", "end": "wait", "dispute": "wait",
    "reconsider": "reconsider", "update": "update", "pass": "activate",
}  # fmt: skip


class Stopped(Exception):  # noqa: N818 - how a stage ends the run
    """A stage ended the run: up to date, or failed with a reason."""

    def __init__(self, reason: str, *, current: bool = False) -> None:
        """Keep the reason; *current* ends the run as up to date rather than failed."""
        super().__init__(reason)
        self.reason, self.current = reason, current


class Context(BaseModel):
    """What a waiting run needs to go on: the candidate, the evidence so far and the next action."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    why: str  # the activation commit's subject
    diff: str
    golden: str
    pins: dict[str, Any]
    manifest: str
    notice: str
    baseline: dict[str, str]  # the package's files an update rewrites, by package path: their digests at the start
    checkout: dict[str, str]  # the package checkout an activation commits on
    start: dict[str, str]  # the updater repository's files as laid out
    sid: str
    sessions: int = 0  # updater sessions so far: the first repair resumes the producer (TD-123)
    summary: str = ""
    replayed: str = ""
    judged: str = ""  # the pack identity the last replay judged
    accepted: str = ""  # the pack identity the owner activated without a pass (TD-256)
    next: Action = "update"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(name: str) -> str:
    return f"{preload.ROOT}/{name}/SKILL.md"


def begin(  # noqa: PLR0913 - the job, the candidate, its checkout and the evidence so far
    job: Job, c: pack_candidate.Candidate, co: pack_git.Checkout, *, diff: str, golden: str, why: str
) -> str | None:
    """Lay out the updater's repository, pin the loop's values and run; the ending's words, or None while waiting."""
    at = job.store.root / UPDATER
    shutil.rmtree(at, ignore_errors=True)  # never resumed from an earlier run
    at.mkdir(parents=True)
    start = pack_updater.lay_out(at, c, job.live.clone)
    ctx = Context(
        tag=c.tag, why=why, diff=diff, golden=golden, pins=c.pins, manifest=c.manifest, notice=c.notice,
        baseline=c.inputs,  # what the candidate was made from, never a later read
        checkout={"root": str(co.root), "branch": co.branch, "remote": co.remote, "merge": co.merge},
        start=start, sid=pack_updater.new_id(),
    )  # fmt: skip
    lp = RoundLoop(subject=PACK, policy=rounds.policy(job.store.settings(), PACK, "updater"))
    job.keep(ctx, lp)
    return advance(job, c, ctx, lp)


def rebuilt(job: Job, ctx: Context) -> pack_candidate.Candidate:
    """The waiting run's candidate again, after checking nothing it stands on moved meanwhile.

    Raises:
        Stopped: Its detector is gone from this machine, or a package skill changed since the run started.
    """
    installed = design_pack.installed(ctx.pins)
    if installed is None:
        msg = f"the candidate {ctx.pins['pack']} is no longer installed on this machine; run the update again"
        raise Stopped(msg)
    package = job.live.package.resolve()
    _unchanged(package, ctx)
    baseline = {n: (package / _path(n)).read_bytes() for n in ctx.pins["skills"]}
    return pack_candidate.Candidate(
        ctx.tag, ctx.pins, ctx.manifest, ctx.notice, installed, job.store.root / CANDIDATE, baseline
    )


def _unchanged(package: Path, ctx: Context) -> None:
    for path, digest in ctx.baseline.items():
        if _sha((package / path).read_bytes()) != digest:
            name = path.removeprefix(f"{preload.ROOT}/").removesuffix("/SKILL.md")
            msg = f"{name} changed in the package during the update; run the update again"
            raise Stopped(msg)


def advance(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> str | None:
    """Run the actions from the context's next one until the owner is asked or the pack is pushed.

    Raises:
        Stopped: An action ended the run.
    """
    while True:
        match ctx.next:
            case "update":
                ctx.next = _update(job, c, ctx, lp)
            case "challenge" | "recheck":
                ctx.next = _challenge(job, c, ctx, lp, recheck=ctx.next == "recheck")
            case "reconsider":
                ctx.next = _reconsider(job, c, lp)
            case "wait":
                identity = design_pack.identity(c.manifest, c.skills)
                job.wait(ctx, lp, pack_rounds.questions(lp, job.state["run"], identity))
                return None
            case "activate":
                return _activate(job, c, ctx, lp)
            case other:
                msg = f"the run's next action {other!r} is unknown; run the update again"
                raise Stopped(msg)
        job.keep(ctx, lp)


def _update(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> Action:
    """One updater session, its edits taken into the candidate, the replay when they changed the pack."""
    at, live, store = job.store.root / UPDATER, job.live, job.store
    lines = pack_rounds.updater_lines(lp)
    earlier = ctx.summary if ctx.sessions else ""
    whole = pack_updater.prompt(c, ctx.diff, lines, earlier)
    resume = ctx.sessions == 1  # the producer repairs once, then a fresh updater (TD-123)
    if ctx.sessions > 1:
        ctx.sid = pack_updater.new_id()
    ask = pack_updater.repair(lines) if resume else whole

    def replaced() -> str:  # the resumed updater is gone: a fresh one takes its repair, told the earlier work (TD-175)
        ctx.sid = pack_updater.new_id()
        job.log("update: the updater's session could not be resumed; a fresh one takes its repair")
        job.keep(ctx, lp)
        return ctx.sid

    keys = (pack_rounds.rejectable(lp), pack_rounds.settled(lp))
    cfg = pack_updater.config(store, at, ctx.sid, ask, resume=resume, fresh=whole, replaced=replaced, keys=keys)

    def update() -> pack_updater.UpdateResult:
        result = pack_updater.ended(live.update(store, cfg))
        pack_updater.taken(at, ctx.start, c)
        return result

    result = job.do("update", update, lambda r: r.summary)
    ctx.sessions, ctx.summary = ctx.sessions + 1, result.summary
    identity = design_pack.identity(c.manifest, c.skills)
    if identity != ctx.judged:  # the affected check reruns after the updater's edits (TD-177)
        ctx.replayed, ctx.judged = job.do("replay", lambda: _replayed(live.replay(store, c))), identity
    then = pack_rounds.revised(lp, {r.finding: r.reason for r in result.rejected}, identity)
    return NEXT[then]


def _replayed(r: Any) -> str:  # noqa: ANN401 - calibration.Replay
    said = pack_candidate.said_replay(r)
    if not r.ok:
        msg = f"calibration replay: {said}"
        raise Stopped(msg)
    return said


def _challenge(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop, *, recheck: bool) -> Action:
    """One challenger round on the whole candidate, or a check of the updater's rejections only (TD-330)."""
    keys = tuple(f.id for f in pack_rounds.pending(lp))
    text = pack_candidate.message(
        c, ctx.diff, ctx.golden, ctx.replayed, updated=ctx.summary,
        rounds=pack_rounds.challenge_lines(lp, recheck=recheck),
    )  # fmt: skip
    cap = 0 if recheck else lp.policy.max_findings
    identity = design_pack.identity(c.manifest, c.skills)

    def challenge() -> tuple[list[str], dict[str, tuple[bool, str]]]:
        run = pack_candidate.challenge(job.store, c, job.live.clone, text, job.live.challenge, rechecks=keys, cap=cap)
        return _verdict(run)

    found, judged = job.do("challenger", challenge, lambda v: f"{len(v[0])} new finding(s)" if v[0] else "passed")
    then = pack_rounds.counted(lp, found, judged, identity, recheck=recheck)
    if then != "pass":
        said = "; ".join(f"{f.id}: {f.text}" for f in lp.findings if f.raised == lp.round - 1) or "rejections judged"
        job.stage("challenger", "returned" if then == "update" else "waiting", said)
    return NEXT[then]


def _verdict(run: Run) -> tuple[list[str], dict[str, tuple[bool, str]]]:
    """The verdict's new findings and its judgements; a wrong premise is its round's finding.

    Raises:
        design_pack.PackError: Its processes are not confirmed gone, or it ended without a verdict.
    """
    p = run.payload
    if not (run.termination and run.termination.confirmed):
        msg = f"the challenger {run.session_id} may still be running; stop it before updating again"
        raise design_pack.PackError(msg)
    if run.ending == "result" and isinstance(p, tools.ReviewResult):
        found = [" ".join(f"{f.place}: {f.problem} - fix: {f.fix}".split()) for f in p.findings]
        return found, {r.finding: (bool(r.upheld), r.reason) for r in p.rechecked}
    if run.ending == "premise" and isinstance(p, tools.WrongPremise):
        return [" ".join(f"premise: {p.reason} ({'; '.join(p.evidence)})".split())], {}
    msg = f"the challenger ended with {run.ending}: {run.detail or 'no verdict'}"
    raise design_pack.PackError(msg[:600])


def _reconsider(job: Job, c: pack_candidate.Candidate, lp: RoundLoop) -> Action:
    """A fresh challenger reconsiders the findings the owner sent back with a note; unsure ones go back to the owner."""
    keys = tuple(f.id for f in pack_rounds.due(lp))
    text = pack_candidate.reconsider_message(c, pack_rounds.reconsider_lines(lp))

    def reconsider() -> dict[str, tuple[str, str]]:
        run = pack_candidate.challenge(
            job.store, c, job.live.clone, text, job.live.challenge, rechecks=keys, submit=dispute_tools.SUBMIT,
            label=pack_candidate.AGAIN,
        )  # fmt: skip
        p = run.payload
        if not (run.termination and run.termination.confirmed):
            msg = f"the challenger {run.session_id} may still be running; stop it before updating again"
            raise design_pack.PackError(msg)
        if run.ending == "premise" and isinstance(p, tools.WrongPremise):
            return dict.fromkeys(keys, ("unsure", f"premise: {p.reason}"))
        if run.ending != "result" or not isinstance(p, dispute_tools.ReconsiderResult):
            msg = f"the challenger ended with {run.ending}: {run.detail or 'no verdict'}"
            raise design_pack.PackError(msg[:600])
        return {r.finding: (r.verdict, r.text if r.verdict == "clarified" else r.reason) for r in p.reconsidered}

    said = job.do("challenger", reconsider, lambda v: f"reconsidered {', '.join(v)}")
    pack_rounds.reconsidered(lp, said)
    return NEXT[pack_rounds.after(lp)]


def _activate(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> str:
    """Commit and push exactly the pack the last verdict passed, or the one the owner accepted (TD-256)."""
    live, package = job.live, job.live.package.resolve()
    expected = ctx.accepted or (lp.head if lp.ended == "clean" else "")
    if not expected or design_pack.identity(c.manifest, c.skills) != expected:
        msg = "the candidate is not what the challenger passed or you accepted; run the update again"
        raise Stopped(msg)
    edited = [n for n in c.pins["skills"] if _sha(pack_updater.skill(c, n).read_bytes()) != ctx.baseline[_path(n)]]
    said = f"The updater changed {', '.join(edited)}." if edited else "The updater changed no skill."
    passed = "" if ctx.accepted else " The challenger passed."
    rounds_ = pack_rounds.summary(lp, owner=bool(ctx.accepted))
    body = f"{ctx.why}\n\nGolden pages as expected. Calibration replay: {ctx.replayed}. {said}{passed} {rounds_}"
    co = pack_git.Checkout(Path(ctx.checkout["root"]), ctx.checkout["branch"], ctx.checkout["remote"],
                           ctx.checkout["merge"])  # fmt: skip
    changed = {package / pack_candidate.MANIFEST: c.manifest, package / pack_candidate.NOTICE: c.notice}

    def activate() -> str:  # the edited skills join the one commit, checked against the package just before
        _unchanged(package, ctx)
        changed.update({package / _path(n): pack_updater.skill(c, n).read_text(encoding="utf-8") for n in edited})
        return pack_git.activate(co, changed, body, live.git)

    commit = job.do("activate", activate)
    job.do("push", lambda: pack_git.push(co, commit, live.git), lambda _o: f"{commit} to {co.remote} {co.merge}")
    job.pushed(commit, co, sorted(str(p.relative_to(co.root)) for p in changed))
    if ctx.accepted:
        return "activated by you after rounds without a pass, committed and pushed"
    return "activated, committed and pushed"
