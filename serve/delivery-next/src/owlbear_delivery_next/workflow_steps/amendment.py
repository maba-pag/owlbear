"""The amendment's sessions (TD-185), run before the step it stopped: the shaper's candidate, its challenge, revisions.

Each runs fresh and read-only in the Change's read-only worktree; its result goes to ``change_flow.amending``, which
moves the path on. A Change that stopped meanwhile declines it; one whose PR merged first hands it to a new Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import amend_tools, dispute_tools, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import Change, ErrorKind, Exit, Names, Outcome, StepKind, Waiting
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import BRIEF
from owlbear_delivery_next.change_flow import amending, loop, worktree
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import amendments, sdk_adapter
from owlbear_delivery_next.settings import profile, rounds
from owlbear_delivery_next.state_store import github_writer, identities
from owlbear_delivery_next.state_store.briefs import new_slug
from owlbear_delivery_next.workflow_steps import engine, pending_child, sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.amendment_records import Amendment
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Lock, Store

LABELS = {
    "prepare": (amend_tools.PREPARE, amend_tools.CANDIDATE), "revise": (amend_tools.REVISE, amend_tools.CANDIDATE),
    "challenge": (amend_tools.CHALLENGE, amend_tools.VERDICT), "recheck": (amend_tools.CHALLENGE, amend_tools.VERDICT),
    "reconsider": (amend_tools.RECONSIDER, dispute_tools.SUBMIT),
}  # fmt: skip


def run(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """Run what the current amendment needs now and record it."""
    now, a = datetime.now(UTC), amending.current(change)
    if a is not None and _merged(store, lock, change, repo, now):
        return
    if a is None or _left(store, lock, change, a):
        store.write(lock, change)
        return
    am = change.amending
    if am is None:
        return
    if am.phase == "ask":
        _asked(change, a, now)
        store.write(lock, change)
        return
    if am.phase == "prepare" and a.source == "revert":
        amending.opened(change, a, rounds.pinned(change, BRIEF, store.settings(), "shaper"))
        store.write(lock, change)
        return
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    store.write(lock, change)
    phase = am.phase
    label, submit = LABELS[phase]
    made = _made(store, lock, change, a)

    def start(keep: sessions.Keep) -> pending_child.Judged:
        return sessions.review_run(store, lock, change, path, made, label, submit=submit, keep=keep)

    # its paid run is kept until its result and spend commit together, in one of the writes below (RUN-04)
    verdict, done = pending_child.child(store, lock, change, (label, pending_child.amending(change)), start)
    step = pending_child.booked(change, done, {"exit": verdict.exit})
    store.write(lock, _recorded(store, change, a, verdict, done))
    if step is not None:
        sessions.announce(store, lock, change.slug, step)


def _recorded(store: Store, change: Change, a: Amendment, verdict: loop.StepResult, done: Run) -> Change:
    """The Change with the session's result recorded; a failed one stays in its phase, to run again or ask."""
    now, payload, phase = datetime.now(UTC), done.payload, change.amending.phase if change.amending else ""
    if phase == "reconsider" and _reconsidered(change, verdict, payload, now):
        return change
    if verdict.cause is None and verdict.exit == Exit.DONE and isinstance(payload, amend_tools.VerdictResult):
        amending.judged(change, payload, done.session_id, now)
    elif verdict.cause is None and verdict.exit == Exit.DONE and isinstance(payload, amend_tools.CandidateResult):
        if phase == "prepare":
            amending.prepared(change, payload, rounds.pinned(change, BRIEF, store.settings(), "shaper"), now)
        else:
            amending.revised(change, payload, now)
    else:  # failed: the phase stays and it runs again, or the owner is asked or stopped for it
        whole = verdict.exit in {Exit.RETRY, Exit.STOP} or verdict.question or verdict.waiting
        cause = verdict.cause or cause_key(ErrorKind.RESULT, change.step.kind, f"amend {a.id}")
        failed = verdict if whole else verdict.model_copy(update={"exit": Exit.RETRY, "cause": cause})
        return loop.apply(change, failed, now)
    return change


def _reconsidered(change: Change, verdict: loop.StepResult, payload: object, now: datetime) -> bool:
    """A reconsideration's verdicts, or each finding unsure on a wrong premise; False when it failed."""
    due = [f.id for f in change.loops[amending.key(amending.current(change))].findings if f.reconsider == "due"]
    if isinstance(payload, tools.WrongPremise) and verdict.exit == Exit.BACK and not verdict.operational:
        said = dict.fromkeys(due, ("unsure", f"premise: {payload.reason}"))  # he decides each, as for unsure
    elif verdict.cause is None and verdict.exit == Exit.DONE and isinstance(payload, dispute_tools.ReconsiderResult):
        said = {r.finding: (r.verdict, r.text if r.verdict == "clarified" else r.reason) for r in payload.reconsidered}
    else:
        return False
    amending.reconsidered(change, said, now)
    return True


