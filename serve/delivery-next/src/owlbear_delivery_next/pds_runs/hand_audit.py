"""The PDS audit started by hand (#777): the installed pages audited against the installed pin, its report kept.

It changes nothing but its report: ``pds-audit.json`` in the project's store, beside the PDS update's record. One runs
at a time, holding the machine's update lock, and never while an earlier PDS session is unproven. The host, never the
model, writes the version and commit it audited into the saved report.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable_runs import machine_lock
from owlbear_delivery_next.impeccable_runs.pack_state import MACHINE_LOCK
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.pds_runs import audit, pin, sessions
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.workflow_steps import sessions as step_sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

STATE = "pds-audit.json"
INTERRUPTED = "OwlBear stopped while the audit ran; start it again"


class Busy(Exception):  # noqa: N818 - says what happened
    """The audit cannot start now; the message says why."""


UNBOUND = "the machine's maintenance ownership is not bound; the PDS audit cannot start"


def _unbound(_cfg: Session) -> Run:
    raise Busy(UNBOUND)


class Hand:
    """The project's hand audit: its state file, its one thread and the session runner the host binds."""

    def __init__(self, store: Store, run: Callable[[Session], Run] = _unbound) -> None:
        self.store, self.run = store, run
        self.maintenance: Maintenance | None = None
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None

    @property
    def path(self) -> Path:
        """Where the last hand audit's report is kept."""
        return self.store.root / STATE

    def busy(self) -> bool:
        """Whether an audit runs now: work a project's stop waits for."""
        return self.thread is not None and self.thread.is_alive()

    def read(self) -> dict[str, Any]:
        """The last hand audit: ``none``, ``running``, ``done`` or ``failed``; one lost while running failed."""
        try:
            kept = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"state": "none"}
        except ValueError as exc:
            return {"state": "failed", "reason": f"the saved audit cannot be read: {exc}"[:300]}
        if kept.get("state") == "running" and not self.busy():
            return {**kept, "state": "failed", "reason": INTERRUPTED}
        return kept

    def start(self) -> dict[str, Any]:
        """Start an audit of the installed pages in a thread and return its state.

        Raises:
            Busy: One runs, the machine's update lock is held, an earlier PDS session is unproven, the maintenance
                ownership is unbound or the auditor's settings are unset.
        """
        with self.lock:
            if self.busy():
                raise Busy("a PDS audit is running")  # noqa: EM101, TRY003
            if self.maintenance is None:
                raise Busy(UNBOUND)
            try:
                roles.chosen(self.store.settings(), sessions.AUDIT)
            except SettingsUnset as exc:
                raise Busy(str(exc)) from None
            try:
                held = machine_lock.take(local_home.root() / MACHINE_LOCK, f"{self._name} (PDS audit)", self._unproven)
            except machine_lock.HeldError as exc:
                msg = f"an update runs for {exc.who}; one runs at a time on this machine"
                raise Busy(msg) from None
            state = {"state": "running", "started_at": datetime.now(UTC).isoformat()}
            try:
                self._save(state)
                self.thread = threading.Thread(target=self._work, args=(held, state), name="pds-audit", daemon=True)
                self.thread.start()
            except BaseException:
                os.close(held)
                raise
            return state

    @property
    def _name(self) -> str:
        return self.store.name or self.store.root.parent.parent.name

    def _unproven(self) -> None:
        if self.maintenance is not None and self.maintenance.pending(kind="pds"):
            msg = "an earlier PDS session is unproven; recover it on the Maintenance page first"
            raise Busy(msg)

    def _work(self, held: int, state: dict[str, Any]) -> None:
        try:
            with spend_ledger.at(spend_ledger.Where.of(self.store, job="PDS audit")):
                saved = {**state, **self._audit()}
        except Exception as exc:  # noqa: BLE001 - the page must learn how the audit ended
            saved = {**state, "state": "failed", "reason": f"{type(exc).__name__}: {exc}"[:600]}
        finally:
            os.close(held)
        self._save({**saved, "ended_at": datetime.now(UTC).isoformat()})

    def _audit(self) -> dict[str, Any]:
        package = pin.package()
        version, commit = pin.read(package).version, _commit(package)
        said = {"version": version, "commit": commit}
        if differs := pin.verify(package):
            return {**said, "state": "failed", "reason": f"the installed PDS files differ from their pin: {differs[0]}"}
        settings, memory = self.store.settings(), step_sessions.memory(self.store)
        assert self.maintenance is not None  # noqa: S101 - start refuses without it

        def session(at: Path, skills: Path, message: str) -> Run:
            return self.run(sessions.auditor(settings, at, skills, message, memory=memory))

        with self.maintenance.workspace("owlbear-pds-audit-") as at:
            done = audit.audit(at, web=package / "web", tree=package / pin.TREE, version=version, session=session)
        v = done.verdict
        return {
            **said, "state": "done" if v.outcome != "stop" else "failed", "outcome": v.outcome, "reason": v.reason,
            "run_id": done.run_id, "findings": [dataclasses.asdict(f) for f in v.findings],
            "follow_ups": [dataclasses.asdict(f) for f in v.follow_ups], "report": done.report,
            "markdown": done.markdown,
        }  # fmt: skip

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, json.dumps(state, indent=2) + "\n")


def _commit(package: Path) -> str:
    found = subprocess.run(  # noqa: S603 - a fixed argument list
        ["git", "-C", str(package), "rev-parse", "HEAD"],  # noqa: S607 - git from PATH, as elsewhere
        capture_output=True,
        text=True,
        check=False,
    )
    return found.stdout.strip() if found.returncode == 0 and found.stdout.strip() else "not a git checkout"
