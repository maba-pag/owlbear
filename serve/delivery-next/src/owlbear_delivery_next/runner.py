"""Process entry for one Change and one step: ``python -m owlbear_delivery_next.runner <change> [--repo PATH]``."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import uuid
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import (
    budgets,
    calibration,
    design_tools,
    held,
    loop,
    overlap,
    permissions,
    profile,
    prompts,
    roles,
    sdk_adapter,
    session_result,
    sessions,
    setup,
    tools,
)
from owlbear_delivery_next.cli import describe
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.models import Environment, ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.sessions import UsageUnreadError
from owlbear_delivery_next.steps import (
    before,
    check,
    cleanup,
    conversation,
    decision,
    design,
    engine,
    follow,
    judges,
    merge,
    publish,
    review,
    visual,
    worktree,
)
from owlbear_delivery_next.store import LockHeldError, Store, StoreError, git_common_dir

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change, Step
    from owlbear_delivery_next.store import Lock

AGENT = frozenset({StepKind.PLAN, StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK})
TARGET = ("target", StepKind.BUILD, Exit.BACK)  # a builder's accepted target premise; a stop on its processes wins


type Result = loop.StepResult


def _shape(_ctx: engine.Ctx, c: Change) -> tuple[Change, loop.StepResult]:
    """Shaping happens in chat; the step waits for a revised brief and its approval."""
    why = c.outcome.reason if c.outcome else f"brief v{c.brief.version} is not approved for planning"
    return c, engine.pending(Waiting.CHAT, f"brief needs a change: {why} · revise in chat, then approve", None, "you")


ENGINE: dict[StepKind, engine.Step] = {
    StepKind.SHAPE: _shape,
    StepKind.PUBLISH: publish.run,
    StepKind.FOLLOW: follow.run,
    StepKind.MERGE: merge.run,
    StepKind.CLEANUP: cleanup.run,
}
_out = sessions.out


def _previous(store: Store, slug: str, session: str | None) -> dict[int, float | None]:
    """PIDs earlier runners persisted for *session*; they remain in the activity log when a runner is killed."""
    pids = [e.get("pids", {}) for e in store.events(slug) if e.get("event") == "pids" and e.get("session") == session]
    return {int(p): c for found in pids for p, c in found.items()}


def _others(store: Store, slug: str) -> dict[str, list[str]]:
    """Scopes of the other open Changes of this clone: their plan's task scopes, else their brief's."""
    return {n.handle: n.scope for n in overlap.neighbours(store, slug, datetime.now(UTC)) if not n.merged}


def _agent(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    answer = next(
        (q for q in reversed(change.questions) if q.step == s.kind and q.answer and not q.effect_observed_at), None
    )
    accepted = held.take(store, lock, change)  # TD-56: processed in place of a new session
    resume = bool(answer and s.session)
    if not resume:
        s.session = (
            accepted.session_id if accepted else f"{slug}-{s.kind}-{s.task or s.mode or 'all'}-{uuid.uuid4().hex[:8]}"
        )
    s.started_at = now
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    if s.kind == StepKind.BUILD and task and task.base is None:
        task.base = worktree.head(path)
    since = task.base if task and s.kind in {StepKind.BUILD, StepKind.REVIEW} else None
    start = worktree.head(path) if s.kind == StepKind.INTEGRATE else None
    store.write(lock, change)  # The session id and task base are durable before the runtime starts.
    others = _planning(store, lock, slug, path) if s.kind == StepKind.PLAN else {}
    parts = prompts.session(change, profile, path, others)

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, within = budgets.charge(change, session_result.missing_cause(s.kind), datetime.now(UTC))
        change.step.session = f"{slug}-{s.kind}-{s.task or s.mode or 'all'}-{uuid.uuid4().hex[:8]}" if within else None
        store.write(lock, change)
        return change.step.session

    role = roles.chosen(store.settings(), s.kind)
    cfg = sdk_adapter.Session(
        kind=s.kind,
        worktree=path,
        session_id=s.session or "",
        message=prompts.answer(answer) if resume and answer else parts.message,
        resume=resume,
        policy=permissions.Policy(
            path, parts.allowed, write=parts.write, checks=tuple(worktree.checks(profile)) if parts.write else ()
        ),
        observe=lambda: worktree.observe(path, change.names.target, since),
        checks=parts.checks,
        submit=parts.submit,
        scope=tuple(change.brief.scope),
        model=role.model,
        effort=role.effort,
        fresh=parts.message,
        previous=_previous(store, slug, s.session) if resume else {},
        journal=sdk_adapter.Journal(
            lambda e: store.log(lock, slug, e), delivered, replaced, lambda d: store.write_now(lock, slug, d)
        ),
        item=task.item if task and task.item and s.kind == StepKind.BUILD else None,
        memory=sessions.memory(store),
        ui=change.brief.ui,
        helpers=((design_tools.SCAN, partial(design.builder_scan, path)),)
        if s.kind == StepKind.BUILD and change.brief.ui  # the builder's design detector (slice 7)
        else (),
    )
    run = accepted or _kept(cfg, store)
    end = datetime.now(UTC)
    # The session's callbacks replace ``change``; objects taken from it before the session are stale.
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    result = review.recorded(change, task, run, path, session_result.to_result(run, s.kind, end))
    result = conversation.disputed(task, run.payload, result)
    conversation.respond(task, run.payload, run.head, result.exit)
    sessions.logged(
        store, lock, change, run, {"kind": s.kind, "exit": result.exit} | ({"held": True} if accepted else {})
    )
    if s.kind == StepKind.PLAN and result.plan:
        message = prompts.plan_challenge(change, result.plan, profile, path, others)
        result = _challenge(store, lock, change, dataclasses.replace(cfg, message=message), result)
        if result.exit == Exit.DONE and result.plan:  # shared paths are shown, never asked about (D7)
            change.overlaps = overlap.found(result.plan, others, overlap.generated(path))
        end = datetime.now(UTC)
    result = overlap.integrated(store, change, path, (start, run.ending), result)
    if isinstance(p := run.payload, tools.WrongPremise) and (p.stage, s.kind, result.exit) == TARGET:
        result = engine.needs_target(change, path, f"{p.reason} ({'; '.join(p.evidence)})", end)
    if answer and session_result.effect_seen(run):
        change = budgets.effect_observed(change, answer.id, end)
    if isinstance(p := run.payload, tools.CheckRecipe) and result.exit == Exit.PENDING:
        change.env = Environment(check=s.task or "", command=p.command, directory=p.directory, ready_url=p.ready_url)
    store.write(lock, loop.apply(change, result, end))


def _kept(cfg: sdk_adapter.Session, store: Store) -> session_result.Run:
    """The step's own session; an unread one names its worktree so the gate can hold its result (TD-56)."""
    try:
        return sessions.run(store, cfg)
    except UsageUnreadError as exc:
        exc.worktree = cfg.worktree
        raise


