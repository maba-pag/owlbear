"""Updating OwlBear on this machine (self-update build §5; TD-296, TD-299, TD-305, TD-352, TD-353).

One update at a time: prepare the newest version of the machine's channel beside the running one (install,
selfcheck and its Impeccable), start it as a standby, then fence the machine (no runner, environment, background
work or project change starts) and check again that nothing runs; anything running lifts the fence and the update
waits. Otherwise
the alias rename activates the new version and the host hands over to it (``handover``). A failure before the rename
leaves the running version as it was; a version that keeps failing is tried three times.

Each update reports its ten steps (``update_steps``). Start update now refuses while work runs (``unstartable``);
Run updates now still waits for it (TD-353).
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import alias, handover, update_steps, versions
from owlbear_delivery_next.state_store import registry

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.machine_host.machine import Machine

ATTEMPTS = 3  # tries per version before it waits for a newer one (§5.1)
RECHECK = 5.0  # seconds between looks whether the steps an update waits for ended
FENCED = "OwlBear is updating; try again in a minute"
SHOWN = 5  # running steps a refusal names


class Updater:
    """The machine's one update: its thread and its state, as the pages show it."""

    def __init__(self, machine: Machine) -> None:
        """No update runs yet."""
        self.machine, self.lock = machine, threading.Lock()
        self.thread: threading.Thread | None = None
        self.attempts: dict[str, int] = {}
        self.auto, self.uses = False, 0  # an automatic update, and the owner's use counted when it started
        self.state: dict[str, Any] = {"phase": "idle", "detail": "", "version": "", "at": None}
        self.steps = update_steps.Steps(machine.say)

    def read(self) -> dict[str, Any]:
        """The update's state: its phase, what it says and the version it is about."""
        with self.lock:
            return dict(self.state)

    def report(self) -> dict[str, Any]:
        """The state with its steps and log, and whether Start update now may start one now, or why not."""
        why = self.unstartable()
        return self.read() | self.steps.read() | {"startable": not why, "reason": why}

    def unstartable(self) -> str:
        """Why Start update now refuses now (D-01M63CC7CYSMN156SJEBVFAXTQ): an update, a stop or work running."""
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return "An update runs now"
        if self.machine.stopping.is_set():
            return "OwlBear is stopping"
        if self.machine.ending:
            return "OwlBear stops once the running steps end"
        if left := self.machine.busy():
            more = f" and {len(left) - SHOWN} more" if len(left) > SHOWN else ""
            return f"Work runs now: {'; '.join(left[:SHOWN])}{more}"
        return ""

    def took_over(self, loaded: list[str]) -> None:
        """This host took over as the new version: the handover ends once every project it had loaded loads here."""
        tag = self.machine.updated
        here = {p.entry.id for p in list(self.machine.projects.values()) if p.state == "loaded"}
        left = [pid for pid in loaded if pid not in here]
        said = f"{tag} took over at the same address; {len(loaded) - len(left)} of {len(loaded)} projects loaded"
        self.steps.took_over(tag, "failed" if left else "done", said)

    def _set(self, phase: str, detail: str = "", version: str | None = None) -> None:
        if phase in {"failed", "refused"}:  # the step it ended in, with its own line when it set one
            self.steps.end("failed" if phase == "failed" else "stopped", detail)
        with self.lock:
            self.state |= {"phase": phase, "detail": detail, "at": datetime.now(UTC).isoformat(timespec="seconds")}
            if version is not None:
                self.state["version"] = version
        self.machine.say(f"update: {phase}" + (f" {version}" if version else "") + (f": {detail}" if detail else ""))

    def run_now(self, *, auto: bool = False) -> dict[str, Any]:
        """Run updates now (TD-352, TD-353): start an update unless one runs or OwlBear stops.

        An *auto* update, after an announcement (§7), gives way to the owner: any use, his settings or new work end it.
        """
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return dict(self.state)
            self.auto, self.uses = auto, self.machine.auto.uses
            if why := self._cancelled():
                return dict(self.state) | {"phase": "refused", "detail": why}
            self.thread = threading.Thread(target=self._run, name="update", daemon=True)
            self.thread.start()
        return self.read()

    def _cancelled(self, *, working: bool = False) -> str:
        """Why the update may not go on: a stop, or a stop when idle the owner asked for (a stop wins, §5)."""
        if self.machine.stopping.is_set():
            return "OwlBear is stopping"
        if self.machine.ending:
            return "OwlBear stops once the running steps end"
        if self.auto and self.machine.auto.uses != self.uses:
            return "postponed: you used OwlBear"
        if self.auto and not self.machine.auto.permitted():
            return "postponed: updating by itself is off now"
        return "postponed: work started" if self.auto and working else ""

    def _run(self) -> None:
        try:
            self._update()
        except Exception as exc:  # noqa: BLE001 - the page learns how it ended; the running version stays
            if self.machine.handover is None:  # after the rename nothing goes back to the older version
                self.machine.unfence()
            self._set("failed", f"{type(exc).__name__}: {exc}"[:600])

    def _update(self) -> None:
        self.steps.begin()
        self.steps.mark("looking", "running", "fetching the versions")
        self._set("looking", "fetching the versions")
        try:
            choice = versions.target()
        except (versions.VersionError, registry.RegistryError) as exc:
            self._set("failed", f"the versions could not be read: {exc}")
            return
        if choice is None or not choice.tag:
            said = "; ".join(choice.notes) if choice else "no newer version of this machine's channel"
            self.steps.mark("looking", "done", said)
            self._set("current", said)
            return
        tag = choice.tag
        self.steps.about(tag)
        if self.attempts.get(tag, 0) >= ATTEMPTS:
            self._set("failed", f"{tag} failed {ATTEMPTS} times; a later version is tried", tag)
            return
        self.steps.mark("looking", "done", f"{tag} is the newest version this machine takes")
        if (folder := self._prepared(choice)) is None:
            return
        while not (why := self._cancelled()):
            if left := self.machine.busy():  # the request stays: it goes on once they end (TD-353)
                if why := self._cancelled(working=True):  # an automatic one gives way to new work instead
                    break
                self.steps.mark("waiting", "running", f"waits for {'; '.join(left[:5])}")
                self._set("waiting", f"waits for {'; '.join(left[:5])}", tag)
                self.machine.stopping.wait(RECHECK)
                continue
            self.steps.mark("waiting", "done", "nothing runs")
            try:
                if self._switch(folder, tag):
                    return
            except versions.VersionError as exc:
                self._set("failed", str(exc), tag)
                return
        self._set("refused", why, tag)

    def _prepared(self, choice: versions.Choice) -> Path | None:
        """The version installed, checked and its Impeccable in place; None when that failed, said and counted."""
        tag = choice.tag
        self._set("preparing", "installing it beside the running version and checking it", tag)
        try:
            folder = versions.install(choice, self.steps.mark)
        except versions.VersionError as exc:
            self.attempts[tag] = self.attempts.get(tag, 0) + 1
            if isinstance(exc, versions.PackInstallError):  # every page offers Install for it
                self.machine.impeccable.failed(tag, str(exc))
            self._set("failed", str(exc), tag)
            return None
        self.machine.impeccable.ready(tag)
        return folder

    def _switch(self, folder: Path, tag: str) -> bool:
        """A standby, the fence, a last look that nothing runs, the rename and the handover; False to wait again.

        Raises:
            versions.VersionError: The standby never answered; the running version stays.
        """
        self.steps.mark("standby", "running", f"starting {tag} beside the running version")
        self._set("standby", "starting it beside the running version", tag)
        standby = handover.Standby(folder / ".venv" / "bin" / "python", folder, tag, local_home.root() / "host.log")
        self.steps.mark("standby", "done", f"{tag} started")
        self.steps.mark("health", "running", f"waiting up to {handover.HEALTH:.0f} s for {tag} to answer")
        if standby.healthy() is None:
            standby.stop()
            self.attempts[tag] = self.attempts.get(tag, 0) + 1
            msg = f"{tag} did not answer within {handover.HEALTH:.0f} s; the running version stays"
            raise versions.VersionError(msg)
        self.steps.mark("health", "done", f"{tag} answered")
        self.steps.mark("switching", "running", "nothing starts now; a last look that nothing runs")
        left = self.machine.fence(FENCED)
        if left or self._cancelled():
            standby.stop()
            self.machine.unfence()
            return False
        self._set("activating", "switching the runtime to it", tag)
        try:
            alias.activate(folder, tag)  # the one activation point: raises only before the rename
        except Exception:
            standby.stop()
            self.machine.unfence()
            raise
        self.steps.mark("switching", "done", f"the runtime is now {tag}")
        loaded = [pid for pid, p in self.machine.projects.items() if p.state == "loaded"]
        record = self.machine.record
        self.machine.handover = (standby, handover.Handover(
            port=int(record.url.rstrip("/").rsplit(":", 1)[1]), token=record.token, paused=self.machine.paused,
            ending=self.machine.ending, version=tag, loaded=loaded,
        ))  # fmt: skip
        self.steps.mark("handover", "running", f"OwlBear hands over to {tag}")  # the record its new host reads
        self._set("handing over", f"OwlBear now hands over to {tag}", tag)
        self.machine.on_stop()
        return True
