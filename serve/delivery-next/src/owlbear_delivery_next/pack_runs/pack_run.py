"""A design pack update's resumable run (TD-208, TD-220, TD-256): its context, its next action and its sessions.

The run is a loop of actions: the updater, the golden pages on its candidate, the replay when the skills changed, the
challenger's rounds, a reconsideration, the owner and the activation (``pack_activation``). The owner also decides each
change outside the pack, to its expected evidence or its code, and each one the challenger is unsure the upgrade needs
(``pack_gates``). The context, the loop and the owner's questions are kept in the job's state file, and the updater's
repository and the candidate's skills under the store, so a run that waits for the owner survives a host restart. A
session that fails ends the run, as before. An agent's CI repair of the pull request that changes protected pack
content is laid into the candidate, its whole protected content as its commit holds it, and checked the same way, from
the golden pages on, before Delivery pushes it (``pack_repair``): its findings go to the owner, never back to the
updater.
"""

from __future__ import annotations

import hashlib
import shutil
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts import dispute_tools, pack_tools, tools
from owlbear_delivery_next.change_contracts.round_records import PACK, RoundLoop
from owlbear_delivery_next.design_packs import design_pack, pack_git
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.pack_runs import (
    pack_activation,
    pack_candidate,
    pack_gates,
    pack_publish,
    pack_repair,
    pack_rounds,
    pack_updater,
)
from owlbear_delivery_next.pack_runs.pack_gates import GOLDEN
from owlbear_delivery_next.settings import rounds

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.pack_runs.pack_job import Job
    from owlbear_delivery_next.runtimes.session_result import Run

type Action = Literal["update", "golden", "replay", "challenge", "recheck", "reconsider", "wait", "activate"]
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
    baseline: dict[str, str]  # the package's files the update may rewrite, by package path: their digests at the start
    checkout: dict[str, str]  # the package's checkout: its root, repository and the base pinned for the commit
    publication: pack_publish.Publication | None = None  # set once the update goes into main
    start: dict[str, str]  # the updater repository's files as laid out
    sid: str
    sessions: int = 0  # updater sessions so far: the first repair resumes the producer (TD-123)
    summary: str = ""
    reason: str = ""  # the updater's last reason for changed evidence
    replayed: str = ""
    judged: str = ""  # the pack identity the last replay judged
    accepted: str = ""  # the pack identity the owner activated without a pass (TD-256)
    after: Action = "challenge"  # what follows the updater's session once its candidate's checks pass
    evidence: str = ""  # the changed golden evidence the owner accepted: its digest (TD-177)
    code: str = ""  # the glue change the owner approved: its digest (TD-194, TD-414)
    kept: dict[str, str] = Field(default_factory=dict)  # changes the owner kept when the challenger was unsure
    unsure: dict[str, str] = Field(default_factory=dict)  # the last full round's unsure changes, for the owner
    changes: list[str] = Field(default_factory=list)  # the last full round's judgement of each changed file
    undo: list[str] = Field(default_factory=list)  # the paths the owner had undone, restored before the next session
    repair: pack_repair.Repair = Field(default_factory=pack_repair.Repair)  # the agent's CI repairs of the pull request
    next: Action = "update"


