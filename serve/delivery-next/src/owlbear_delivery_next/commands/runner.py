"""Process entry for one Change and one step: ``python -m owlbear_delivery_next run <change> [--repo PATH]``."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import permissions, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import VISUAL, Environment, ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import (
    amending,
    budgets,
    disputes,
    loop,
    plan_rounds,
    repairs,
    shaping_capture,
    stuck,
    worktree,
)
from owlbear_delivery_next.change_flow.curation_flow import CURATE
from owlbear_delivery_next.commands import worker_input
from owlbear_delivery_next.commands.cli import describe
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.impeccable_runs import visual_settled
from owlbear_delivery_next.local_system import git_files
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.project_host import host
from owlbear_delivery_next.runtimes import (
    amendments,
    command_marks,
    readiness,
    sdk_adapter,
    session_result,
    step_answers,
    step_decisions,
    step_input,
)
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import github_writer, project_home, spend_ledger
from owlbear_delivery_next.state_store.store import LockHeldError, Store, StoreError
from owlbear_delivery_next.workflow_steps import (
    amendment,
    before,
    brief_round,
    captures,
    check,
    clarification,
    cleanup,
    conversation,
    curation,
    curation_build,
    decision_publication,
    decisions_gate,
    design,
    engine,
    follow,
    held,
    held_writes,
    judges,
    lookup,
    merge,
    overlap,
    pending_child,
    plan_round,
    prepare,
    project_checks,
    publish,
    queue,
    review,
    session_choice,
    sessions,
    step_repair,
    unset_settings,
    visual,
    watched,
    worker_questions,
)
from owlbear_delivery_next.workflow_steps.sessions import UsageUnreadError

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.github.account import Writer
    from owlbear_delivery_next.state_store.store import Lock

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
_kept = held.kept_session


def _agent(store: Store, lock: Lock, change: Change, repo: Path) -> None:  # noqa: C901, PLR0915 - session lifecycle
    now, s, slug = datetime.now(UTC), change.step, change.slug
    if held.settled(store, lock, change) or (profile := project_checks.profile_for(store, lock, change, repo)) is None:
        return  # its result is recorded already (RUN-04), or the owner settles the project's checks first (#968)
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    if worker_questions.continued(store, lock, change, path):
        return
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    curated = change.tests is not None and s.kind == StepKind.BUILD and s.task == CURATE  # the curator's (TD-339)
    role = roles.chosen(settings := store.settings(), session := curation_build.LABEL if curated else s.kind)
    if stopped := overlap.starting(change, task):
        store.write(lock, loop.apply(change, stopped, now))
        return
    look_limit = watched.needed(
        settings
    )  # before anything is recorded: an unset Spotter setting asks, leaving no open span
    review.started(change, task, path, settings)  # one snapshot, checked before anything is taken (TD-208)
    answer, accepted, repair, resume = session_choice.opening(store, lock, change, task)  # unset settings take nothing
    s.started_at = now
    since = task.base if task and s.kind in {StepKind.BUILD, StepKind.REVIEW} else None
    start = worktree.head(path) if s.kind == StepKind.INTEGRATE else since
    store.write(lock, change)  # The session id and task base are durable before the runtime starts.
    others = worker_input.planning(store, lock, slug, path) if s.kind == StepKind.PLAN else {}

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, new = session_choice.replaced(store, lock, change, repair)
        return new

    ctx = prepare.context(store, change, settings, path) if s.kind == StepKind.CHECK else None  # TD-107
    asked = lookup.Asked(store, lock, lambda: change)  # the worker's lookup_decisions (TD-456)

    def config(at: Path) -> sdk_adapter.Session:
        parts = step_input.session(change, profile, at, others, ctx)
        told = (
            parts.message
            + (repairs.fallback(task) if repair else "")
            + (step_answers.answer(answer) if s.question_errors and answer else "")
            + (worker_questions.feedback(s.question_errors) if s.question_errors else "")
        )
        return sdk_adapter.Session(
            kind=s.kind,
            worktree=at,
            session_id=s.session or "",
            message=step_decisions.resumed(told)
            if resume and s.question_errors
            else step_decisions.resumed(step_answers.answer(answer))
            if resume and answer
            else told,
            resume=resume,
            policy=permissions.Policy(at, write=parts.write),
            observe=lambda: worktree.observe(at, change.names.target, since),
            checks=parts.checks,
            packages=parts.packages,
            submit=parts.submit,
            scope=tuple(change.brief.scope),
            model=role.model,
            effort=role.effort,
            limit=roles.limit(settings, session),
            context=role.context,
            fresh=told,
            previous=sessions.previous(store, slug, s.session) if resume else {},
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
            subagents=roles.subagents(settings, session),  # TD-374, TD-376: the role's setting
            user=roles.user_config(settings),  # D-01M5YE4P5317N1HWD0QN6N05E0: the owner's own instructions and skills
            memory=sessions.memory(store),
            ui=change.brief.ui,
            helpers=worker_input.helpers(change, at, asked),
            preparing=ctx,
            watch=watched.watching(store, lock, session, settings, at, _out, look_limit, asked),  # W1a's switch
        )

    made = (lambda at: curation_build.curator(config(at), change, settings)) if curated else config
    run = accepted or asked.settled(partial(_kept, store, lock, change, path, made))
    end = datetime.now(UTC)
    # The session's callbacks replace ``change``; objects taken from it before the session are stale.
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    curation_build.recorded(change, run, path)
    post = held_writes.Deferred(store, slug) if accepted else store  # an accepted hold's writes wait for its receipt
    result = session_result.to_result(run, s.kind, end)
    private = run.ending == "ask" and result.cause == cause_key(ErrorKind.RESULT, s.kind, worker_questions.LABEL)
    kept = worker_questions.unbound(post, lock, change, run, run.checks) if private else None
    if kept is None:
        sessions.logged(
            post, lock, change, run, {"kind": s.kind, "exit": result.exit} | ({"held": True} if accepted else {})
        )
    if ctx is not None:
        try:
            result = prepare.chosen(post, lock, change, path, run.payload, ctx, result)
        except (OSError, subprocess.SubprocessError) as exc:
            why = f"the preparer's cleanup failed: {failure(exc)}"
            post.log(lock, slug, {"event": "preparer-cleanup-failed", "at": end.isoformat(), "reason": why})
            result = check.failed_cleanup(result, why)
    if kept is not None:
        if result.cause == cause_key(ErrorKind.RESULT, s.kind, worker_questions.LABEL):
            worker_questions.bound(kept, lock, change, path)
            worker_questions.continued(kept, lock, change, path)
            return
        change.pending_question, change.pending_child = None, None
    result = review.recorded(change, task, run, path, result)
    result = disputes.processed(change, task, run.session_id, run.payload, result, run.changed)
    result = review.delegated(change, task, result)
    result = conversation.disputed(change, task, run.payload, result)
    conversation.respond(task, run.payload, run.head, result.exit)
    change = budgets.effect_observed(change, answer.id, end) if answer and session_result.effect_seen(run) else change
    events: list[dict[str, object]] = []
    if s.kind == StepKind.PLAN and result.plan:  # recorded, then challenged in its loop (TD-190)
        result = plan_round.planned(post, lock, change, path, run.payload, result, profile, others, events)
        overlap.record(change, result, others, path)
        end = datetime.now(UTC)
    result = overlap.integrated(post, lock, change, path, (start, run.ending), result)
    if isinstance(p := run.payload, tools.WrongPremise) and (p.stage, s.kind, result.exit) == TARGET:
        writer = github_writer.of(store, repo)
        result = engine.needs_target(change, path, f"{p.reason} ({'; '.join(p.evidence)})", end, writer)
    if isinstance(p := run.payload, tools.CheckRecipe) and result.exit == Exit.PENDING:
        change.env = Environment(check=s.task or "", command=p.command, directory=p.directory, ready_url=p.ready_url)
        before.reset(change, worktree.head(path))  # each new environment's capture gets its own "before"
    if isinstance(p := run.payload, tools.WrongPremise) and p.stage == "brief" and result.exit == Exit.BACK:
        amending.premised(change, p, run.session_id, end)  # TD-185: run before this step goes on; a stop wins
    final = change if change.amending is not None else loop.apply(change, result, end)
    held_writes.write_result(store, lock, change, accepted, final, post)
    sessions.announce_all(store, lock, slug, events)  # logged once the result that counts their round is durable


def _captured(change: Change, path: Path, head: str, out: Path, widths: list[int]) -> tuple[list[Any], list[Any]]:
    """The states to redo captured at *widths* from the ready environment, and the design scans they and the UI hold."""
    pack, url = design.pack(), check.url(change.env) if change.env else ""
    redo = visual.redone(change, head, visual.tree(path, head))
    shots = visual.oversize(out, visual.CAPTURE(visual.root(url), redo, out, widths, pack=pack))
    states = {s.name: s.version for s in change.brief.visual}
    source = design.sources(path, visual.ui_paths(change, head), pack)
    found = [s.design for s in shots if s.design] + ([source] if source else [])
    return shots, design.marked(found, change.before, states)


def _visual(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """B23: capture the brief's states from the ready environment and judge the screenshots in a reviewer session."""
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    mine, theirs, ran = [], [], []  # the judges' sessions and how they ended
    settings = store.settings()  # one snapshot: what the round records is what it ran with
    try:
        head = worktree.head(path)
        tree, out = visual.tree(path, head), store.visual_dir(change.slug, head)
        widths = (change.before.widths if change.before else None) or settings.widths  # pairs with before
        if visual_settled.settled(store, lock, change, (head, tree, widths or []), out):
            return  # the owner's decision on a captured round needs no judge
        settings.need(*(() if widths else ("widths",)), "design_failures", "agents.reviewer", "agents.design-judge")
        prepare.stepped(change, prepared=prepare.read(store, change.slug, VISUAL) is not None)  # TD-96
        shots, scans = _captured(change, path, head, out, widths)
    except SettingsUnset:  # the runner's handler asks the owner: never a capture error
        raise
    except prepare.PrepareError as exc:
        result = exc.result
    except visual.BrowserMissingError as exc:
        result = visual.missing_browser(str(exc))
    except Exception as exc:  # noqa: BLE001 - a capture error is never a pass
        result = visual.broken(worktree.failure(exc))
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
            failed = (r for r, run in designed if r.exit != Exit.DONE and (r.setup or not run.payload))
            result = result or next(failed, None)
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