def _planning(store: Store, lock: Lock, slug: str, path: Path) -> dict[str, list[str]]:
    """The read-only planner needs a clean tree: edits an earlier step left are kept in a stash first.

    Returns:
        The other open Changes' scopes the planner avoids.
    """
    message = f"owlbear {slug}: uncommitted edits before planning"
    if worktree.shelve(path, message):
        store.log(lock, slug, {"event": "shelved", "at": datetime.now(UTC).isoformat(timespec="seconds")})
        _out(f"{slug}: uncommitted edits kept in `git stash list` as '{message}'")
    return _others(store, slug)


def _visual(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """B23: capture the brief's states from the ready environment and judge the screenshots in a reviewer session."""
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    url = change.env.ready_url if change.env else ""
    try:
        settings = store.settings()  # one snapshot: what the round records is what it ran with
        head = worktree.head(path)
        tree, out = visual.tree(path, head), store.visual_dir(change.slug, head)
        if owned := decision.decided(change, head, tree):  # the owner decided this round (TD-79)
            store.write(lock, loop.apply(owned[0], owned[1], datetime.now(UTC)))
            _calibrated(store, owned[0], out)  # after the decision is saved: it never waits on the shared repository
            return
        widths = (change.before.widths if change.before else None) or settings.widths  # pairs with before
        visual.seed(change, path, settings.seed, lambda e: store.log(lock, change.slug, e))  # TD-65
        pack = design.pack()
        shots = visual.oversize(out, visual.CAPTURE(visual.root(url), change.brief.visual, out, widths, pack=pack))
        states = {s.name: s.version for s in change.brief.visual}
        source = design.sources(path, visual.ui_paths(change, head), pack)
        found = [s.design for s in shots if s.design] + ([source] if source else [])
        scans = design.marked(found, change.before, states)
    except visual.SeedError as exc:
        result = exc.result
    except visual.BrowserMissingError as exc:
        result = visual.missing_browser(str(exc))
    except Exception as exc:  # noqa: BLE001 - a capture error is never a pass
        result = visual.broken(f"{type(exc).__name__}: {exc}"[:300])
    else:
        result, judgement, kept = None, None, None
        if shots and all(s.file for s in shots):  # a failed shot is a finding without a reviewer
            errors = visual.classify([e for s in shots for e in s.errors], change.before)
            base = sdk_adapter.Session(
                kind=StepKind.REVIEW, worktree=path, session_id="", message="", resume=False,
                policy=permissions.Policy(path, prompts.GIT_READ, write=False),
                observe=lambda: tools.Worktree(head, head), checks=(), submit=tools.VISUAL_REVIEW,
                journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)), memory=sessions.memory(store),
            )  # fmt: skip
            images = judges.blind(
                change, shots, out, store.before_dir(change.slug, change.before.head) if change.before else None
            )
            given = {"errors": errors, "scans": scans}
            mine = [("visual-review", r) for r in judges.reviews(base, change, head, shots, out, **given)]
            theirs = [("design-review", d) for d in judges.sessions(base, change, head, images, **given)]
            ran = sessions.judges(store, lock, change, [*mine, *theirs], settings)
            reviewed, designed = ran[: len(mine)], ran[len(mine) :]
            stop = next((r for r, _ in ran if r.exit == Exit.STOP), None)  # any judge left running stops the Change
            result = stop or next((r for r, run in reviewed if not isinstance(run.payload, tools.ReviewResult)), None)
            result = result or next((r for r, run in designed if r.exit != Exit.DONE and not run.payload), None)
            judgement = None if result else judges.merged([run.payload for _, run in reviewed])
            runs = ([run for _, run in reviewed], [run for _, run in designed])
            inputs = [judges.given(cfg) for _, cfg in theirs]  # kept, so a calibration replay judges the same
            kept = judges.recorded(
                change,
                head,
                tree,
                widths,
                runs=runs,
                scans=scans,
                images=images,
                settings=settings,
                now=datetime.now(UTC),
                inputs=inputs,
            )
            change.visual_rounds.append(kept)
        if judgement is not None or result is None:
            change, result = visual.judged(
                change, head, tree, shots, verdict=judgement, now=datetime.now(UTC), scans=scans, kept=kept
            )
    store.write(lock, loop.apply(change, result, datetime.now(UTC)))


