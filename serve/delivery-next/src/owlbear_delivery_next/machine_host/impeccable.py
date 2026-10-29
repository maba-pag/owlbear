"""Impeccable OwlBear's versions bring (TD-76): the running one's in place, and a newer one in a release.

A version counts as installed only once its pack is in place (``versions.install``); a pack that failed, or the
running version's pack missing, gives every page a banner with Install. Install puts the running version's pinned
pack in place even when no newer version exists, and the pack of a version whose update failed on it.

A separate look, the OwlBear update check's (``update_checks``) whatever updating by itself is set to, reads the
pack the version this machine would take pins (``versions.target``, then its ``impeccable.json`` from ``repo.git``):
it never installs or activates anything. Pages read only what the last look kept. ``notice.json`` stays upstream's
view of Impeccable's releases, for whoever updates the pack.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import versions
from owlbear_delivery_next.state_store import machine_settings, registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.machine import Machine

RELEASED = "released.json"  # beside the installed packs: the last look at the pack of the version to take
FAILED = "failed.json"  # beside it: the last pack that failed, kept across restarts until it is installed
PRESENT = 60.0  # seconds a look whether the running pack is in place holds: it hashes the engine
ANY = object()  # _keep without an expected failure
MOVED = "the update channel changed since the last check"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _kept() -> dict[str, Any]:
    try:
        kept = json.loads((local_home.root() / pack_files.PACKS / RELEASED).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return kept if isinstance(kept, dict) else {}


def _channel() -> str | None:
    """This machine's update channel as resolved now; None when its settings cannot be read."""
    try:
        return machine_settings.current().channel
    except registry.RegistryError:
        return None


def _found() -> dict[str, Any]:
    """One look: the version this machine would take on its channel and the pack it pins; fetches."""
    channel = _channel()
    try:
        choice = versions.target(channel)  # the channel kept with the look is the one it ran on
    except (versions.VersionError, registry.RegistryError) as exc:
        return {"state": "unknown", "detail": f"the versions could not be read: {exc}"}
    if choice is None or not choice.tag:
        return {"state": "none", "detail": "; ".join(choice.notes) if choice else "", "channel": channel}
    try:
        pins = versions.pins(choice.commit)
    except versions.VersionError as exc:
        detail = f"{choice.tag}'s Impeccable is unreadable: {exc}"
        return {"state": "unknown", "version": choice.tag, "detail": detail, "channel": channel}
    return {"state": "found", "version": choice.tag, "commit": choice.commit, "pins": pins, "channel": channel}


def checked() -> dict[str, Any]:
    """Look now and keep it for the pages; what was found: ``state``, the ``version`` to take and ``detail``."""
    kept = _found() | {"running": versions.running(), "running_pack": pack_files.manifest()["pack"]}
    path = local_home.root() / pack_files.PACKS / RELEASED
    with contextlib.suppress(OSError):  # a hint: unwritten, it is looked at again by the next check
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(kept | {"checked_at": _now()}) + "\n", encoding="utf-8")
    return kept


def look() -> dict[str, Any]:
    """Look now; what the pages show (``release``)."""
    checked()
    return release()


def release() -> dict[str, Any]:
    """The last look, never fetching: ``newer`` when the version to take pins another pack than the running one.

    ``same`` (that version pins this pack) and ``none`` (no version to take) show nothing; ``unknown`` stays unknown,
    and so does a look on another channel than this machine's now, until the next look.
    """
    kept, running = _kept(), pack_files.manifest()
    said = {"state": "unknown", "version": kept.get("version", ""), "pack": "", "running_pack": running["pack"],
            "checked_at": kept.get("checked_at"), "detail": kept.get("detail", "")}  # fmt: skip
    state, pins = kept.get("state"), kept.get("pins")
    if state in {"none", "found"} and kept.get("channel") != _channel():
        return said | {"detail": MOVED}
    if state == "none":
        return said | {"state": "none"}
    if state != "found" or not isinstance(pins, dict):
        return said
    taken = versions.number(said["version"]) or (0, 0)
    if taken <= (versions.number(versions.running()) or (-1, -1)):  # taken since the look
        return said | {"state": "none"}
    return said | {"state": "same" if pins == running else "newer", "pack": pins.get("pack", "")}