def _ready(prof: Profile, path: Path, now: datetime, writer: Writer) -> Result | None:
    """DR2 before publishing: the publishing readiness facts, their first failure as its exit."""
    host = profile.value(prof, profile.HOST, "github.com")
    return publish.gate(readiness.publishing(host, git_files.probe_in(path), readiness.reach(host), writer), now)


def _engine(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, kind = datetime.now(UTC), change.step.kind
    prof = store.read_profile() or Profile()
    writer = github_writer.of(store, repo)
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo, writer), now, writer)
    if kind in {StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE} and change.names.branch:
        path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
        change.names.worktree = str(path)
    step = ENGINE.get(kind)
    gated = _ready(prof, Path(change.names.worktree or repo), now, writer) if kind == StepKind.PUBLISH else None
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
    before.reset(change, worktree.head(root))
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
        with store.lock(args.change) as lock, command_marks.marking(store, lock, args.change):
            state, moved = engine.observe(store, repo, args.change)
            leave = queue.barrier(store, repo)
            change, step = store.fold(lock, args.change, datetime.now(UTC), state, moved=moved, leave=leave)
            kind = step.kind.value if step is not None else ""
            spend_ledger.enter(spend_ledger.Where.of(store, repo, change=args.change, step=kind))  # every session's
            try:
                _step(store, lock, change, step, repo)
            except Exception as exc:  # the owner reads it in Recent activity; runner.log gets it and its traceback
                at = datetime.now(UTC).isoformat()
                failed = {"event": "runner-failed", "at": at, "reason": failure(exc)}
                sessions.announce(store, lock, args.change, failed)
                raise
            _out(describe(store.read(args.change)))
    except LockHeldError as exc:
        _out(f"{args.change}: {exc}; another runner holds it")
    return 0