def _made(store: Store, lock: Lock, change: Change, a: Amendment) -> Callable[[Path], sdk_adapter.Session]:
    am = change.amending
    phase = am.phase if am else "prepare"
    lp = change.loops.get(amending.key(a))
    keys = tuple(f.id for f in lp.findings if f.state == "rejected") if lp and phase in {"challenge", "recheck"} else ()
    keys = tuple(f.id for f in lp.findings if f.reconsider == "due") if lp and phase == "reconsider" else keys
    shaper = phase in {"prepare", "revise"}

    def made(at: Path) -> sdk_adapter.Session:
        if phase == "prepare":
            message = amendments.prepare(change, a, at)
        elif phase == "revise":
            message = amendments.revise(change, a, at)
        elif phase == "reconsider":
            message = amendments.reconsider(change, a, at)
        else:
            message = amendments.challenge(change, a, at, recheck=phase == "recheck")
        return sdk_adapter.Session(
            kind=StepKind.REVIEW,
            worktree=at,
            session_id="",
            message=message,
            resume=False,
            policy=Policy(at, write=False),
            observe=lambda: worktree.observe(at, change.names.target),
            checks=(),
            rechecks=keys,
            cap=0 if phase in {"recheck", "reconsider"} or lp is None else lp.policy.max_findings,
            rejectable=tuple(f.id for f in lp.findings if f.state == "open") if shaper and lp else (),
            amendable=amendments.amendable(change),  # the shaper's items, the challenger's affected names
            journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
            memory=sessions.memory(store),
        )

    return made


def _asked(c: Change, a: Amendment, now: datetime) -> None:
    """Waiting on the owner: his open question gates again; with none open, the path goes on."""
    q = next((q for q in reversed(c.questions) if q.answer is None and (amending.owned(q) or [None])[0] == a.id), None)
    if q is not None:
        c.outcome = Outcome(exit=Exit.ASK, cause=q.cause, reason=q.text, who="you", question=q.id, at=now)
    else:
        amending.proceed(c, now)


def _merged(store: Store, lock: Lock, c: Change, repo: Path, now: datetime) -> bool:
    """At the merge step, a submitted merge's outcome first: merged, the step ends and the amendment leaves with it."""
    if c.step.kind != StepKind.MERGE or not c.names.pr:
        return False
    prof, writer = store.read_profile() or Profile(), github_writer.of(store, repo)
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo, writer), now, writer)
    try:
        pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr)
    except ProviderError as exc:  # unread: the merge step's own exit for it, and the amendment waits
        store.write(lock, loop.apply(c, engine.failed(c, exc, now), now))
        return True
    if not pr.merged:
        return False
    done = loop.StepResult(exit=Exit.DONE, reason=f"PR #{pr.number} was merged in GitHub")
    store.write(lock, loop.apply(c, engine.landed(ctx, c, pr) or done, now))
    return True


def _left(store: Store, lock: Lock, c: Change, a: Amendment) -> bool:
    """Whether the Change left the stopped step's work: stopped, reshaped, or merged before it ended."""
    s = c.step
    if c.intent.abandoned_at or (s.kind == StepKind.CLEANUP and s.mode == "abandon"):
        amending.left(c, "the Change stopped before it ended")
    elif s.kind == StepKind.SHAPE:
        amending.left(c, "the brief is reshaped")
    elif s.kind == StepKind.CLEANUP:  # its pull request merged: it finishes unchanged, a new Change holds this

        def moved(number: int, taken: list[str]) -> Change:
            new = _follow_up(c, a, number, taken)
            amending.left(c, "")
            a.state, a.moved_to = "moved", new.handle
            return new

        identities.publish_new(store, moved, parent=(lock, c))  # both or neither: a rerun makes no second one
    else:
        return False
    return True


def _follow_up(c: Change, a: Amendment, number: int, taken: list[str]) -> Change:
    """A new Change in shaping that holds the candidate *a* of merged *c*, for the owner to shape and approve."""
    items = "; ".join(f"{i.field} {i.key}: {i.old!r} -> {i.new!r}" if i.key else f"add {i.field}: {i.new!r}"
                      for i in a.items)  # fmt: skip
    words = (
        f"Follow-up of {c.handle or c.slug} ({c.brief.title}), merged before its amendment {a.id} ended: {a.reason}"
        f"{f' Candidate: {items}' if items else ''}"
    )
    slug = new_slug(f"amend {c.brief.title or c.slug}", taken)
    new = Change(slug=slug, handle=f"c{number}", profile_version=c.profile_version,
                 names=Names(branch=f"owlbear/{slug}", target=c.names.target))  # fmt: skip
    new.intent.words = words[:4000]
    why = f"from {c.handle or c.slug}: {a.reason}"
    new.amendments.append(a.model_copy(deep=True, update={"id": "A1", "state": "recorded", "reason": why}))
    now = datetime.now(UTC)
    new.outcome = Outcome(exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", at=now,
                          reason="shape the amendment of the merged Change in chat, then approve it")  # fmt: skip
    return new
