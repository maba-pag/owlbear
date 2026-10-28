"""The design pack OwlBear's versions bring (TD-76): the running one's in place, and a newer one in a release.

A version counts as installed only once its pack is in place (``versions.install``); a pack that failed, or the
running version's pack missing, gives every page a banner with Install. Install puts the running version's pinned
pack in place even when no newer version exists, and the pack of a version whose update failed on it.

A separate look, at most daily and whatever updating by itself is set to, reads the pack the version this machine
would take pins (``versions.target``, then its ``design_pack.json`` from ``repo.git``): it never installs or
activates anything. Pages read only what the last look kept. ``notice.json`` stays upstream's view of Impeccable's
releases, for whoever updates the pack.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import versions
from owlbear_delivery_next.state_store import registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.machine import Machine

RELEASED = "released.json"  # beside the installed packs: the last look at the pack of the version to take
STALE, RETRY = timedelta(days=1), timedelta(hours=1)  # a look's age before the next; an unknown one's
PRESENT = 60.0  # seconds a look whether the running pack is in place holds: it hashes the engine
TICK = 60.0  # seconds between the loop's looks whether a look is due


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _kept() -> dict[str, Any]:
    try:
        kept = json.loads((local_home.root() / design_pack.PACKS / RELEASED).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return kept if isinstance(kept, dict) else {}


def _due(kept: dict[str, Any]) -> bool:
    """Whether the last look is too old, unknown for an hour, or was made by another version than the running one."""
    try:
        checked = datetime.fromisoformat(kept["checked_at"])
    except KeyError, TypeError, ValueError:
        return True
    if kept.get("running") != versions.running() or kept.get("running_pack") != design_pack.manifest()["pack"]:
        return True
    return datetime.now(UTC) - checked > (RETRY if kept.get("state") == "unknown" else STALE)


def _found() -> dict[str, Any]:
    """One look: the version this machine would take and the pack it pins; fetches."""
    try:
        choice = versions.target()
    except (versions.VersionError, registry.RegistryError) as exc:
        return {"state": "unknown", "detail": f"the versions could not be read: {exc}"}
    if choice is None or not choice.tag:
        return {"state": "none", "detail": "; ".join(choice.notes) if choice else ""}
    try:
        pins = versions.pins(choice.commit)
    except versions.VersionError as exc:
        return {"state": "unknown", "version": choice.tag, "detail": f"{choice.tag}'s design pack is unreadable: {exc}"}
    return {"state": "found", "version": choice.tag, "commit": choice.commit, "pins": pins}


def look(*, force: bool = False) -> dict[str, Any]:
    """Look again when the last look is due, or when *force*d; what the pages show (``release``)."""
    if force or _due(_kept()):
        kept = _found() | {"running": versions.running(), "running_pack": design_pack.manifest()["pack"]}
        path = local_home.root() / design_pack.PACKS / RELEASED
        with contextlib.suppress(OSError):  # a hint: unwritten, it is looked at again next time
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(kept | {"checked_at": _now()}) + "\n", encoding="utf-8")
    return release()


def release() -> dict[str, Any]:
    """The last look, never fetching: ``newer`` when the version to take pins another pack than the running one.

    ``same`` (that version pins this pack) and ``none`` (no version to take) show nothing; ``unknown`` stays unknown.
    """
    kept, running = _kept(), design_pack.manifest()
    said = {"state": "unknown", "version": kept.get("version", ""), "pack": "", "running_pack": running["pack"],
            "checked_at": kept.get("checked_at"), "detail": kept.get("detail", "")}  # fmt: skip
    state, pins = kept.get("state"), kept.get("pins")
    if state == "none":
        return said | {"state": "none"}
    if state != "found" or not isinstance(pins, dict):
        return said
    taken = versions.number(said["version"]) or (0, 0)
    if taken <= (versions.number(versions.running()) or (-1, -1)):  # taken since the look
        return said | {"state": "none"}
    return said | {"state": "same" if pins == running else "newer", "pack": pins.get("pack", "")}


class Packs:
    """The machine's design pack: whether the running one is in place, a failed install, and Install."""

    def __init__(self, machine: Machine, mono: Callable[[], float] = time.monotonic) -> None:
        """Nothing failed yet; whether the pack is in place is looked at on the first read."""
        self.machine, self.mono, self.lock = machine, mono, threading.Lock()
        self.thread: threading.Thread | None = None
        self.failure: dict[str, Any] | None = None  # the last pack that failed: its version, what it said, when
        self.present: tuple[float, bool] | None = None

    def failed(self, tag: str, detail: str) -> None:
        """Keep a version's pack that could not be installed, for the pages' banner."""
        with self.lock:
            self.failure = {"version": tag, "detail": detail[:600], "at": _now()}

    def ready(self, tag: str) -> None:
        """A version's pack is in place: a failure kept for it ends."""
        with self.lock:
            if self.failure and self.failure["version"] == tag:
                self.failure = None

    def _in_place(self) -> bool:
        with self.lock:
            if self.present and self.mono() - self.present[0] < PRESENT:
                return self.present[1]
        found = design_pack.installed() is not None
        with self.lock:
            self.present = (self.mono(), found)
        return found

    def read(self) -> dict[str, Any]:
        """What every page shows: ``install`` (None, or missing, failed or installing) and ``release``."""
        with self.lock:
            installing, failure = self.thread is not None and self.thread.is_alive(), self.failure
        running, pack = versions.running(), design_pack.manifest()["pack"]
        if installing:
            install = {"state": "installing", "version": running, "pack": pack, "detail": "", "at": None}
        elif failure:
            install = {"state": "failed", "pack": pack if failure["version"] == running else ""} | failure
        elif not self._in_place():
            install = {"state": "missing", "version": running, "pack": pack, "detail": design_pack.status(), "at": None}
        else:
            install = None
        return {"install": install, "release": release()}

    def install(self) -> dict[str, Any]:
        """Install: the running version's pack when missing, and a failed version's own; refused while updating."""
        m = self.machine
        if why := m.updating or ("OwlBear is stopping" if m.stopping.is_set() else ""):
            return self.read() | {"refused": why}
        if m.updater.thread is not None and m.updater.thread.is_alive():
            return self.read() | {"refused": "an update runs; it installs the pack of the version it takes"}
        with self.lock:
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run, name="design-pack", daemon=True)
                self.thread.start()
        return self.read()

    def _run(self) -> None:
        with self.lock:
            failure = self.failure
        tag = failure["version"] if failure else versions.running()
        try:
            if not self._installed():
                design_pack.install()  # this host's own manifest: the running version's pinned pack
            if failure and tag != versions.running():
                self._version(tag)
        except Exception as exc:  # noqa: BLE001 - the banner says how it ended
            self.failed(tag, f"{type(exc).__name__}: {exc}")
            self.machine.say(f"design pack: installing failed: {exc}")
        else:
            with self.lock:
                self.failure = None
            self.machine.say("design pack: installed")
        with self.lock:
            self.present = None

    def _version(self, tag: str) -> None:
        """A version whose update failed on its pack: that pack, with the version's own interpreter and manifest."""
        folder = local_home.root() / local_home.VERSIONS / tag
        if not folder.is_dir():
            return  # removed since: the next update installs it whole
        if said := versions.pack(folder):
            raise design_pack.PackError(said)
        self.machine.updater.attempts.pop(tag, None)  # ready now: the next update takes it again

    def _installed(self) -> bool:
        with self.lock:
            self.present = None
        return self._in_place()

    def loop(self) -> None:
        """Thread: look for a newer pack in a release when the last look is due, until the machine stops."""
        while True:
            try:
                look()
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed look
                self.machine.say(f"looking for a newer design pack failed: {type(exc).__name__}: {exc}")
            if self.machine.stopping.wait(TICK):
                return
