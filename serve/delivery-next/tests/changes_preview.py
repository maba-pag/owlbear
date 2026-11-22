"""A synthetic Change stopped the way c8 stopped, for tests and the Changes page's preview; never the live store.

``deadline_stopped`` builds it through the engine's own transitions: build task t1's builder runs out of time twice
(attempt 2, ``liveness:build:deadline`` counted 2), Delivery's repair starts, and the repairer's own deadline ends that
repair, so ``repairs.done[0]`` holds it and the Change stops. ``credit_stopped`` is the same record whose repairer
instead hit its credit limit: the stop is the owner's credit-limit policy stop while the outcome keeps the deadline.
Importing this file reads and writes nothing.

Run as a script, ``changes_preview.py <port>`` serves the Changes page on that stop for the owner's look before merge:
directory ``serve/delivery-next``, command ``uv run python tests/changes_preview.py {port}``, page
``http://127.0.0.1:{port}/#token=preview``; state paths open without ``#token=`` because
``metrics_preview.SEED`` supplies the token. Its only project is the registered throwaway clone ``preview-shop``,
whose store holds ``deadline_stopped`` as Change ``c1``, under complete settings so no unset-settings block hides the
rerun. It never reads the owner's data or live c8: ``main`` replaces HOME with a fresh temporary folder
(``metrics_preview._isolate``), keeps Git off GitHub and puts a ``gh`` that only fails first on PATH
(``backlog_preview._offline``). No confirmation starts a session or spends credits: the host's runner and
environment launches are held by ``launch_gate.blocked``, which prints ``LAUNCH`` once and starts nothing, and its
spawn is never reached. The machine starts unpaused, so that held launch, not Delivery's pause, keeps a Change the owner
lets run again queued; automatic curation, Retro and updates are off, and the GitHub account is chosen offline.
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    Change,
    ErrorKind,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
)
from owlbear_delivery_next.change_flow import repair_recovery, stuck
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.github import account
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import launch_gate, pages
from owlbear_delivery_next.project_host.host import Host, HostRecord, RunnerRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import carried, config
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.store import Store

__all__ = ["CAUSE", "CLONE", "LAUNCH", "NOW", "credit_stopped", "deadline_stopped"]

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
CAUSE = cause_key(ErrorKind.LIVENESS, StepKind.BUILD, "deadline")
CLONE = ("preview-shop", "https://github.com/preview/preview-shop.git")
LAUNCH = "Changes preview: a runner would start now; none starts"


def _timed_out(slug: str, worktree: str) -> Change:
    plan = Plan(tasks=[Task(id="t1", title="Show the stopped step's rerun", checks=["uv run test"])])
    c = Change(slug=slug, plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=Names(worktree=worktree))
    for _ in range(2):  # the second timeout of one cause starts Delivery's repair
        c = apply(c, StepResult(exit=Exit.RETRY, cause=CAUSE, reason="step deadline"), NOW)
    return c


def deadline_stopped(slug: str = "c1", worktree: str = "") -> Change:
    """Builder deadline twice, then the repairer's own deadline: the c8 shape."""
    c = _timed_out(slug, worktree)
    stuck.stopped(c, repair_recovery.REPAIRER_DEADLINE, NOW)
    return c


def credit_stopped(slug: str = "c1", worktree: str = "") -> Change:
    """Builder deadline twice, then the repairer's credit limit replaced the stop; the deadline cause stays."""
    c = _timed_out(slug, worktree)
    stuck.stopped(c, "its session's result was voided: credit limit reached: 5.00 of 5", NOW)
    c.stop = Stop(
        kind=ErrorKind.POLICY,
        reason="credit limit reached: 5.00 of 5",
        action="Raise the step's credit limit, or run it without one",
        resume="The step's credit limit allows it to finish",
        at=NOW,
    )
    return c


def _settings() -> None:
    """Complete settings under Global, with the automatic sessions of curation, Retro and updates off."""
    from conftest import IMPROVEMENT_MACHINE, complete_layer  # noqa: PLC0415 - the tests' complete values, beside this script

    prefs = config.Prefs(
        merge_method=MergeMethod.SQUASH,
        delete_remote_branch=False,
        ci_poll_seconds=20,
        ci_start_window_seconds=300,
        ask_before_merge=False,
    )
    config.BASE = complete_layer().model_copy(update={"prefs": prefs})
    off = {"update_when_idle": False, "update_while_paused": False} | dict.fromkeys(
        ("curate_after_merge", "curate_when_idle", "retro_after_change", "retro_when_idle"), "off"
    )
    machine_settings.BASE = carried.MACHINE.model_copy(update=IMPROVEMENT_MACHINE | off)


def _no_runner() -> None:
    """Every runner and environment launch is held and says so once; the runner's spawn is never reached."""
    said: list[str] = []

    def held(_host: Host) -> bool:
        if not said:
            said.append(LAUNCH)
            sys.stdout.write(f"{LAUNCH}\n")
            sys.stdout.flush()
        return True

    def spawn(slug: str) -> RunnerRecord:
        msg = f"the Changes preview never spawns a runner ({slug})"
        raise AssertionError(msg)

    class PreviewHost(Host):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs, spawn=spawn)

    launch_gate.blocked = held
    project.Host = PreviewHost


def _offline_account(setting: str, origin: account.Origin, *, until: float | None = None) -> Access:
    del until
    if origin == account.Origin.LOCAL:
        return Access.LOCAL
    login = account.FALLBACK if setting == account.REPOSITORY_OWNER else setting
    return Access(login, "chosen offline in the preview", origin.host, f"preview-{login}", "gh")


def seed(home: Path) -> None:
    """The shared data checkout and the registered clone, whose store holds the c8-shaped stop as ``c1``."""
    from backlog_preview import DATA, _checkout, _offline  # noqa: PLC0415 - the Backlog preview's offline setup, beside this script

    _offline(home)
    account.resolve = _offline_account
    readiness.ready = lambda _store, _repo, **_kwargs: []  # its checks ask GitHub
    DataRepo(_checkout(home / ".owlbear" / "data", DATA, home / "remotes" / "owlbear-data.git"))
    name, origin = CLONE
    clone = _checkout(home / "projects" / name, origin)
    registry.register(clone)
    (work := home / "worktrees" / "c1").mkdir(parents=True)
    store = Store.open(clone)
    with store.lock("c1") as lock:
        store.write(lock, deadline_stopped("c1", str(work)))


def main() -> None:
    from metrics_preview import TOKEN, _isolate, seed_pages  # noqa: PLC0415 - beside this script

    port = int(sys.argv[1])
    home = _isolate()

    def gone() -> None:
        shutil.rmtree(home, ignore_errors=True)

    try:
        _settings()
        _no_runner()
        seed(home)
        seed_pages(pages)
        base = f"http://127.0.0.1:{port}"
        record = HostRecord(
            url=f"{base}/", token=TOKEN, pid=os.getpid(), started_at=datetime.now(UTC), code=codebase.CURRENT
        )
        machine = Machine(record, paused=False)
        machine.load_all()
        sys.stdout.write(f"Changes preview: {base}/#token={TOKEN}\n")
        sys.stdout.flush()
        try:
            uvicorn.run(app.create(machine, gone), host="127.0.0.1", port=port, log_level="warning")
        finally:
            machine.stop_all()
    finally:  # Uvicorn replays a stop signal once it returns: the app's own end removes HOME
        gone()


if __name__ == "__main__":
    main()
