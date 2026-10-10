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

from owlbear_delivery_next import loop, prompts, sdk_adapter
from owlbear_delivery_next.cli import describe
from owlbear_delivery_next.models import Profile, StepKind
from owlbear_delivery_next.process_probe import ProcessTableWorktreeProbe, WorktreeProcessScanError
from owlbear_delivery_next.steps import worktree
from owlbear_delivery_next.store import LockHeldError, Store, git_common_dir

if TYPE_CHECKING:
    from owlbear_delivery_next.models import Change, Question
    from owlbear_delivery_next.store import Lock


def _pending_answer(change: Change) -> Question | None:
    open_ = [q for q in change.questions if q.step == change.step.kind and q.answer and not q.effect_observed_at]
    return open_[-1] if open_ else None


def _scan(path: Path, since: datetime) -> tuple[tuple[int, str], ...] | None:
    """Slice stand-in for the host's worktree scan, run after the runtime has exited; None when it cannot run."""
    try:
        return ProcessTableWorktreeProbe().active_processes((path,), started_after=since)
    except WorktreeProcessScanError:
        return None


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _previous(store: Store, slug: str, session: str | None) -> dict[int, float | None]:
    """PIDs earlier runners persisted for *session*; they remain in the activity log when a runner is killed."""
    pids = [e.get("pids", {}) for e in store.events(slug) if e.get("event") == "pids" and e.get("session") == session]
    return {int(p): c for found in pids for p, c in found.items()}


def _build(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    task = next(t for t in change.plan.tasks if t.id == s.task) if change.plan else None
    if task is None:
        msg = f"{slug}: build step names no plan task"
        raise RuntimeError(msg)
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    answer = _pending_answer(change)
    resume = bool(answer and s.session)
    if not resume:
        s.session = f"{slug}-{s.kind}-{s.task}-{uuid.uuid4().hex[:8]}"
    s.started_at = now
    store.write(lock, change)  # The session id is durable before the runtime starts.
    extra, pairs = profile.entries.get(f"allow:{s.kind}"), worktree.installs(profile, task.scope)
    extras = extra.value.split("\n") if extra else []
    allowed = (*sdk_adapter.GIT_BUILD, "cd", *(c for _, c in pairs), *task.checks, *extras)
    fresh = prompts.build(change, task, path, pairs, allowed)

    def delivered() -> None:
        nonlocal change
        change = loop.answer_delivered(change, answer.id if answer else "", datetime.now(UTC))
        store.write(lock, change)

    def replaced() -> str | None:
        nonlocal change
        change, within = loop.charge(change, sdk_adapter.missing_cause(StepKind.BUILD), datetime.now(UTC))
        change.step.session = f"{slug}-{s.kind}-{s.task}-{uuid.uuid4().hex[:8]}" if within else None
        store.write(lock, change)
        return change.step.session

    model = profile.models.get(StepKind.BUILD)
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=path,
        session_id=s.session or "",
        message=prompts.answer(answer) if resume and answer else fresh,
        resume=resume,
        policy=sdk_adapter.Policy(path, tuple(allowed)),
        observe=lambda: worktree.observe(path, change.names.target),
        checks=tuple(task.checks),
        model=None if model in {None, "", "auto"} else model,
        fresh=fresh,
        readback=bool(answer and answer.delivered_at),
        previous=_previous(store, slug, s.session) if resume else {},
        journal=sdk_adapter.Journal(lambda e: store.log(lock, slug, e), delivered, replaced),
    )
    run = asyncio.run(sdk_adapter.run(cfg))
    scanned = _scan(path, now)
    if scanned is None and run.termination:
        problems = (*run.termination.problems, "worktree scan failed")
        run.termination = dataclasses.replace(run.termination, confirmed=False, problems=problems)
    end = datetime.now(UTC)
    result = sdk_adapter.to_result(run, StepKind.BUILD, end, scanned or ())
    if answer and sdk_adapter.effect_seen(run):
        change = loop.effect_observed(change, answer.id, end)
    step = {
        "event": "step",
        "at": end.isoformat(timespec="seconds"),
        "session": run.session_id,
        "ending": run.ending,
        "exit": result.exit,
        "head": run.head,
        "termination": dataclasses.asdict(run.termination) if run.termination else None,
        "scanned": scanned,
        "usage": run.usage,
    }
    store.log(lock, slug, step)
    store.write(lock, loop.apply(change, result, end))
    _out(json.dumps(step, default=str))


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
            change, step = store.fold(lock, args.change, datetime.now(UTC))
            if step is None:
                _out(f"nothing to run\n{describe(change)}")
            elif step.kind != StepKind.BUILD:
                _out(f"step {step.kind} is not supported yet\n{describe(change)}")
            else:
                _build(store, lock, change, repo)
                _out(describe(store.read(args.change)))
    except LockHeldError as exc:
        _out(f"{args.change}: {exc}; another runner holds it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