def _step(store: Store, lock: Lock, change: Change, step: Step | None, repo: Path) -> None:
    """Run the folded Change's next step; a session whose usage stayed unread stops it for the owner (TD-54)."""
    if (settled := pending_child.retired(store, lock, change)) is not change:  # a captured child's gate: it decides
        change, step = settled, loop.next_step(settled, datetime.now(UTC))  # a left child counts once (retired)
    if (pending := held.uncounted(store, change)) is not None:  # a held session counts before anything else runs
        held.counted_hold(store, lock, pending)
        return
    if step is not None:
        try:
            store.settings()
        except StoreError as exc:  # damaged settings stop the Change once, not every runner the host starts
            now = datetime.now(UTC)
            stop = loop.StepResult(exit=Exit.STOP, reason=failure(exc), stop=exc.stop(now))
            store.write(lock, loop.apply(change, stop, now))
            return
        try:
            if (resumed := decision_publication.resume(store, lock, change, datetime.now(UTC))) is None:
                return
            if step.kind in AGENT and (resumed := clarification.checked(store, lock, resumed)) is None:
                return  # TD-461: the clarification's check asked the owner, or waits to run again
        except SettingsUnset as exc:
            unset_settings.asked(store, lock, exc)
            return
        change = resumed
    try:
        with decisions_gate.gated(store, lock, change, step) as passed:
            if passed is None:  # a gone check's end runs whatever the decisions say
                prepare.ran(store, lock, store.read(lock.slug), repo, runnable=False)
            else:
                _run(store, lock, passed, step, repo)
    except SettingsUnset as exc:  # the gate's reassessment picks with the picker's settings (TD-459)
        unset_settings.asked(store, lock, exc)


