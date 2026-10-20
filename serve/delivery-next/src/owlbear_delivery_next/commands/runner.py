"""Process entry for one Change and one step: ``python -m owlbear_delivery_next run <change> [--repo PATH]``."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import permissions, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import VISUAL, Environment, ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import budgets, disputes, loop, plan_rounds, repairs, worktree
from owlbear_delivery_next.change_flow.curation_flow import CURATE
from owlbear_delivery_next.commands.cli import describe
from owlbear_delivery_next.design_packs import design_tools
from owlbear_delivery_next.local_system import git_files
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.pack_runs import visual_settled
from owlbear_delivery_next.project_host import host
from owlbear_delivery_next.runtimes import (
    amendments,
    readiness,
    sdk_adapter,
    session_result,
    step_decisions,
    step_input,
)
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.store import LockHeldError, Store, StoreError
from owlbear_delivery_next.workflow_steps import (
    amend,
    before,
    brief_round,
    check,
    cleanup,
    conversation,
    curation,
    curation_build,
    decisions_gate,
    design,
    engine,
    follow,
    held,
    judges,
    merge,
    overlap,
    plan_round,
    prepare,
    publish,
    queue,
    review,
    session_choice,
    sessions,
    visual,
)
from owlbear_delivery_next.workflow_steps.sessions import UsageUnreadError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.state_store.store import Lock

AGENT = frozenset({StepKind.PLAN, StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK})
READ_ONLY = frozenset({StepKind.PLAN, StepKind.REVIEW})  # their sessions run in the Change's read-only worktree
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


def _agent(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    answer, accepted, repair, resume = session_choice.opening(store, lock, change, task)
    s.started_at = now
    review.started(change, task, path, store.settings())  # a build's base; a plan task's loop (TD-208)
    since = task.base if task and s.kind in {StepKind.BUILD, StepKind.REVIEW} else None
    start = worktree.head(path) if s.kind == StepKind.INTEGRATE else None
    store.write(lock, change)  # The session id and task base are durable before the runtime starts.
    others = _planning(store, lock, slug, path) if s.kind == StepKind.PLAN else {}

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, new = session_choice.replaced(store, lock, change, repair)
        return new

    role = roles.chosen(store.settings(), s.kind)
    ctx = prepare.context(store, change, store.settings(), path) if s.kind == StepKind.CHECK else None  # TD-107

    def config(at: Path) -> sdk_adapter.Session:
        parts = step_input.session(change, profile, at, others, ctx)
        told = parts.message + (repairs.fallback(task) if repair else "")  # a fresh session taking a repair chance
        return sdk_adapter.Session(
            kind=s.kind,
            worktree=at,
            session_id=s.session or "",
            message=step_decisions.resumed(step_input.answer(answer))
            if resume and answer
            else (parts.message if resume else told),
            resume=resume,
            policy=permissions.Policy(at, write=parts.write),
            observe=lambda: worktree.observe(at, change.names.target, since),
            checks=parts.checks,
            submit=parts.submit,
            scope=tuple(change.brief.scope),
            model=role.model,
            effort=role.effort,
            limit=roles.limit(store.settings(), s.kind),
            context=role.context,
            fresh=told,
            previous=_previous(store, slug, s.session) if resume else {},
            journal=sdk_adapter.Journal(
                lambda e: store.log(lock, slug, e), delivered, replaced, lambda d: store.write_now(lock, slug, d)
            ),
            item=task.item if task and task.item and s.kind == StepKind.BUILD else None,
            rejectable=disputes.rejectable(task) if s.kind == StepKind.BUILD else plan_rounds.rejectable(change),
            settled=disputes.settled(task) if s.kind == StepKind.BUILD else plan_rounds.settled(change),
            rechecks=disputes.pending(disputes.target(change, task)) if s.kind == StepKind.REVIEW else (),
            cap=disputes.cap(change),
            plan_tasks=disputes.planned(change),
            amendable=amendments.amendable(change),
            subagents=roles.subagents(store.settings(), s.kind),  # TD-374, TD-376: the role's setting
            memory=sessions.memory(store),
            ui=change.brief.ui,
            helpers=((design_tools.SCAN, partial(design.builder_scan, at)),)
            if s.kind == StepKind.BUILD and change.brief.ui  # the builder's design detector (slice 7)
            else (),
            preparing=ctx,
        )

    curated = change.tests is not None and s.kind == StepKind.BUILD and s.task == CURATE  # the curator's (TD-339)
    made = (lambda at: curation_build.curator(config(at), change, store.settings())) if curated else config
    run = accepted or _kept(store, lock, change, path, made)
    end = datetime.now(UTC)
    # The session's callbacks replace ``change``; objects taken from it before the session are stale.
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    curation_build.recorded(change, run, path)
    result = review.recorded(change, task, run, path, session_result.to_result(run, s.kind, end))
    result = disputes.processed(change, task, run.session_id, run.payload, result)
    result = amend.challenge(store, lock, change, path, run, result=result)  # TD-179: judged, never applied here
    result = conversation.disputed(task, run.payload, result)
    conversation.respond(task, run.payload, run.head, result.exit)
    sessions.logged(
        store, lock, change, run, {"kind": s.kind, "exit": result.exit} | ({"held": True} if accepted else {})
    )
    if s.kind == StepKind.PLAN and result.plan:  # recorded, then challenged in its loop (TD-190)
        result = plan_round.planned(store, lock, change, path, run.payload, result, profile, others)
        overlap.record(change, result, others, path)
        end = datetime.now(UTC)
    result = overlap.integrated(store, change, path, (start, run.ending), result)
    if isinstance(p := run.payload, tools.WrongPremise) and (p.stage, s.kind, result.exit) == TARGET:
        result = engine.needs_target(change, path, f"{p.reason} ({'; '.join(p.evidence)})", end)
    change = budgets.effect_observed(change, answer.id, end) if answer and session_result.effect_seen(run) else change
    if ctx is not None:
        result = prepare.chosen(store, change, path, run.payload, ctx, result)
    if isinstance(p := run.payload, tools.CheckRecipe) and result.exit == Exit.PENDING:
        change.env = Environment(check=s.task or "", command=p.command, directory=p.directory, ready_url=p.ready_url)
    store.write(lock, loop.apply(change, result, end))


def _kept(
    store: Store, lock: Lock, change: Change, path: Path, config: Callable[[Path], sdk_adapter.Session]
) -> session_result.Run:
    """The step's own session, a read-only one in the Change's read-only worktree.

    An unread one names the Change worktree, whose HEAD is the commit judged, so the gate can hold its result (TD-56).
    """

    def own(cfgs: list[sdk_adapter.Session]) -> list[session_result.Run]:
        try:
            return [sessions.run(store, cfgs[0])]
        except UsageUnreadError as exc:
            exc.worktree = path
            raise

    if change.step.kind in READ_ONLY:
        return sessions.isolated(store, lock, change, path, lambda at: [config(at)], own)[0]
    return own([config(path)])[0]


def _planning(store: Store, lock: Lock, slug: str, path: Path) -> dict[str, list[str]]:
    """The read-only planner needs a clean tree: edits an earlier step left are kept in a stash first.

    Returns:
        The other open Changes' scopes the planner avoids.
    """
    message = f"owlbear {slug}: uncommitted edits before planning"
    if worktree.shelve(path, message):
        store.log(lock, slug, {"event": "shelved", "at": datetime.now(UTC).isoformat(timespec="seconds")})
        _out(f"{slug}: uncommitted edits kept in `git stash list` as '{message}'")
    return plan_round.scopes(store, slug)


def _visual(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """B23: capture the brief's states from the ready environment and judge the screenshots in a reviewer session."""
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    url = change.env.ready_url if change.env else ""
    mine, theirs, ran = [], [], []  # the judges' sessions and how they ended
    try:
        settings = store.settings()  # one snapshot: what the round records is what it ran with
        head = worktree.head(path)
        tree, out = visual.tree(path, head), store.visual_dir(change.slug, head)
        widths = (change.before.widths if change.before else None) or settings.widths  # pairs with before
        if visual_settled.settled(store, lock, change, (head, tree, widths), out):
            return
        prepare.stepped(change, prepared=prepare.read(store, change.slug, VISUAL) is not None)  # TD-96
        pack = design.pack()
        shots = visual.oversize(out, visual.CAPTURE(visual.root(url), change.brief.visual, out, widths, pack=pack))
        states = {s.name: s.version for s in change.brief.visual}
        source = design.sources(path, visual.ui_paths(change, head), pack)
        found = [s.design for s in shots if s.design] + ([source] if source else [])
        scans = design.marked(found, change.before, states)
    except prepare.PrepareError as exc:
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
                policy=permissions.Policy(path, write=False),
                observe=lambda: tools.Worktree(head, head), checks=(), submit=tools.VISUAL_REVIEW,
                journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)), memory=sessions.memory(store),
            )  # fmt: skip
            images = judges.blind(
                change, shots, out, store.before_dir(change.slug, change.before.head) if change.before else None
            )
            given = {"errors": errors, "scans": scans}
            mine = [("visual-review", r) for r in judges.reviews(base, change, head, shots, out, **given)]
            theirs = [("design-review", d) for d in judges.sessions(base, change, head, images, **given)]
            ran = sessions.judges(store, lock, change, path, lambda _at: [*mine, *theirs], settings, hold=True)
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
    if ran:  # after the round and its question are saved: a failed log never loses the gate (TD-94)
        sessions.log_held(store, lock, [label for label, _ in [*mine, *theirs]], [run for _, run in ran])