def _calibrated(store: Store, change: Change, out: Path) -> None:
    """Keep a decided round for calibration in the shared repository; the decision never waits on it."""
    v, b = change.visual, change.before
    if store.shared is None or v is None or not change.visual_rounds:
        return
    before = store.before_dir(change.slug, b.head) if b else None
    images = {f"after-{f}": out / f for f in v.files}
    images |= {f"before-{f}": before / f for f in v.files if before and (before / f).is_file()}
    try:
        if notice := calibration.keep(store.shared, store.name, change.slug, change.visual_rounds[-1], images):
            _out(f"calibration: {notice}")
    except Exception as exc:  # noqa: BLE001 - calibration is evidence; the decision stands without it
        _out(f"calibration: {type(exc).__name__}: {exc}"[:300])


def _before(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """TD-24: render the brief's states at the merge-base once, before the visual check's own preview starts."""
    change.before = shots = before.capture(
        change,
        repo,
        lambda base: store.before_dir(change.slug, base),
        store.read_profile() or Profile(),
        lambda e: store.log(lock, change.slug, e),
        widths=store.settings().widths,
        seed=store.settings().seed,
    )
    store.write(lock, change)
    _out("; ".join([f"before: {len(shots.files)} screenshots at {shots.head[:7]}", *shots.findings]))


def _challenge(store: Store, lock: Lock, change: Change, cfg: sdk_adapter.Session, planned: Result) -> Result:
    """The plan's independent read-only challenge: pass keeps it; findings send it back for one more round."""
    if planned.exit != Exit.DONE or planned.plan is None:
        return planned
    verdict = sessions.reviewer(store, lock, change, cfg, "plan-challenge")
    if verdict.exit == Exit.DONE:
        return planned
    if verdict.exit in {Exit.ASK, Exit.STOP} or (verdict.operational and verdict.exit == Exit.BACK):
        return verdict
    return verdict.model_copy(
        update={"exit": Exit.RETRY, "plan": planned.plan, "reason": f"plan challenge: {verdict.reason}"}
    )


def _brief_challenge(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """J2: the challenger tests the approved brief version (TD-73); pass plans, findings go back to the owner."""
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    extra = worktree.allowed(store.read_profile() or Profile(), StepKind.REVIEW)
    cfg = sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=path,
        session_id="",
        message=prompts.brief_challenge(change, path),
        resume=False,
        policy=permissions.Policy(path, (*prompts.GIT_READ, *extra), write=False),
        observe=lambda: worktree.observe(path, change.names.target),
        checks=(),
        journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
        memory=sessions.memory(store),
    )
    change, result = loop.brief_challenge(change, sessions.reviewer(store, lock, change, cfg, "brief-challenge"))
    store.write(lock, loop.apply(change, result, datetime.now(UTC)))


def _ready(prof: Profile, path: Path, now: datetime) -> Result | None:
    """DR2 before publishing: the publishing readiness facts, their first failure as its exit."""
    host = profile.value(prof, profile.HOST, "github.com")
    return publish.gate(setup.publishing(host, setup.probe_in(path), setup.reach(host)), now)


def _engine(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, kind = datetime.now(UTC), change.step.kind
    prof = store.read_profile() or Profile()
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo), now)
    if kind in {StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE} and change.names.branch:
        path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
        change.names.worktree = str(path)
    step = ENGINE.get(kind)
    gated = _ready(prof, Path(change.names.worktree or repo), now) if kind == StepKind.PUBLISH else None
    if gated:
        result = gated
    else:
        change, result = engine.run(step, ctx, change) if step else (change, engine.unsupported(change, now))
    end = datetime.now(UTC)
    event = {"event": "step", "at": end.isoformat(timespec="seconds"), "kind": kind, "exit": result.exit}
    event |= {"reason": result.reason, "seconds": round((end - now).total_seconds(), 1)}
    store.log(lock, change.slug, event)
    store.write(lock, loop.apply(change, result, end))
    _out(json.dumps(event, default=str))


