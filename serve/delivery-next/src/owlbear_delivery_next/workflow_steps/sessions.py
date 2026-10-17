"""One runner's agent sessions: run them in the profile's runtime, log their usage, and run fresh read-only judges."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import in_window
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, session_result, vscode_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.workflow_steps import disposable, ro_installs

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store

type Result = loop.StepResult


class UsageUnreadError(Exception):
    """A session whose model check could not run; its run is never processed unless the owner accepts it."""

    def __init__(self, run: session_result.Run) -> None:
        super().__init__(run.usage_unread)
        self.run = run
        self.worktree: Path | None = None  # set for an agent step's own session, whose result may be held (TD-56)


def out(text: str) -> None:
    """One line on the runner's output."""
    sys.stdout.write(text + "\n")


def memory(store: Store) -> Path | None:
    """The project's memory folder in the shared repository (TD-72); none without one, so the clone stays clean."""
    if store.shared is None:
        return None
    folder = store.shared.memory_path(store.name)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run(store: Store, cfg: sdk_adapter.Session, *, hold: bool = False) -> session_result.Run:
    """Run one agent session where the profile's runtime says (TD-35), screenshots included (C7).

    Either runtime's unknown model stops the Change for the owner (TD-94), unless the caller *holds* the run to
    decide it with others, as a visual round does.
    """
    if in_window(store.read_profile()):
        done = vscode_adapter.run(cfg, store.root / "steps" / f"{uuid.uuid4().hex}.json")
    else:
        done = asyncio.run(sdk_adapter.run(cfg))
    if unread(done) and not (hold and held(done)):
        raise UsageUnreadError(done)
    return done


def held(done: session_result.Run) -> bool:
    """A judge's verdict whose model is unknown, which its round decides with the owner; any other ending gates."""
    return unread(done) and done.ending == "result" and done.payload is not None


def log_held(store: Store, lock: Lock, labels: list[str], runs: list[session_result.Run]) -> None:
    """Log the held verdicts once their round and its question are saved, so a failed log never loses the gate."""
    for label, done in zip(labels, runs, strict=True):
        if held(done):
            logged(store, lock, store.read(lock.slug), done, {"kind": label, "exit": "held"})


def unread(done: session_result.Run) -> bool:
    """Its model is unknown while its processes are confirmed gone; else the termination stop wins.

    A voided read-only run is not: its violation decides the step, its usage is logged as it is. A known wrong model
    is not either: it reruns once after a wait (TD-94).
    """
    confirmed = done.termination and done.termination.confirmed
    voided = done.ending in {"read-only-write", "shared-git-changed"} or done.model_check == "mismatch"
    return bool(done.usage_unread and confirmed and not voided)


def logged(store: Store, lock: Lock, change: Change, done: session_result.Run, fields: dict[str, object]) -> None:
    """Log one session's step event and add its usage to the Change's spend, which the log may later drop.

    A held run's usage was added when its gate logged it.
    """
    step = {"event": "step", "at": datetime.now(UTC).isoformat(timespec="seconds"), "session": done.session_id}
    step |= fields | {"ending": done.ending, "head": done.head, "usage": done.usage, "model": done.model_check}
    step |= {"usage_unread": done.usage_unread} if done.usage_unread else {}
    step |= {"subagents": done.subagents} if done.subagents else {}  # within the usage, never added to the spend
    step["termination"] = dataclasses.asdict(done.termination) if done.termination else None
    if done.usage.get("error") != "held":
        change.spend = change.spend.plus(done.usage, done.session_id)
    store.write(lock, change)
    store.log(lock, change.slug, step)
    out(json.dumps(step, default=str))


def reviewer(  # noqa: PLR0913, PLR0917 - the session is made in the read-only worktree of the source
    store: Store, lock: Lock, change: Change, source: Path, made: Callable[[Path], sdk_adapter.Session], label: str
) -> Result:
    """One fresh read-only reviewer session over the message *made* gives; its verdict as a step result."""
    return review_run(store, lock, change, source, made, label)[0]


