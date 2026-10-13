"""One runner's agent sessions: run them in the profile's runtime, log their usage, and run fresh read-only judges."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, roles, sdk_adapter, session_result, tools, vscode_adapter
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.profile_record import Profile

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.config import Settings
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Lock, Store

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


def run(store: Store, cfg: sdk_adapter.Session) -> session_result.Run:
    """Run one agent session where the profile's runtime says (TD-35), screenshots included (C7)."""
    if (store.read_profile() or Profile()).runtime == "vscode":
        return vscode_adapter.run(cfg, store.root / "steps" / f"{uuid.uuid4().hex}.json")
    done = asyncio.run(sdk_adapter.run(cfg))
    if unread(done):
        raise UsageUnreadError(done)
    return done


def unread(done: session_result.Run) -> bool:
    """Its usage could not be read while its processes are confirmed gone; else the termination stop wins."""
    return bool(done.usage_unread and done.termination and done.termination.confirmed)


def logged(store: Store, lock: Lock, change: Change, done: session_result.Run, fields: dict[str, object]) -> None:
    """Log one session's step event and add its usage to the Change's spend, which the log may later drop."""
    step = {"event": "step", "at": datetime.now(UTC).isoformat(timespec="seconds"), "session": done.session_id}
    step |= fields | {"ending": done.ending, "head": done.head, "usage": done.usage}
    step["termination"] = dataclasses.asdict(done.termination) if done.termination else None
    change.spend = change.spend.plus(done.usage, done.session_id)
    store.write(lock, change)
    store.log(lock, change.slug, step)
    out(json.dumps(step, default=str))


def reviewer(store: Store, lock: Lock, change: Change, cfg: sdk_adapter.Session, label: str) -> Result:
    """One fresh read-only reviewer session over ``cfg.message``; its verdict as a step result."""
    return review_run(store, lock, change, cfg, label)[0]


def review_run(  # noqa: PLR0913 - the visual review has its own result schema
    store: Store, lock: Lock, change: Change, cfg: sdk_adapter.Session, label: str, *, submit: tools.Spec = tools.REVIEW
) -> tuple[Result, session_result.Run]:
    """The reviewer session's verdict and its run, whose payload is the submitted review."""
    return judges(store, lock, change, [(label, dataclasses.replace(cfg, submit=submit))])[0]


def judges(
    store: Store,
    lock: Lock,
    change: Change,
    sessions: list[tuple[str, sdk_adapter.Session]],
    settings: Settings | None = None,
) -> list[tuple[Result, session_result.Run]]:
    """Fresh read-only judges: together on the SDK, one after another in the window, which shares one worktree.

    *settings* is the round's snapshot, so what is recorded is what ran. A judge left running stops the Change ahead
    of another's unread usage; otherwise an unread run is gated and nothing is processed (TD-54).
    """
    settings = settings or store.settings()
    cfgs = []
    for label, cfg in sessions:
        role = roles.chosen(settings, label)
        session_id, model, effort = f"{lock.slug}-{label}-{uuid.uuid4().hex[:8]}", role.model, role.effort
        cfgs.append(
            dataclasses.replace(
                cfg, kind=StepKind.REVIEW, session_id=session_id, resume=False, checks=(), model=model,
                effort=effort, context=role.context, fresh=cfg.message, previous={},
            )
        )  # fmt: skip
    if len(cfgs) == 1 or (store.read_profile() or Profile()).runtime == "vscode":
        runs = [run(store, cfg) for cfg in cfgs]
    else:
        runs = asyncio.run(_together(cfgs))
    judged = []
    for (label, _cfg), done in zip(sessions, runs, strict=True):  # state writes one at a time, under the lock
        verdict = session_result.to_result(done, StepKind.REVIEW, datetime.now(UTC), change.step.kind)
        if not unread(done):
            logged(store, lock, change, done, {"kind": label, "exit": verdict.exit})
        judged.append((verdict, done))
    left = any(not (r.termination and r.termination.confirmed) for r in runs)
    if (first := next((r for r in runs if unread(r)), None)) and not left:
        raise UsageUnreadError(first)
    return judged


async def _together(cfgs: list[sdk_adapter.Session]) -> list[session_result.Run]:
    """Every judge runs to its own end, teardown included, before any error of one goes on."""
    done = await asyncio.gather(*(sdk_adapter.run(cfg) for cfg in cfgs), return_exceptions=True)
    if error := next((d for d in done if isinstance(d, BaseException)), None):
        raise error
    return [d for d in done if not isinstance(d, BaseException)]
