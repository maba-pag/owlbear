"""Updating OwlBear on this machine (self-update build §5; TD-296, TD-299, TD-305, TD-352, TD-353).

One update at a time: prepare the newest version of the machine's channel beside the running one (install and
selfcheck), start it as a standby, then fence the machine (no runner, environment, background work or project
change starts) and check again that nothing runs; anything running lifts the fence and the update waits. Otherwise
the alias rename activates the new version and the host hands over to it (``handover``). A failure before the rename
leaves the running version as it was; a version that keeps failing is tried three times.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import alias, handover, registry, versions

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.machine import Machine

ATTEMPTS = 3  # tries per version before it waits for a newer one (§5.1)
FENCED = "OwlBear is updating; try again in a minute"
FINAL = frozenset({"idle", "current", "waiting", "failed"})


class Updater:
    """The machine's one update: its thread and its state, as the pages show it."""

    def __init__(self, machine: Machine) -> None:
        """No update runs yet."""
        self.machine, self.lock = machine, threading.Lock()
        self.thread: threading.Thread | None = None
        self.attempts: dict[str, int] = {}
        self.state: dict[str, Any] = {"phase": "idle", "detail": "", "version": "", "at": None}

    def read(self) -> dict[str, Any]:
        """The update's state: its phase, what it says and the version it is about."""
        with self.lock:
            return dict(self.state)

    def _set(self, phase: str, detail: str = "", version: str | None = None) -> None:
        with self.lock:
            self.state |= {"phase": phase, "detail": detail, "at": datetime.now(UTC).isoformat(timespec="seconds")}
            if version is not None:
                self.state["version"] = version
        self.machine.say(f"update: {phase}" + (f" {version}" if version else "") + (f": {detail}" if detail else ""))

    def run_now(self) -> dict[str, Any]:
        """Run updates now (TD-352, TD-353): start an update unless one runs or OwlBear stops when idle."""
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return dict(self.state)
            if self.machine.ending:
                return dict(self.state) | {"phase": "refused", "detail": "OwlBear stops once the running steps end"}
            self.thread = threading.Thread(target=self._run, name="update", daemon=True)
            self.thread.start()
        return self.read()

    def _run(self) -> None:
        try:
            self._update()
        except Exception as exc:  # noqa: BLE001 - the page learns how it ended; the running version stays
            self.machine.unfence()
            self._set("failed", f"{type(exc).__name__}: {exc}"[:600])

    def _update(self) -> None:
        self._set("looking", "fetching the versions")
        try:
            choice = versions.target()
        except (versions.VersionError, registry.RegistryError) as exc:
            self._set("failed", f"the versions could not be read: {exc}")
            return
        if choice is None or not choice.tag:
            self._set("current", "; ".join(choice.notes) if choice else "no newer version of this machine's channel")
            return
        tag = choice.tag
        if self.attempts.get(tag, 0) >= ATTEMPTS:
            self._set("failed", f"{tag} failed {ATTEMPTS} times; a later version is tried", tag)
            return
        self._set("preparing", "installing it beside the running version and checking it", tag)
        try:
            folder = versions.install(choice)
        except versions.VersionError as exc:
            self.attempts[tag] = self.attempts.get(tag, 0) + 1
            self._set("failed", str(exc), tag)
            return
        self._set("standby", "starting it beside the running version", tag)
        standby = handover.Standby(folder / ".venv" / "bin" / "python", folder, tag, local_home.root() / "host.log")
        if standby.healthy() is None:
            standby.stop()
            self.attempts[tag] = self.attempts.get(tag, 0) + 1
            self._set("failed", f"{tag} did not answer within {handover.HEALTH:.0f} s; the running version stays", tag)
            return
        self._switch(standby, folder, tag)

    def _switch(self, standby: handover.Standby, folder: Any, tag: str) -> None:  # noqa: ANN401 - a Path
        """Fence, check that nothing runs, rename the alias and hand over; or wait with what runs."""
        if left := self.machine.fence(FENCED):
            standby.stop()
            self.machine.unfence()
            self._set("waiting", f"waits for {'; '.join(left[:5])}", tag)
            return
        self._set("activating", "switching the runtime to it", tag)
        try:
            alias.activate(folder, tag)
        except Exception:
            standby.stop()
            self.machine.unfence()
            raise
        loaded = [pid for pid, p in self.machine.projects.items() if p.state == "loaded"]
        record = self.machine.record
        self.machine.handover = (standby, handover.Handover(
            port=int(record.url.rstrip("/").rsplit(":", 1)[1]), token=record.token, paused=self.machine.paused,
            ending=self.machine.ending, version=tag, loaded=loaded,
        ))  # fmt: skip
        self._set("handing over", f"OwlBear now hands over to {tag}", tag)
        self.machine.on_stop()