class Impeccable:
    """The machine's Impeccable: whether the running one is in place, a failed install, and Install."""

    def __init__(self, machine: Machine, mono: Callable[[], float] = time.monotonic) -> None:
        """The failure kept before a restart, if any; whether the pack is in place is looked at on the first read."""
        self.machine, self.mono, self.lock = machine, mono, threading.Lock()
        self.thread: threading.Thread | None = None
        self.target = ""  # the version the running Install puts in place
        self.present: tuple[float, bool] | None = None
        self.failure: dict[str, Any] | None = self._restored()  # the last pack that failed: its version, what, when

    def _restored(self) -> dict[str, Any] | None:
        """The failure ``failed.json`` keeps; an unreadable one is itself a failure the banner says."""
        path = local_home.root() / pack_files.PACKS / FAILED
        try:
            kept = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            kept = exc
        if not (isinstance(kept, dict) and all(isinstance(kept.get(k), str) for k in ("version", "detail", "at"))):
            said = f"the kept Impeccable failure {path} is unreadable: {kept}"[:600]
            self.machine.say(f"Impeccable: {said}")
            return {"version": "", "detail": said, "at": None}
        return {k: kept[k] for k in ("version", "detail", "at")}

    def _keep(self, failure: dict[str, Any] | None, expected: object = ANY) -> None:
        """Hold *failure* and write it to ``failed.json``; None ends it and removes the file.

        With *expected*, nothing changes once the held failure is another than that one.
        """
        path = local_home.root() / pack_files.PACKS / FAILED
        with self.lock:
            if expected is not ANY and self.failure is not expected:
                return
            self.failure = failure
            try:
                if failure is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_name(f".{FAILED}.tmp")
                    tmp.write_text(json.dumps(failure) + "\n", encoding="utf-8")
                    tmp.replace(path)
            except OSError as exc:  # the banner holds it until the host ends
                self.machine.say(f"Impeccable: the failure could not be kept in {path}: {exc}")

    def failed(self, tag: str, detail: str, expected: object = ANY) -> None:
        """Keep a version's pack that could not be installed, for the pages' banner, also across restarts."""
        self._keep({"version": tag, "detail": detail[:600], "at": _now()}, expected)

    def ready(self, tag: str) -> None:
        """A version's pack is in place: a failure kept for it ends."""
        with self.lock:
            failure = self.failure
        if failure is not None and failure["version"] == tag:
            self._resolved(failure)  # one kept meanwhile, for a newer version, stays

    def _applies(self, failure: dict[str, Any]) -> bool:
        """Whether a kept failure still wants Install: its version is there, not older, not running with its pack."""
        tag, running = failure["version"], versions.running()
        if not tag:
            return True  # an unreadable record: Install ends it
        if tag == running:
            return not self._in_place()
        older = (versions.number(tag) or (0, 0)) < (versions.number(running) or (-1, -1))
        return not older and (local_home.root() / local_home.VERSIONS / tag).is_dir()

    def _in_place(self) -> bool:
        with self.lock:
            if self.present and self.mono() - self.present[0] < PRESENT:
                return self.present[1]
        found = pack_files.installed() is not None
        with self.lock:
            self.present = (self.mono(), found)
        return found

    def read(self) -> dict[str, Any]:
        """What every page shows: ``install`` (None, or missing, failed or installing) and ``release``."""
        with self.lock:
            installing, failure, target = self.thread is not None and self.thread.is_alive(), self.failure, self.target
        if failure and not installing and not self._applies(failure):
            self._resolved(failure)
            failure = None
        running, pack = versions.running(), pack_files.manifest()["pack"]
        if installing:
            install = {
                "state": "installing",
                "version": target,
                "pack": pack if target == running else "",
                "detail": "",
                "at": None,
            }
        elif failure:
            install = {"state": "failed", "pack": pack if failure["version"] == running else ""} | failure
        elif not self._in_place():
            install = {"state": "missing", "version": running, "pack": pack, "detail": pack_files.status(), "at": None}
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
                failure = self.failure
                self.target = (failure["version"] if failure else "") or versions.running()  # unreadable: none named
                self.thread = threading.Thread(target=self._run, args=(failure, self.target), name="impeccable",
                                               daemon=True)  # fmt: skip
                self.thread.start()
        return self.read()

    def _run(self, failure: dict[str, Any] | None, tag: str) -> None:
        try:
            if not self._installed():
                pack_files.install()  # this host's own manifest: the running version's pinned pack
            if tag != versions.running():
                self._version(tag)
        except Exception as exc:  # noqa: BLE001 - the banner says how it ended
            self.failed(tag, f"{type(exc).__name__}: {exc}", expected=failure)  # an update's newer one stays
            self.machine.say(f"Impeccable: installing failed: {exc}")
        else:
            self._resolved(failure)
            self.machine.say("Impeccable: installed")
        with self.lock:
            self.present = None

    def _resolved(self, failure: dict[str, Any] | None) -> None:
        """End *failure*, the one this install set out to repair; one an update kept meanwhile stays."""
        self._keep(None, expected=failure)

    def _version(self, tag: str) -> None:
        """A version whose update failed on its pack: that pack, with the version's own interpreter and manifest."""
        folder = local_home.root() / local_home.VERSIONS / tag
        if not folder.is_dir():
            return  # removed since: the next update installs it whole
        if said := versions.pack(folder):
            raise pack_files.PackError(said)
        self.machine.updater.attempts.pop(tag, None)  # ready now: the next update takes it again

    def _installed(self) -> bool:
        with self.lock:
            self.present = None
        return self._in_place()
