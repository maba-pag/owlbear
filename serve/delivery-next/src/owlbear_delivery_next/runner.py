"""Process entry for one Change and one step: ``python -m owlbear_delivery_next.runner <change> [--repo PATH]``."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile, prompts, sdk_adapter, setup, tools
from owlbear_delivery_next.cli import describe
from owlbear_delivery_next.models import Environment, Exit, Profile, StepKind, Waiting
from owlbear_delivery_next.steps import cleanup, engine, follow, merge, publish, review, worktree
from owlbear_delivery_next.store import LockHeldError, Store, StoreError, git_common_dir

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Lock

AGENT = frozenset({StepKind.PLAN, StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK})
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


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _previous(store: Store, slug: str, session: str | None) -> dict[int, float | None]:
    """PIDs earlier runners persisted for *session*; they remain in the activity log when a runner is killed."""
    pids = [e.get("pids", {}) for e in store.events(slug) if e.get("event") == "pids" and e.get("session") == session]
    return {int(p): c for found in pids for p, c in found.items()}


def _others(store: Store, slug: str) -> dict[str, list[str]]:
    """Scopes of the other open Changes of this clone: their plan's task scopes, else their brief's."""
    out = {}
    for other in store.slugs():
        try:
            o = store.read(other)
        except StoreError:
            continue
        scope = [p for t in o.plan.tasks for p in t.scope] if o.plan else o.brief.scope
        if other != slug and scope and not (o.finished_at or o.intent.abandoned_at):
            out[o.handle or other] = sorted(set(scope))
    return out


def _agent(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    open_ = [q for q in change.questions if q.step == s.kind and q.answer and not q.effect_observed_at]
    answer = open_[-1] if open_ else None
    resume = bool(answer and s.session)
    if not resume:
        s.session = f"{slug}-{s.kind}-{s.task or s.mode or 'all'}-{uuid.uuid4().hex[:8]}"
    s.started_at = now
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    if s.kind == StepKind.BUILD and task and task.base is None:
        task.base = worktree.head(path)
    since = task.base if task and s.kind in {StepKind.BUILD, StepKind.REVIEW} else None
    store.write(lock, change)  # The session id and task base are durable before the runtime starts.
    others = _others(store, slug) if s.kind == StepKind.PLAN else {}
    parts = prompts.session(change, profile, path, others)

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, within = loop.charge(change, sdk_adapter.missing_cause(s.kind), datetime.now(UTC))
        change.step.session = f"{slug}-{s.kind}-{s.task or s.mode or 'all'}-{uuid.uuid4().hex[:8]}" if within else None
        store.write(lock, change)
        return change.step.session

    model = profile.models.get(s.kind)
    cfg = sdk_adapter.Session(
        kind=s.kind,
        worktree=path,
        session_id=s.session or "",
        message=prompts.answer(answer) if resume and answer else parts.message,
        resume=resume,
        policy=sdk_adapter.Policy(path, parts.allowed, write=parts.write),
        observe=lambda: worktree.observe(path, change.names.target, since),
        checks=parts.checks,
        submit=parts.submit,
        scope=tuple(change.brief.scope),
        model=None if model in {None, "", "auto"} else model,
        fresh=parts.message,
        previous=_previous(store, slug, s.session) if resume else {},
        journal=sdk_adapter.Journal(lambda e: store.log(lock, slug, e), delivered, replaced),
    )
    run = asyncio.run(sdk_adapter.run(cfg))
    end = datetime.now(UTC)
    result = review.recorded(change, parts.task, run, path, sdk_adapter.to_result(run, s.kind, end))
    _log(store, lock, change, run, {"kind": s.kind, "exit": result.exit})
    if s.kind == StepKind.PLAN and result.plan:
        message = prompts.plan_review(change, result.plan, path, others)
        planned = _challenge(store, lock, change, dataclasses.replace(cfg, message=message), result)
        result = loop.overlap_ask(planned, others)
        end = datetime.now(UTC)
    if isinstance(p := run.payload, tools.WrongPremise) and p.stage == "target" and s.kind == StepKind.BUILD:
        result = engine.needs_target(change, path, f"{p.reason} ({'; '.join(p.evidence)})", end)
    if answer and sdk_adapter.effect_seen(run):
        change = loop.effect_observed(change, answer.id, end)
    if isinstance(p := run.payload, tools.CheckRecipe) and result.exit == Exit.PENDING:
        change.env = Environment(check=s.task or "", command=p.command, directory=p.directory, ready_url=p.ready_url)
    store.write(lock, loop.apply(change, result, end))


def _log(store: Store, lock: Lock, change: Change, run: sdk_adapter.Run, fields: dict[str, object]) -> None:
    """Log one session's step event and add its usage to the Change's spend, which the log may later drop."""
    step = {"event": "step", "at": datetime.now(UTC).isoformat(timespec="seconds"), "session": run.session_id}
    step |= fields | {"ending": run.ending, "head": run.head, "usage": run.usage}
    step["termination"] = dataclasses.asdict(run.termination) if run.termination else None
    change.spend = change.spend.plus(run.usage)
    store.write(lock, change)
    store.log(lock, change.slug, step)
    _out(json.dumps(step, default=str))


def _reviewer(store: Store, lock: Lock, change: Change, cfg: sdk_adapter.Session, label: str) -> Result:
    """One fresh read-only reviewer session over ``cfg.message``; its verdict as a step result."""
    model = (store.read_profile() or Profile()).models.get(StepKind.REVIEW)
    review_cfg = dataclasses.replace(
        cfg,
        kind=StepKind.REVIEW,
        session_id=f"{lock.slug}-{label}-{uuid.uuid4().hex[:8]}",
        resume=False,
        submit=tools.REVIEW,
        checks=(),
        model=None if model in {None, "", "auto"} else model,
        fresh=cfg.message,
        previous={},
    )
    run = asyncio.run(sdk_adapter.run(review_cfg))
    verdict = sdk_adapter.to_result(run, StepKind.REVIEW, datetime.now(UTC))
    _log(store, lock, change, run, {"kind": label, "exit": verdict.exit})
    return verdict


def _challenge(store: Store, lock: Lock, change: Change, cfg: sdk_adapter.Session, planned: Result) -> Result:
    """The plan's independent read-only challenge: pass keeps it; findings send it back for one more round."""
    if planned.exit != Exit.DONE or planned.plan is None:
        return planned
    verdict = _reviewer(store, lock, change, cfg, "plan-review")
    if verdict.exit == Exit.DONE:
        return planned
    if verdict.exit in {Exit.ASK, Exit.STOP}:
        return verdict
    return verdict.model_copy(
        update={"exit": Exit.RETRY, "plan": planned.plan, "reason": f"plan review: {verdict.reason}"}
    )


def _brief_review(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """J2: the reviewer challenges the approved brief version; pass plans, findings go back to the owner."""
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    extra = worktree.allowed(store.read_profile() or Profile(), StepKind.REVIEW)
    cfg = sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=path,
        session_id="",
        message=prompts.brief_review(change, path),
        resume=False,
        policy=sdk_adapter.Policy(path, (*prompts.GIT_READ, *extra), write=False),
        observe=lambda: worktree.observe(path, change.names.target),
        checks=(),
        journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
    )
    change, result = loop.brief_review(change, _reviewer(store, lock, change, cfg, "brief-review"))
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
            if step is None or change.env is not None:
                _out("nothing to run; the host owns a check environment" if change.env else "nothing to run")
            elif step.kind in AGENT:
                _agent(store, lock, change, repo)
            elif step.kind == StepKind.SHAPE and loop.brief_due(change):
                _brief_review(store, lock, change, repo)
            else:
                _engine(store, lock, change, repo)
            _out(describe(store.read(args.change)))
    except LockHeldError as exc:
        _out(f"{args.change}: {exc}; another runner holds it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
