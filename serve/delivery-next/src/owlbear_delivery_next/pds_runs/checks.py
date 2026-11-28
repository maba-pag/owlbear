"""A PDS run's three judges of one tree (#777): the deprecation audit, the browser tests and the challenger.

The run calls them on its candidate, and the merge gate on the pull request's head when its pages differ from what
they passed. Each judges the tree as it is; none changes it.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.impeccable_runs import pack_rounds
from owlbear_delivery_next.impeccable_runs.pack_run import Stopped
from owlbear_delivery_next.pds_runs import audit, browser, pin, sessions, tree
from owlbear_delivery_next.pds_runs.context import AUDIT, BASE
from owlbear_delivery_next.workflow_steps import sessions as step_sessions

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop
    from owlbear_delivery_next.pds_runs.context import Context
    from owlbear_delivery_next.pds_runs.job import Job
    from owlbear_delivery_next.runtimes.session_result import Run


def skills(at: Path) -> Path:
    """The release's skills folder in the tree at *at*."""
    return at / pin.PREFIX / pin.TREE / "skills"


def audited(job: Job, ctx: Context, at: Path) -> audit.Verdict:
    """The deprecation audit of the pages in the tree at *at*, in a fresh copy; its reports kept in the workspace."""
    folder = job.workspace / AUDIT
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    package, settings, memory = at / pin.PREFIX, job.store.settings(), step_sessions.memory(job.store)

    def session(copy: Path, found: Path, message: str) -> Run:
        return job.live.session(job.store, sessions.auditor(settings, copy, found, message, memory=memory))

    done = audit.audit(folder, web=package / "web", tree=package / pin.TREE, version=ctx.version, session=session)
    audit.write(job.workspace, done)
    return done.verdict


def finding(f: audit.Finding) -> str:
    """One audit finding as the updater reads it: its place in the copy, the rule and the fix."""
    swap = f" (replace with {f.replacement})" if f.replacement else ""
    said = f"{f.path.removeprefix(pin.PREFIX)}:{f.line}: {f.title} [{f.rule}]: `{' '.join(f.snippet.split())}`"
    return f"- {said} - fix: {f.fix}{swap}"


def follow_up(f: audit.FollowUp) -> str:
    """One manual follow-up as the owner reads it."""
    places = "; ".join(f"{e['path'].removeprefix(pin.PREFIX)}:{e['line']}" for e in f.evidence)
    return f"{f.subject}: {f.reason} ({places})"


def browsed(job: Job, ctx: Context, at: Path) -> browser.Result:
    """The browser tests in the tree at *at*; a failure passing a rerun on main and on *at* is a flake, named in a pass.

    Raises:
        browser.Unrunnable: They cannot run, or the PDS CDN did not answer.
        Stopped: The suite did not finish, it failed without naming a test, or a failing test also fails on main.
    """
    r = _completed(job, at, (), "first pass")
    if r.passed:
        return r
    if not r.failed:
        msg = f"browser tests: {r.said()} (exit {r.code})"
        raise Stopped(msg)
    main = _completed(job, base(job, ctx), r.failed, "rerun on main")
    if not main.cleared(r.failed):
        passed = [test for test in r.failed if test in main.passed_ids]
        absent = [test for test in r.failed if test not in main.failed and test not in main.passed_ids]
        lead = (
            "The browser rerun on main did not clear the failures. Try again if the machine was busy; "
            "if main is broken, fix it, discard this update and start a new one."
        )
        msg = (
            f"Failed: {', '.join(main.failed) or 'none named'}.\n"
            f"Passed on main: {', '.join(passed) or 'none'}. Did not run on main: {', '.join(absent) or 'none'}."
        )
        if main.told:
            msg += f"\n\n{main.told}"
        raise Stopped(msg, lead=lead)
    candidate = _completed(job, at, r.failed, "rerun on the candidate")
    return r.flake() if candidate.cleared(r.failed) else r  # D-01M6BFK5YF5GYYN7QCDDPBEZH2


def _completed(job: Job, at: Path, ids: tuple[str, ...], attempt: str) -> browser.Result:
    try:
        result = job.live.browser(at, ids)
    except browser.Unrunnable as exc:
        exc.add_note(f"Browser pass: {attempt}")
        raise
    if result.code not in (0, 1):
        lead = f"The browser tests did not finish ({attempt}). Try again if the machine was busy."
        msg = f"{result.said()} (exit {result.code})\n{result.output}"
        raise Stopped(msg, lead=lead)
    return result


def base(job: Job, ctx: Context) -> Path:
    """The base's worktree, made once for the run: where a failing browser test is run again."""
    at = job.workspace / BASE
    if not (at / ".git").exists():
        tree.worktree(Path(ctx.checkout["root"]), at, ctx.checkout["base"], job.live.git)
    return at


def pages(job: Job, ctx: Context, at: Path) -> str:
    """The page changes in the tree at *at* against the base, as one diff."""
    return job.live.git(at, ["diff", "--no-color", ctx.checkout["base"], "--", *tree.SCOPE])


def challenged(job: Job, ctx: Context, at: Path, lp: RoundLoop, *, recheck: bool = False) -> Run:
    """One challenger session on the tree at *at*: the release's evidence, the vendored change and every page edit."""
    text = sessions.challenge_message(
        ctx.version, ctx.old, evidence=ctx.diff, vendored=ctx.vendored, pages=pages(job, ctx, at)[: 4 * 20000],
        updated=ctx.summary, rounds=pack_rounds.challenge_lines(lp, recheck=recheck),
    )  # fmt: skip
    keys = tuple(f.id for f in pack_rounds.pending(lp))
    cap = 0 if recheck else lp.policy.max_findings
    cfg = sessions.challenger(
        job.store.settings(), at, skills(at), text, rechecks=keys, cap=cap,
        memory=step_sessions.memory(job.store),
    )  # fmt: skip
    return job.live.session(job.store, cfg)