def _before(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """TD-24: render the brief's states at the merge-base once, before the visual check's own preview starts."""
    settings, log = store.settings(), lambda e: store.log(lock, change.slug, e)
    change.before = shots = before.capture(
        change,
        repo,
        lambda base: store.before_dir(change.slug, base),
        store.read_profile() or Profile(),
        log,
        widths=settings.widths,
        prepare=prepare.merge_base(store, change, settings, log),
    )
    store.write(lock, change)
    _out("; ".join([f"before: {len(shots.files)} screenshots at {shots.head[:7]}", *shots.findings]))


def _ready(prof: Profile, path: Path, now: datetime) -> Result | None:
    """DR2 before publishing: the publishing readiness facts, their first failure as its exit."""
    host = profile.value(prof, profile.HOST, "github.com")
    return publish.gate(readiness.publishing(host, git_files.probe_in(path), readiness.reach(host)), now)


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


def _reused(store: Store, lock: Lock, change: Change) -> bool:
    """Check prep without an agent: this check's last launched recipe, while still valid and its inputs unchanged.

    Otherwise the recipe is forgotten and an agent prepares again.
    """
    r, s, now = change.recipe, change.step, datetime.now(UTC)
    if s.kind != StepKind.CHECK or r is None:
        return False
    root = Path(change.names.worktree)
    recipe = tools.CheckRecipe(command=r.command, directory=r.directory, ready_url=r.ready_url, summary="reused")
    held = r.check == (s.task or "") and root.is_dir() and not tools.check_recipe(recipe, tools.Worktree("", ""), root)
    held = held and prepare.reusable(store, change, store.settings())  # its preparation still declared and permitted
    if not (held and r.inputs and worktree.launch_inputs(root, r.directory) == r.inputs):
        change.recipe = None
        store.write(lock, change)
        return False
    change.env = Environment(check=r.check, command=r.command, directory=r.directory, ready_url=r.ready_url)
    reason = f"starting `{r.command}` for the check, as it last launched"
    result = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, reason=reason)
    event = {"event": "step", "at": now.isoformat(timespec="seconds"), "kind": StepKind.CHECK, "exit": result.exit}
    store.log(lock, change.slug, event | {"reason": reason})
    store.write(lock, loop.apply(change, result, now))
    _out(json.dumps(event | {"reason": reason}, default=str))
    return True