def review_run(  # noqa: PLR0913, PLR0917 - the visual review has its own result schema
    store: Store,
    lock: Lock,
    change: Change,
    source: Path,
    made: Callable[[Path], sdk_adapter.Session],
    label: str,
    *,
    submit: tools.Spec = tools.REVIEW,
) -> tuple[Result, session_result.Run]:
    """The reviewer session's verdict and its run, whose payload is the submitted review."""
    return judges(store, lock, change, source, lambda at: [(label, dataclasses.replace(made(at), submit=submit))])[0]


def judges(  # noqa: PLR0913, PLR0917 - the round's settings snapshot
    store: Store,
    lock: Lock,
    change: Change,
    source: Path,
    made: Callable[[Path], list[tuple[str, sdk_adapter.Session]]],
    settings: Settings | None = None,
    *,
    hold: bool = False,
) -> list[tuple[Result, session_result.Run]]:
    """Fresh read-only judges in the read-only worktree of *source*: together on the SDK, in turn in the window.

    *made* builds the judges' sessions in that worktree, which the window resets before each judge. *settings* is the
    round's snapshot, so what is recorded is what ran. A judge left running stops the Change ahead of another's unread
    usage; otherwise an unread run is gated and nothing is processed (TD-54), unless *hold* keeps it for the round's
    own decision (TD-94).
    """
    settings = settings or store.settings()
    labels: list[str] = []

    def fresh(at: Path) -> list[sdk_adapter.Session]:
        cfgs = []
        for label, cfg in made(at):
            role = roles.chosen(settings, label)
            session_id, model, effort = f"{lock.slug}-{label}-{uuid.uuid4().hex[:8]}", role.model, role.effort
            journal = sdk_adapter.Journal(event=cfg.journal.event, now=cfg.journal.now)  # never the judged step's
            labels.append(label)
            cfgs.append(
                dataclasses.replace(
                    cfg, role=cfg.role or roles.SESSIONS[label], kind=StepKind.REVIEW, session_id=session_id,
                    resume=False, checks=(), model=model, effort=effort, context=role.context, fresh=cfg.message,
                    previous={}, journal=journal, worktree=at, policy=Policy(at, write=False),
                    judging=label in tools.VERDICTS, job=label,
                )
            )  # fmt: skip
        return cfgs

    def ran(cfgs: list[sdk_adapter.Session]) -> list[session_result.Run]:
        return [run(store, cfgs[0], hold=hold)] if len(cfgs) == 1 else asyncio.run(_together(cfgs))

    window = in_window(store.read_profile())
    runs = isolated(store, lock, change, source, fresh, ran, each=window)
    judged = []
    for label, done in zip(labels, runs, strict=True):  # state writes one at a time, under the lock
        verdict = session_result.to_result(done, StepKind.REVIEW, datetime.now(UTC), change.step.kind)
        if not unread(done):
            logged(store, lock, change, done, {"kind": label, "exit": verdict.exit})
        judged.append((verdict, done))
    left = any(not (r.termination and r.termination.confirmed) for r in runs)
    if (first := next((r for r in runs if unread(r) and not (hold and held(r))), None)) and not left:
        raise UsageUnreadError(first)
    return judged