def main(argv: list[str] | None = None) -> int:
    """Take the Change lock without waiting, fold the inbox, run the next step, write its exit and exit."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next.runner")
    parser.add_argument("change")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    store = Store.open(repo)
    try:
        with store.lock(args.change) as lock:
            state, moved = engine.observe(store, repo, args.change)
            change, step = store.fold(lock, args.change, datetime.now(UTC), state, moved=moved)
            _step(store, lock, change, step, repo)
            _out(describe(store.read(args.change)))
    except LockHeldError as exc:
        _out(f"{args.change}: {exc}; another runner holds it")
    return 0


def _step(store: Store, lock: Lock, change: Change, step: Step | None, repo: Path) -> None:
    """Run the folded Change's next step; a session whose usage stayed unread stops it for the owner (TD-54)."""
    if step is not None:
        try:
            store.settings()
        except StoreError as exc:  # damaged settings stop the Change once, not every runner the host starts
            now = datetime.now(UTC)
            stop = loop.StepResult(exit=Exit.STOP, reason=str(exc), stop=exc.stop(now))
            store.write(lock, loop.apply(change, stop, now))
            return
    try:
        if step is not None and check.capturing(change):
            _visual(store, lock, change, repo)
        elif step is not None and before.due(change):
            _before(store, lock, change, repo)
        elif step is None or change.env is not None:
            _out("nothing to run; the host owns a check environment" if change.env else "nothing to run")
        elif step.kind in AGENT:
            _agent(store, lock, change, repo)
        elif step.kind == StepKind.SHAPE and loop.brief_due(change):
            _brief_challenge(store, lock, change, repo)
        else:
            _engine(store, lock, change, repo)
    except UsageUnreadError as exc:
        _gate_unread(store, lock, exc)
    except worktree.ShelveError as exc:  # the planner never starts on edits it would have to reject
        store.write(lock, loop.apply(store.read(lock.slug), _unshelved(exc), datetime.now(UTC)))


def _gate_unread(store: Store, lock: Lock, exc: UsageUnreadError) -> None:
    """TD-54: the owner decides; an agent step's own result is held so it can be accepted instead (TD-56)."""
    kept = store.read(lock.slug)  # what the step wrote before and during the session; nothing after it
    head = held.head(exc.worktree) if exc.worktree else None
    head = head if head and exc.run.head in {None, head} else None  # the result's own commit is still HEAD
    gated = loop.apply(kept, session_result.usage_gate(exc.run, kept.step.kind, accept=bool(head)), datetime.now(UTC))
    store.write(lock, gated)
    if head:  # after its question exists: a hold no question offers is never taken
        held.keep(store, lock, gated, exc.run, head)
    sessions.logged(store, lock, gated, exc.run, {"kind": kept.step.kind, "exit": Exit.ASK})


def _unshelved(exc: worktree.ShelveError) -> Result:
    """The owner clears the worktree the planner would find dirty, then planning runs again."""
    text = f"Delivery could not set aside the uncommitted edits before planning ({exc}). Commit, stash or discard them."
    cause = cause_key(ErrorKind.STATE, StepKind.PLAN, "dirty-worktree")
    return engine.ask(StepKind.PLAN, text, cause, engine.continue_or_pause(StepKind.PLAN))


if __name__ == "__main__":
    sys.exit(main())
