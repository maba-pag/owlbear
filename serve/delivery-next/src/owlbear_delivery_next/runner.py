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
from owlbear_delivery_next.models import ErrorKind, Exit, Profile, StepKind
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


def _build(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    now, s, slug = datetime.now(UTC), change.step, change.slug
    task = next(t for t in change.plan.tasks if t.id == s.task) if change.plan else None
    if task is None:
        msg = f"{slug}: build step names no plan task"
        raise RuntimeError(msg)
    profile = store.read_profile() or Profile()
    path = worktree.ensure(repo, git_common_dir(repo), slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    installs = worktree.install(path, profile, task.scope)
    runs = [dataclasses.asdict(i) for i in installs]
    store.log(lock, slug, {"event": "install", "at": now.isoformat(timespec="seconds"), "runs": runs})
    if failed := next((i for i in installs if i.exit_code), None):
        cause = loop.cause_key(ErrorKind.PROJECT_ENV, StepKind.BUILD, failed.package)
        result = loop.StepResult(exit=Exit.RETRY, cause=cause, reason=f"`{failed.command}` failed: {failed.tail}")
        store.write(lock, loop.apply(change, result, now))
        return
    answer = _pending_answer(change)
    resume = bool(answer and s.session)
    if not resume:
        s.session = f"{slug}-{s.kind}-{s.task}-{uuid.uuid4().hex[:8]}"
    s.started_at = now
    store.write(lock, change)  # The session id is durable before the runtime starts.
    extra, pairs = profile.entries.get(f"allow:{s.kind}"), worktree.installs(profile, task.scope)
    allowed = (
        *sdk_adapter.GIT_BUILD,
        "cd",
        *(c for _, c in pairs),
        *task.checks,
        *(extra.value.split("\n") if extra else ()),
    )
    packages = [p for p, _ in pairs]
    model = profile.models.get(StepKind.BUILD)
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=path,
        session_id=s.session or "",
        message=prompts.answer(answer) if resume and answer else prompts.build(change, task, path, packages, allowed),
        resume=resume,
        policy=sdk_adapter.Policy(path, tuple(allowed)),
        observe=lambda: worktree.observe(path, change.names.target),
        checks=tuple(task.checks),
        model=None if model in {None, "", "auto"} else model,
    )
    run = asyncio.run(sdk_adapter.run(cfg))
    scanned = _scan(path, now)
    if scanned is None and run.termination:
        problems = (*run.termination.problems, "worktree scan failed")
        run.termination = dataclasses.replace(run.termination, confirmed=False, problems=problems)
    end = datetime.now(UTC)
    result = sdk_adapter.to_result(run, StepKind.BUILD, end, scanned or ())
    if answer and run.delivered:
        change = loop.effect_observed(change, answer.id, end)
    step = {
        "event": "step",
        "at": end.isoformat(timespec="seconds"),
        "session": run.session_id,
        "resumed": resume,
        "ending": run.ending,
        "exit": result.exit,
        "runtime_pid": run.runtime_pid,
        "recorded_pids": sorted(run.pids),
        "termination": dataclasses.asdict(run.termination) if run.termination else None,
        "scanned": scanned,
        "usage": run.usage,
    }
    for event in [*run.events, step]:
        store.log(lock, slug, event)
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
