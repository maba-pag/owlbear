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

from owlbear_delivery_next import loop, profile, prompts, sdk_adapter, tools
from owlbear_delivery_next.cli import describe
from owlbear_delivery_next.models import Environment, Exit, Profile, StepKind
from owlbear_delivery_next.steps import cleanup, engine, follow, merge, publish, review, worktree
from owlbear_delivery_next.store import LockHeldError, Store, git_common_dir

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Lock

AGENT = frozenset({StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK})
ENGINE: dict[StepKind, engine.Step] = {
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


def _agent(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    open_ = [q for q in change.questions if q.step == s.kind and q.answer and not q.effect_observed_at]
    answer = open_[-1] if open_ else None
    resume = bool(answer and s.session)
    if not resume:
        s.session = f"{slug}-{s.kind}-{s.task or s.mode}-{uuid.uuid4().hex[:8]}"
    s.started_at = now
    store.write(lock, change)  # The session id is durable before the runtime starts.
    parts = prompts.session(change, profile, path)

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, within = loop.charge(change, sdk_adapter.missing_cause(s.kind), datetime.now(UTC))
        change.step.session = f"{slug}-{s.kind}-{s.task}-{uuid.uuid4().hex[:8]}" if within else None
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
        observe=lambda: worktree.observe(path, change.names.target),
        checks=parts.checks,
        submit=parts.submit,
        model=None if model in {None, "", "auto"} else model,
        fresh=parts.message,
        previous=_previous(store, slug, s.session) if resume else {},
        journal=sdk_adapter.Journal(lambda e: store.log(lock, slug, e), delivered, replaced),
    )
    run = asyncio.run(sdk_adapter.run(cfg))
    end = datetime.now(UTC)
    result = review.recorded(change, parts.task, run, path, sdk_adapter.to_result(run, s.kind, end))
    if answer and sdk_adapter.effect_seen(run):
        change = loop.effect_observed(change, answer.id, end)
    if isinstance(p := run.payload, tools.CheckRecipe) and result.exit == Exit.PENDING:
        change.env = Environment(check=s.task or "", command=p.command, directory=p.directory, ready_url=p.ready_url)
    step = {"event": "step", "at": end.isoformat(timespec="seconds"), "session": run.session_id, "kind": s.kind}
    step |= {"ending": run.ending, "exit": result.exit, "head": run.head, "usage": run.usage}
    step["termination"] = dataclasses.asdict(run.termination) if run.termination else None
    store.log(lock, slug, step)
    store.write(lock, loop.apply(change, result, end))
    _out(json.dumps(step, default=str))


def _engine(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, kind = datetime.now(UTC), change.step.kind
    prof = store.read_profile() or Profile()
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo), now)
    if kind in {StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE} and change.names.branch:
        path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
        change.names.worktree = str(path)
    step = ENGINE.get(kind)
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
            state = engine.observe(store, repo, args.change)
            change, step = store.fold(lock, args.change, datetime.now(UTC), state)
            if step is None or change.env is not None:
                _out("nothing to run; the host owns a check environment" if change.env else "nothing to run")
            elif step.kind in AGENT:
                _agent(store, lock, change, repo)
            else:
                _engine(store, lock, change, repo)
            _out(describe(store.read(args.change)))
    except LockHeldError as exc:
        _out(f"{args.change}: {exc}; another runner holds it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