def _run(store: Store, lock: Lock, change: Change, step: Step | None, repo: Path) -> None:  # noqa: C901, PLR0912
    """The step's phase: a test copy's end, a capture, a test review, an agent, a brief challenge or an engine step."""
    try:
        if prepare.ran(store, lock, change, repo, runnable=step is not None):  # a gone check's end; a test copy
            _out(f"{change.slug}: test preparation ran")
        elif step is not None and stuck.bound(change):  # a stuck step's repair runs first (#1066)
            step_repair.run(store, lock, change, repo)
        elif step is not None and check.capturing(change):
            _visual(store, lock, change, repo)
        elif step is not None and before.due(change):
            _out(captures.at_merge_base(store, lock, change, repo))
        elif step is None or change.env is not None:
            _out("nothing to run; the host owns a check environment" if change.env else "nothing to run")
        elif step.kind == StepKind.TESTS or change.amending is not None:
            (curation.run if step.kind == StepKind.TESTS else amendment.run)(store, lock, change, repo)
        elif step.kind in AGENT:
            agent = _reused(store, lock, change)
            agent = agent or prepare.refused(store, lock, change) or review.completed(store, lock, change, repo)
            agent = agent or plan_round.continued(store, lock, change, repo)
            agent or _agent(store, lock, change, repo)
        elif shaping_capture.owed(change):  # the draft's pages, before its challenge and the chat's wait
            _out(f"{change.slug}: {captures.at_target(store, lock, change, repo)}")
        elif step.kind == StepKind.SHAPE and brief_round.due(change):  # TD-221: before approval
            brief_round.run(store, lock, change, repo)
        else:
            _engine(store, lock, change, repo)
    except UsageUnreadError as exc:
        held.gate_unread(store, lock, exc)
    except sessions.SessionGrantError as exc:
        now = datetime.now(UTC)
        store.write(lock, loop.apply(store.read(lock.slug), exc.result(now), now))
    except worktree.ShelveError as exc:  # the planner never starts on edits it would have to reject
        now = datetime.now(UTC)
        reason = failure(exc)
        store.log(lock, lock.slug, {"event": "not-shelved", "at": now.isoformat(timespec="seconds"), "reason": reason})
        store.write(lock, loop.apply(store.read(lock.slug), plan_round.unshelved(reason), now))
    except SettingsUnset as exc:
        unset_settings.asked(store, lock, exc)