def main(argv: list[str] | None = None) -> int:
    """Take the Change lock without waiting, fold the inbox, run the next step, write its exit and exit."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next run")
    parser.add_argument("change")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--sessions", type=int, default=None)  # its grant (TD-336); unlimited when run by hand
    args = parser.parse_args(argv)
    sessions.GRANT = args.sessions
    repo = args.repo.resolve()
    found = project_home.current(repo)  # before Store.open, which may write or move it
    if found and host.stale(host.running(Store(found))):
        _out(f"{args.change}: {host.RESTART}")
        return 1
    store = Store.open(repo)
    try:
        with store.lock(args.change) as lock:
            state, moved = engine.observe(store, repo, args.change)
            leave = queue.barrier(store, repo)
            change, step = store.fold(lock, args.change, datetime.now(UTC), state, moved=moved, leave=leave)
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
    with decisions_gate.gated(store, lock, change, step) as passed:
        if passed is None:  # a gone check's end runs whatever the decisions say
            prepare.ran(store, lock, store.read(lock.slug), repo, runnable=False)
        else:
            _run(store, lock, passed, step, repo)


def _run(  # noqa: C901 - one branch per phase
    store: Store, lock: Lock, change: Change, step: Step | None, repo: Path
) -> None:
    """The step's phase: a test copy's end, the visual capture, "before", a test review, an agent or engine step."""
    try:
        if prepare.ran(store, lock, change, repo, runnable=step is not None):  # a gone check's end; a test copy
            _out(f"{change.slug}: test preparation ran")
        elif step is not None and check.capturing(change):
            _visual(store, lock, change, repo)
        elif step is not None and before.due(change):
            _before(store, lock, change, repo)
        elif step is None or change.env is not None:
            _out("nothing to run; the host owns a check environment" if change.env else "nothing to run")
        elif step.kind == StepKind.TESTS:  # a test review's reviewers (TD-373)
            curation.run(store, lock, change, repo)
        elif step.kind in AGENT:
            agent = _reused(store, lock, change) or prepare.refused(store, lock, change)
            agent = (
                agent or review.completed(store, lock, change, repo) or plan_round.continued(store, lock, change, repo)
            )
            agent or _agent(store, lock, change, repo)
        elif step.kind == StepKind.SHAPE and brief_round.due(change):  # TD-221: before approval
            brief_round.run(store, lock, change, repo)
        else:
            _engine(store, lock, change, repo)
    except UsageUnreadError as exc:
        _gate_unread(store, lock, exc)
    except sessions.SessionGrantError as exc:
        now = datetime.now(UTC)
        store.write(lock, loop.apply(store.read(lock.slug), exc.result(now), now))
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
    label = {"label": exc.label} if exc.label else {}  # whose session it was, when not the step's own (TD-376)
    sessions.logged(store, lock, gated, exc.run, {"kind": kept.step.kind, "exit": Exit.ASK} | label)


def _unshelved(exc: worktree.ShelveError) -> Result:
    """The owner clears the worktree the planner would find dirty, then planning runs again."""
    text = f"Delivery could not set aside the uncommitted edits before planning ({exc}). Commit, stash or discard them."
    cause = cause_key(ErrorKind.STATE, StepKind.PLAN, "dirty-worktree")
    return engine.ask(StepKind.PLAN, text, cause, engine.continue_or_pause(StepKind.PLAN))