def sha(data: bytes) -> str:
    """The SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def skill_path(name: str) -> str:
    """The package path of the pinned skill *name*."""
    return f"{preload.ROOT}/{name}/SKILL.md"


def begin(  # noqa: PLR0913 - the job, the candidate, its checkout and the evidence so far
    job: Job, c: pack_candidate.Candidate, src: pack_git.Source, *, diff: str, golden: str, why: str
) -> str | None:
    """Lay out the updater's repository, pin the loop's values and run; the ending's words, or None while waiting."""
    at = job.workspace
    shutil.rmtree(at, ignore_errors=True)  # never resumed from an earlier run
    at.mkdir(parents=True)
    package = job.live.package.resolve()
    start = pack_updater.lay_out(at, c, job.live.clone, package)
    ctx = Context(
        tag=c.tag, why=why, diff=diff, golden=golden, pins=c.pins, manifest=c.manifest, notice=c.notice,
        baseline=c.inputs | pack_gates.baseline(package),  # what the candidate was made from, never a later read
        checkout={"root": str(src.root), "repository": src.repository, "base": src.base},
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
    unchanged(package, ctx)
    baseline = {n: (package / skill_path(n)).read_bytes() for n in ctx.pins["skills"]}
    return pack_candidate.Candidate(
        ctx.tag, ctx.pins, ctx.manifest, ctx.notice, installed, job.store.root / CANDIDATE, baseline
    )


def unchanged(package: Path, ctx: Context) -> None:
    """Check that no package file the update may rewrite changed since it started.

    Raises:
        Stopped: One changed.
    """
    for path, digest in ctx.baseline.items():
        if not (package / path).is_file() or sha((package / path).read_bytes()) != digest:
            name = path.removeprefix(f"{preload.ROOT}/").removesuffix("/SKILL.md")
            msg = f"{name} changed in the package during the update; run the update again"
            raise Stopped(msg)


def updater_edits(job: Job, ctx: Context) -> dict[str, bytes | None]:
    """The updater's edits in its folder, against the package's files at the start (``pack_gates``)."""
    return pack_gates.edits(job.workspace, ctx.baseline)


def advance(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> str | None:
    """Run the actions from the context's next one until the owner is asked or the pack is merged.

    Raises:
        Stopped: An action ended the run.
    """
    while True:
        if (r := ctx.repair).phase == "checking" and r.laid != r.commit and not pack_activation.laid(job, c, ctx, lp):
            return None  # a repair is checked only on its own snapshot, laid out again after a host stop
        match ctx.next:
            case "update":  # a repair's findings go to the owner, never the updater
                ctx.next = "wait" if ctx.repair.phase == "checking" else _update(job, c, ctx, lp)
            case "golden":  # a CI repair's check: a new round of the repaired candidate
                ctx.next = _golden(job, c, ctx, lp.round + 1)
            case "replay":
                ctx.next = _replay(job, c, ctx)
            case "challenge" | "recheck":
                ctx.next = _challenge(job, c, ctx, lp, recheck=ctx.next == "recheck")
            case "reconsider":
                ctx.next = _reconsider(job, c, lp)
            case "wait":
                asked, stage = _asked(job, c, ctx, lp)
                job.wait(ctx, lp, pack_activation.repairing(ctx, asked), stage)
                return None
            case "activate":
                return pack_activation.activate(job, c, ctx, lp)
            case other:
                msg = f"the run's next action {other!r} is unknown; run the update again"
                raise Stopped(msg)
        job.keep(ctx, lp)


def _update(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> Action:
    """One updater session, its edits taken into the candidate, then the golden pages on the candidate (TD-177).

    Raises:
        Stopped: The golden pages differ from the candidate's expectations.
    """
    at, live, store = job.workspace, job.live, job.store
    if ctx.undo:  # what the owner had undone, restored before the updater adjusts the rest
        pack_gates.restore(at, ctx.undo, live.package.resolve(), c)
        if any(p.startswith("upstream/") for p in ctx.undo):
            pack_updater.upstream(at, c, live.clone)
        ctx.undo = []
        job.keep(ctx, lp)
    lines = pack_rounds.updater_lines(lp)
    earlier = ctx.summary if ctx.sessions else ""
    whole = pack_updater.prompt(c, ctx.diff, lines, earlier, ctx.golden)
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

    result = job.do(  # a session that completed, never a verdict on its candidate
        "update", lambda: pack_updater.ended(live.update(store, cfg)), lambda r: r.summary, round_=lp.round + 1,
        judged=lambda _r: "completed",
    )  # fmt: skip
    ctx.sessions, ctx.summary, ctx.reason = ctx.sessions + 1, result.summary, result.evidence
    bad = pack_updater.outside(at, ctx.start, c.pins["skills"])
    if not bad:
        pack_updater.taken(at, c)
    identity = pack_gates.identity(c, updater_edits(job, ctx))
    job.identified(identity)
    ctx.after = NEXT[pack_rounds.revised(lp, {r.finding: r.reason for r in result.rejected}, identity)]
    if bad:
        return "wait"  # the owner first: undo or discard (TD-194)
    return _golden(job, c, ctx)


def _golden(job: Job, c: pack_candidate.Candidate, ctx: Context, round_: int | None = None) -> Action:
    """The golden pages on the candidate (TD-177); its changed evidence goes to the owner first.

    Raises:
        Stopped: The golden pages differ from the candidate's expectations.
    """
    identity = pack_gates.identity(c, updater_edits(job, ctx))

    def golden() -> str:  # the candidate's own pages and expectations, with the running code (TD-414)
        said = pack_gates.checked(job.live.golden(c.installed, job.workspace / "golden"))
        if said != pack_gates.AS_EXPECTED:
            raise Stopped(said)
        return said

    ctx.golden = job.do("golden", golden, op="candidate-golden", round_=round_, identity=identity)
    job.identified(identity)  # what the rounds found about another candidate is stale now
    return "wait" if unaccepted(job, ctx) else "replay"


def unaccepted(job: Job, ctx: Context) -> str:
    """The digest of changed golden evidence the owner has not accepted, or empty."""
    mark = pack_gates.digest(updater_edits(job, ctx), GOLDEN)
    return mark if mark != ctx.evidence else ""


def _replay(job: Job, c: pack_candidate.Candidate, ctx: Context) -> Action:
    """The calibration replay when the skills changed since the last one (TD-177); then what the session led to."""
    identity, candidate = design_pack.identity(c.manifest, c.skills), pack_gates.identity(c, updater_edits(job, ctx))
    if identity != ctx.judged:
        replay = lambda: _replayed(job.live.replay(job.store, c, keep=job.keeps))  # noqa: E731
        ctx.replayed, ctx.judged = job.do("replay", replay, identity=candidate), identity
    else:  # the skills it judged are unchanged: its result stands for this candidate
        job.note("replay", "replay", "reused", ctx.replayed, candidate)
    return ctx.after


def _replayed(r: Any) -> str:  # noqa: ANN401 - calibration.Replay
    said = pack_candidate.said_replay(r)
    if not r.ok:
        msg = f"calibration replay: {said}"
        raise Stopped(msg)
    return said


def _challenge(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop, *, recheck: bool) -> Action:
    """One challenger round on the whole candidate, or a check of the updater's rejections only (TD-330).

    A full round judges each file the updater changed (TD-194); one it is unsure about goes to the owner first.
    """
    at, keys = job.workspace, tuple(f.id for f in pack_rounds.pending(lp))
    edits = updater_edits(job, ctx)
    changed = None if recheck else pack_gates.diffs(c, at, job.live.package.resolve(), edits)
    text = pack_candidate.message(
        c, ctx.diff, ctx.golden, ctx.replayed, updated=ctx.summary,
        rounds=pack_rounds.challenge_lines(lp, recheck=recheck), changed=changed,
    )  # fmt: skip
    cap = 0 if recheck else lp.policy.max_findings
    identity = pack_gates.identity(c, edits)
    submit = tools.REVIEW if recheck else pack_tools.REVIEW
    round_ = lp.round + 1  # a recheck stays in the round of the update whose rejections it judges (TD-330)

    def challenge() -> tuple[list[str], list[pack_tools.Change], str]:
        run = pack_candidate.challenge(
            job.store, c, job.live.clone, text, job.live.challenge, rechecks=keys, cap=cap, submit=submit,
            changed=tuple(changed or ()), keep=job.keeps,
        )  # fmt: skip
        found, judged, changes = _verdict(run)
        return found, changes, pack_rounds.counted(lp, found, judged, identity, recheck=recheck)

    def judgement(v: tuple[list[str], list[pack_tools.Change], str]) -> str:  # the session's, then the candidate's
        return "passed" if v[2] == "pass" else "findings" if v[0] else "completed"

    _found, changes, then = job.do(
        "challenger", challenge, lambda v: f"{len(v[0])} new finding(s)" if v[0] else judgement(v),
        op="rejection-recheck" if recheck else "full-challenge", round_=round_, identity=identity, judged=judgement,
    )  # fmt: skip
    if not recheck:
        ctx.changes = [f"{x.path}: needed {x.needed}; {x.what}; suspicious: {x.suspicious}" for x in changes]
        ctx.unsure = {
            x.path: f"{x.what}; suspicious: {x.suspicious}"
            for x in changes
            if x.needed == "unsure" and ctx.kept.get(x.path) != pack_gates.content(c, at, x.path)
        }
    if then != "pass":
        said = "; ".join(f"{f.id}: {f.text}" for f in lp.findings if f.raised == lp.round - 1) or "rejections judged"
        job.stage("challenger", "returned" if then == "update" else "waiting", said)
    return "wait" if ctx.unsure else NEXT[then]


def _verdict(run: Run) -> tuple[list[str], dict[str, tuple[bool, str]], list[pack_tools.Change]]:
    """The verdict's new findings, its judgements and its file judgements; a wrong premise is its round's finding.

    Raises:
        design_pack.PackError: Its processes are not confirmed gone, or it ended without a verdict.
    """
    p = run.payload
    if not (run.termination and run.termination.confirmed):
        msg = f"the challenger {run.session_id} may still be running; stop it before updating again"
        raise design_pack.PackError(msg)
    if run.ending == "result" and isinstance(p, tools.ReviewResult):
        found = [" ".join(f"{f.place}: {f.problem} - fix: {f.fix}".split()) for f in p.findings]
        changes = p.changes if isinstance(p, pack_tools.PackReview) else []
        return found, {r.finding: (bool(r.upheld), r.reason) for r in p.rechecked}, changes
    if run.ending == "premise" and isinstance(p, tools.WrongPremise):
        return [" ".join(f"premise: {p.reason} ({'; '.join(p.evidence)})".split())], {}, []
    msg = f"the challenger ended with {run.ending}: {run.detail or 'no verdict'}"
    raise design_pack.PackError(msg[:600])


def _asked(job: Job, c: pack_candidate.Candidate, ctx: Context, lp: RoundLoop) -> tuple[list[dict[str, Any]], str]:
    """The owner's open questions and the stage they hold: scope, evidence, unsure changes, then the rounds'."""
    at, run = job.workspace, job.state["run"]
    if bad := pack_updater.outside(at, ctx.start, c.pins["skills"]):
        return [pack_gates.scope(run, bad)], "update"
    edits = updater_edits(job, ctx)
    if mark := unaccepted(job, ctx):
        shown = pack_gates.diffs(c, at, job.live.package.resolve(), edits)
        diff = "\n".join(s for p, s in shown.items() if p.startswith(GOLDEN))
        return [pack_gates.evidence(run, diff, ctx.reason, ctx.golden, mark)], "golden"
    if ctx.unsure:
        shown = pack_gates.diffs(c, at, job.live.package.resolve(), edits)
        return [
            pack_gates.unsure(run, p, said, shown.get(p, "(unchanged)"), pack_gates.content(c, at, p))
            for p, said in ctx.unsure.items()
        ], "challenger"
    return pack_rounds.questions(lp, run, pack_gates.identity(c, edits)), "challenger"


def gated(
    asked: list[dict[str, Any]], q: dict[str, Any], option: str, ctx: Context, lp: RoundLoop
) -> list[dict[str, Any]]:
    """Record the owner's answer to a gate question; the questions still open. An undo is restored, then repaired."""
    kind = q["kind"]
    if option == pack_rounds.UNDO:
        paths = q["bad"] if kind == "scope" else [q["path"]] if kind == "unsure" else [GOLDEN.rstrip("/")]
        ctx.undo = sorted({*ctx.undo, *paths})
        why = {"scope": "it is outside what you may change", "unsure": "the owner judged the upgrade does not need it",
               "evidence": "the owner did not accept the changed evidence"}[kind]  # fmt: skip
        pack_rounds.undo(lp, f"{', '.join(paths)}: Delivery restored the package's version ({why}) - fix: keep it "
                             "restored and adjust anything else you changed that depended on it")  # fmt: skip
    elif kind == "evidence":
        ctx.evidence = q["digest"]
    elif kind == "unsure":
        ctx.kept[q["path"]] = q["digest"]
    elif kind == "code":
        ctx.code = q["digest"]
    if kind == "unsure":
        ctx.unsure.pop(q["path"], None)
    left = [x for x in asked if x["id"] != q["id"]]
    if not left:
        accepted = option != pack_rounds.UNDO and kind in {"evidence", "code"}
        ctx.next = {"evidence": "replay", "code": "activate"}[kind] if accepted else NEXT[pack_rounds.after(lp)]
    return left


def _reconsider(job: Job, c: pack_candidate.Candidate, lp: RoundLoop) -> Action:
    """A fresh challenger reconsiders the findings the owner sent back with a note; unsure ones go back to the owner."""
    keys = tuple(f.id for f in pack_rounds.due(lp))
    text = pack_candidate.reconsider_message(c, pack_rounds.reconsider_lines(lp))

    def reconsider() -> dict[str, tuple[str, str]]:
        run = pack_candidate.challenge(
            job.store, c, job.live.clone, text, job.live.challenge, rechecks=keys, submit=dispute_tools.SUBMIT,
            label=pack_candidate.AGAIN, keep=job.keeps,
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

    said = job.do(
        "challenger", reconsider, lambda v: f"reconsidered {', '.join(v)}", op="reconsideration",
        judged=lambda _v: "completed",
    )  # fmt: skip
    pack_rounds.reconsidered(lp, said)
    return NEXT[pack_rounds.after(lp)]


def decided(  # noqa: PLR0913 - the open questions, the answered one, the answer and what it changes
    asked: list[dict[str, Any]], q: dict[str, Any], option: str, *, note: str, ctx: Context, lp: RoundLoop
) -> list[dict[str, Any]]:
    """Record one answer; the questions still open. The last dispute answer sets what the run does next."""
    if q["kind"] == "dispute":
        pack_rounds.decided(lp, q["finding"], option, note)
        left = [x for x in asked if x["id"] != q["id"]]
        if not left:  # TD-193: the answers are carried out together
            ctx.next = NEXT[pack_rounds.after(lp)]
        return left
    if q["kind"] in {"publish", *pack_repair.KINDS}:  # trying again reconciles with GitHub before anything is repeated
        pack_repair.decided(q, option, ctx)
        return []
    if q["kind"] in pack_gates.KINDS:
        return gated(asked, q, option, ctx, lp)
    if option == pack_rounds.ANOTHER:
        lp.extra, lp.ended, ctx.next = lp.extra + 1, "", "challenge"
    else:
        lp.ended, ctx.accepted, ctx.next = lp.ended, q["identity"], "activate"
    return []