def isolated(  # noqa: PLR0913, PLR0917 - the sessions are made for, and run in, the worktree it prepares
    store: Store,
    lock: Lock,
    change: Change,
    source: Path,
    make: Callable[[Path], list[sdk_adapter.Session]],
    go: Callable[[list[sdk_adapter.Session]], list[session_result.Run]],
    *,
    each: bool = False,
) -> list[session_result.Run]:
    """Run read-only sessions in the Change's read-only worktree at *source*'s HEAD; refs they change void their runs.

    It stays for the next session, its window with it. When Delivery may not reset it, or its last sessions'
    processes are not confirmed gone, no session runs: every run is refused. *each* prepares it before each session,
    else once for them all.
    """
    copy = disposable.prepare(source, store, change.slug)
    if isinstance(copy, str):
        return _refused(store, lock, change, copy, make(source))
    note = ro_installs.ready(store, lock, change, copy.path)
    cfgs = make(copy.path)
    runs = _within(store, lock, change, copy, _noted(cfgs[:1] if each else cfgs, note), go)
    for cfg in cfgs[1:] if each else []:
        again = disposable.prepare(source, store, change.slug)
        if isinstance(again, str):
            runs += _refused(store, lock, change, again, [cfg])
        else:
            note = ro_installs.ready(store, lock, change, again.path)
            runs += _within(store, lock, change, again, _noted([cfg], note), go)
    return runs


def _noted(cfgs: list[sdk_adapter.Session], note: str) -> list[sdk_adapter.Session]:
    """The sessions told which dependencies could not be installed, so a failing check is not taken for the code's."""
    if not note:
        return cfgs
    return [
        dataclasses.replace(c, message=f"{c.message}\n\n{note}", fresh=f"{c.fresh}\n\n{note}" if c.fresh else "")
        for c in cfgs
    ]


def _refused(
    store: Store, lock: Lock, change: Change, why: str, cfgs: list[sdk_adapter.Session]
) -> list[session_result.Run]:
    at = datetime.now(UTC).isoformat(timespec="seconds")
    store.log(lock, change.slug, {"event": "read-only-refused", "at": at, "why": why})
    done = Termination(confirmed=True)  # no session started
    return [session_result.Run(c.session_id, "read-only-refused", detail=why, termination=done) for c in cfgs]


def _within(  # noqa: PLR0913, PLR0917 - the sessions run in the prepared copy
    store: Store,
    lock: Lock,
    change: Change,
    copy: disposable.Copy,
    cfgs: list[sdk_adapter.Session],
    go: Callable[[list[sdk_adapter.Session]], list[session_result.Run]],
) -> list[session_result.Run]:
    disposable.begin(store.root / "changes" / change.slug, copy.path)
    try:
        runs = go(cfgs)
    except UsageUnreadError as exc:
        _closed(store, lock, change, copy, [exc.run])
        if len(cfgs) > 1 or unread(exc.run):
            raise
        return [exc.run]  # voided: the violation, not the unread usage, decides the step
    _closed(store, lock, change, copy, runs)
    return runs


def _closed(store: Store, lock: Lock, change: Change, copy: disposable.Copy, runs: list[session_result.Run]) -> None:
    at, ids = datetime.now(UTC).isoformat(timespec="seconds"), [r.session_id for r in runs]
    if changes := disposable.tampered(copy):
        reason = f"a read-only step changed shared Git settings: {'; '.join(changes)}"
        store.log(lock, change.slug, {"event": "read-only-tampered", "at": at, "changes": changes, "sessions": ids})
        for r in runs:
            r.ending, r.payload, r.first, r.head, r.detail = "shared-git-changed", None, None, None, reason[:300]
    elif moved := disposable.changed(copy):
        reason = f"a read-only step changed the repository: {', '.join(moved)}"
        store.log(lock, change.slug, {"event": "read-only-violation", "at": at, "refs": moved, "sessions": ids})
        for r in runs:
            r.ending, r.payload, r.first, r.head, r.detail = "read-only-write", None, None, None, reason
    if all(r.termination and r.termination.confirmed for r in runs):
        disposable.settled(store.root / "changes" / change.slug)


async def _together(cfgs: list[sdk_adapter.Session]) -> list[session_result.Run]:
    """Every judge runs to its own end, teardown included, before any error of one goes on."""
    done = await asyncio.gather(*(sdk_adapter.run(cfg) for cfg in cfgs), return_exceptions=True)
    if error := next((d for d in done if isinstance(d, BaseException)), None):
        raise error
    return [d for d in done if not isinstance(d, BaseException)]
