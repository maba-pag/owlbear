"""The amendment's sessions (TD-185), run before the step it stopped: the shaper's candidate, its challenge, revisions.

Each runs fresh and read-only in the Change's read-only worktree; its result goes to ``change_flow.amending``, which
moves the path on. A Change that stopped meanwhile declines it; one whose PR merged first hands it to a new Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import amend_tools
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
from owlbear_delivery_next.state_store import identities
from owlbear_delivery_next.state_store.briefs import new_slug
from owlbear_delivery_next.workflow_steps import engine, sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.amendment_records import Amendment
    from owlbear_delivery_next.change_contracts.models import Question
    from owlbear_delivery_next.state_store.store import Lock, Store

STOPPED = ("abandon",)


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
    label = amend_tools.CHALLENGE if phase in {"challenge", "recheck"} else (
        amend_tools.PREPARE if phase == "prepare" else amend_tools.REVISE
    )  # fmt: skip
    submit = amend_tools.VERDICT if label == amend_tools.CHALLENGE else amend_tools.CANDIDATE
    # the stopped step's decisions, which the runner's gate holds, and the complete list for the challenger
    verdict, done = sessions.review_run(store, lock, change, path, _made(store, lock, change, a), label, submit=submit)
    now, payload = datetime.now(UTC), done.payload
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
        store.write(lock, loop.apply(change, failed, now))
        return
    store.write(lock, change)


def _made(store: Store, lock: Lock, change: Change, a: Amendment) -> Callable[[Path], sdk_adapter.Session]:
    am = change.amending
    phase = am.phase if am else "prepare"
    lp = change.loops.get(amending.key(a))
    keys = tuple(f.id for f in lp.findings if f.state == "rejected") if lp and phase in {"challenge", "recheck"} else ()
    shaper = phase in {"prepare", "revise"}

    def made(at: Path) -> sdk_adapter.Session:
        if phase == "prepare":
            message = amendments.prepare(change, a, at)
        elif phase == "revise":
            message = amendments.revise(change, a, at)
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
            cap=0 if phase == "recheck" or lp is None else lp.policy.max_findings,
            rejectable=tuple(f.id for f in lp.findings if f.state == "open") if shaper and lp else (),
            amendable=amendments.amendable(change) if shaper else (),
            journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
            memory=sessions.memory(store),
        )

    return made


def _asked(c: Change, a: Amendment, now: datetime) -> None:
    """Waiting on the owner: his open question gates again; with none open, the path goes on."""
    q = next((q for q in reversed(c.questions) if q.answer is None and _of(q, a)), None)
    if q is not None:
        c.outcome = Outcome(exit=Exit.ASK, cause=q.cause, reason=q.text, who="you", question=q.id, at=now)
    else:
        amending.proceed(c, now)


def _of(q: Question, a: Amendment) -> bool:
    own = amending.owned(q)
    return own is not None and own[0] == a.id


def _merged(store: Store, lock: Lock, c: Change, repo: Path, now: datetime) -> bool:
    """At the merge step, a submitted merge's outcome first: merged, the step ends and the amendment leaves with it."""
    if c.step.kind != StepKind.MERGE or not c.names.pr:
        return False
    prof = store.read_profile() or Profile()
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo), now)
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
    if c.intent.abandoned_at or (s.kind == StepKind.CLEANUP and s.mode in STOPPED):
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
    kept = a.model_copy(deep=True, update={"state": "recorded", "reason": f"from {c.handle or c.slug}: {a.reason}"})
    new.amendments.append(kept.model_copy(update={"id": "A1"}))
    now = datetime.now(UTC)
    new.outcome = Outcome(exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", at=now,
                          reason="shape the amendment of the merged Change in chat, then approve it")  # fmt: skip
    return new
