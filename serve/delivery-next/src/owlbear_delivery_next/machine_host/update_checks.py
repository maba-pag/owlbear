"""Update checks (D-01M63CCVRK8ZKFENY9F4A2K11A): whether OwlBear, PDS and Impeccable have a newer version.

Each is checked when the host starts, then every so many hours, its own machine setting. While that setting is unset,
only the start's check and the owner's "Search for updates" run (D-01M63CD5PR0D5Q5BJS9KTZHVY9). A check only looks:
it never installs, and runs whether updating by itself is on and whether the machine is busy.

``update-checks.json`` keeps, per update, its last success, last attempt, failures in a row and the last reason. A
failure shows only once two come in a row; until then the last success stands, except that offline is unknown, never
current. What is shown is read against the version installed now, so an update applied since is no longer offered;
a newer version stays available through failed checks until a check finds it withdrawn.
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError

from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import impeccable, versions
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.state_store import machine_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.machine import Machine

STATE = "update-checks.json"  # in ~/.owlbear: each update's last success, attempt and failures; no history
TITLES = {"owlbear": "OwlBear", "pds": "Porsche Design System", "impeccable": "Impeccable"}
ACTIONABLE = {"owlbear": True, "pds": False, "impeccable": True}  # PDS counts once its update action exists
SHOWN = 2  # failures in a row before a failure shows
RETRY = timedelta(hours=1)  # after a failure, the next timed check comes this soon, unless the interval is shorter
TICK = 60.0  # seconds between the loop's looks whether a check is due
DRAIN = 5.0  # seconds the host's stop waits for the checks still running
PDS = "https://registry.npmjs.org/@porsche-design-system/components-js/latest"  # npm's latest release
SECONDS = 10.0  # the PDS request's limit
VERSION = re.compile(r"\d+\.\d+\.\d+")


class Failed(Exception):  # noqa: N818 - it names the outcome
    """A check that found nothing; ``offline`` when the source was not reached at all."""

    def __init__(self, detail: str, *, offline: bool = False) -> None:
        """Why, and whether the source was reached."""
        super().__init__(detail)
        self.offline = offline


def _iso(at: datetime) -> str:
    return at.isoformat(timespec="seconds")


def _time(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def owlbear() -> dict[str, Any]:
    """The version this machine would take, newer whether or not it pins another Impeccable; never installs.

    It also keeps that version's pack for the pages' Impeccable banner (``impeccable.release``).

    Raises:
        Failed: The versions could not be read, or their channel is unset.
    """
    found, running = impeccable.checked(), versions.running()
    tag = str(found.get("version", ""))
    if found.get("state") == "unknown" and not tag:
        raise Failed(str(found.get("detail", "")))
    newer = bool(tag) and (versions.number(tag) or (0, 0)) > (versions.number(running) or (-1, -1))
    latest, channel = tag if newer else running, found.get("channel")
    return {"newer": newer, "current": running, "latest": latest, "detail": found.get("detail", ""), "channel": channel}


def pds(fetch: Callable[[str, float], bytes] | None = None) -> dict[str, Any]:
    """The latest ``@porsche-design-system/components-js`` on npm against the release ``web/pds/load.mjs`` vendors.

    Raises:
        Failed: npm was not reached, refused, or named no version.
    """
    current = pages.pds_version()
    try:
        latest = json.loads((fetch or pack_files.fetch)(PDS, SECONDS))["version"]
    except HTTPError as exc:
        msg = f"npm answered {exc.code} {exc.reason}"
        raise Failed(msg) from exc
    except (OSError, HTTPException) as exc:
        msg = f"npm was not reached: {exc}"
        raise Failed(msg, offline=True) from exc
    except (ValueError, KeyError, TypeError) as exc:
        msg = "npm's answer names no version"
        raise Failed(msg) from exc
    if not isinstance(latest, str) or not VERSION.fullmatch(latest):
        msg = f"npm's answer names no version: {str(latest)[:60]}"
        raise Failed(msg)
    newer = _number(latest) > _number(current)
    return {"newer": newer, "current": current, "latest": latest, "detail": ""}


def _number(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version))


def impeccable_skill() -> dict[str, Any]:
    """Upstream's skill releases against the pinned tag, kept in ``notice.json`` for the other pages too.

    Raises:
        Failed: GitHub was not reached, refused, or answered with no list of releases.
    """
    said, pinned = pack_update.notice(refresh=False, force=True), pack_files.manifest()["upstream"]["tag"]
    if said["state"] != "known":
        raise Failed(said["detail"] or "the releases could not be read", offline=said["state"] == "unknown")
    behind = said["behind"]
    detail = f"{behind} newer release{'s' if behind != 1 else ''}" if behind else ""
    return {"newer": behind > 0, "current": pinned, "latest": said["latest"] or pinned, "detail": detail}


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {"owlbear": owlbear, "pds": pds, "impeccable": impeccable_skill}
INSTALLED: dict[str, Callable[[], str]] = {
    "owlbear": versions.running, "pds": pages.pds_version,
    "impeccable": lambda: pack_files.manifest()["upstream"]["tag"],
}  # fmt: skip
ORDER: dict[str, Callable[[str], tuple[int, ...] | None]] = {
    "owlbear": versions.number, "pds": lambda v: _number(v) or None, "impeccable": lambda v: _number(v) or None,
}  # fmt: skip


def _installed(name: str) -> str:
    """The version of *name* installed now; empty when it cannot be read, so the last check's word stands."""
    try:
        return INSTALLED[name]()
    except Exception:  # noqa: BLE001 - a hint for the shown state; the check itself reads it again
        return ""


def _ahead(name: str, latest: str, current: str) -> bool:
    """Whether *latest* is still ahead of *current*; True when either cannot be ordered, as the check found."""
    a, b = ORDER[name](latest), ORDER[name](current)
    return a is None or b is None or a > b


class Checks:
    """The machine's update checks: at the start, at each interval, and by hand; what each found."""

    def __init__(
        self,
        machine: Machine,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        spawn: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        """What the last checks kept; nothing runs until ``loop`` or ``start``; without *spawn*, each has a thread."""
        self.machine, self.now, self.spawn, self.lock = machine, now, spawn, threading.Lock()
        self.checking: set[str] = set()
        self.workers: list[threading.Thread] = []  # the threads ``drain`` waits for
        self.path = local_home.root() / STATE  # a check ending after the home moved (a test's teardown) keeps it here
        self.kept: dict[str, dict[str, Any]] = self._restored()

    def _restored(self) -> dict[str, dict[str, Any]]:
        path = self.path
        try:
            kept = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            self.machine.say(f"update checks: {path} is unreadable, so they start afresh: {exc}")
            return {}
        return {n: kept[n] for n in CHECKS if isinstance(kept, dict) and isinstance(kept.get(n), dict)}

    def _keep(self) -> None:
        path = self.path
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            atomic_write(path, json.dumps(self.kept, indent=2) + "\n")
        except OSError as exc:  # held until the host ends; the next check writes it again
            self.machine.say(f"update checks: {path} could not be written: {exc}")

    def start(self, name: str) -> bool:
        """Check *name* now, unless it is being checked or the machine is stopping; whether a check started."""
        with self.lock:  # its thread starts under the lock, so a drain from now on waits for it
            if name in self.checking or self.machine.stopping.is_set():
                return False
            self.checking.add(name)
            if self.spawn is None:
                worker = threading.Thread(target=self._run, args=(name,), daemon=True, name="update-check")
                self.workers = [t for t in self.workers if t.is_alive()] + [worker]
                worker.start()
                return True
        self.spawn(lambda: self._run(name))
        return True

    def drain(self, timeout: float | None = None) -> bool:
        """Wait up to *timeout* (``DRAIN``) seconds for the checks running; whether all ended, said when not."""
        timeout = DRAIN if timeout is None else timeout
        with self.lock:
            running = list(self.workers)
        deadline = time.monotonic() + timeout
        for worker in running:
            worker.join(max(0.0, deadline - time.monotonic()))
        if any(worker.is_alive() for worker in running):
            self.machine.say(f"the update checks did not end within {timeout:.0f} s")
            return False
        return True

    def _run(self, name: str) -> None:
        at, found, failure = self.now(), None, None
        try:
            found = CHECKS[name]()
        except Failed as exc:
            failure = exc
        except Exception as exc:  # noqa: BLE001 - a check that broke is one more failure, never the loop's end
            failure = Failed(f"{type(exc).__name__}: {exc}")
        with self.lock:
            kept = dict(self.kept.get(name, {}))
            kept["attempt_at"] = _iso(at)
            if failure is None:
                kept |= {"success": {"at": _iso(at), **found}, "failures": 0, "reason": "", "offline": False}
            else:
                kept |= {"failures": int(kept.get("failures", 0)) + 1, "reason": str(failure)[:400],
                         "offline": failure.offline}  # fmt: skip
            self.kept[name] = kept
            self.checking.discard(name)
            self._keep()
        if failure is not None:
            self.machine.say(f"update check of {TITLES[name]} failed: {failure}")

    def _settings(self) -> tuple[dict[str, int | None], str | None]:
        """Each check's interval and the machine's update channel, as resolved now."""
        try:
            resolved = machine_settings.current()
        except Exception as exc:  # noqa: BLE001 - unreadable settings: no timed check; the start's and by hand run
            self.machine.say(f"update checks: the machine settings could not be read: {exc}")
            return dict.fromkeys(CHECKS), None
        return {n: getattr(resolved, f"update_check_hours_{n}") for n in CHECKS}, resolved.channel

    def _next(self, name: str, hours: int | None) -> datetime | None:
        """When the timed check of *name* is due; None while its interval is unset."""
        if hours is None:
            return None
        kept = self.kept.get(name, {})
        last = _time(kept.get("attempt_at"))
        if last is None:
            return self.now()
        wait = timedelta(hours=hours)
        return last + (min(wait, RETRY) if kept.get("failures") else wait)

    def tick(self) -> None:
        """Start each check whose interval has passed; one whose interval is unset waits."""
        hours, now = self._settings()[0], self.now()
        for name in CHECKS:
            due = self._next(name, hours[name])
            if due is not None and due <= now:
                self.start(name)

    def loop(self) -> None:
        """Thread: every check at the start, then each at its interval, until the machine stops."""
        for name in CHECKS:
            self.start(name)
        while not self.machine.stopping.wait(TICK):
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed look
                self.machine.say(f"update checks failed: {type(exc).__name__}: {exc}")

    def read(self) -> dict[str, Any]:
        """Each update's state and when it is next checked; ``available`` counts each runnable newer one once."""
        (hours, channel), installed = self._settings(), {n: _installed(n) for n in CHECKS}
        with self.lock:
            shown = [self._shown(n, hours[n], installed[n], channel) for n in CHECKS]
        available = sum(1 for u in shown if u["available"])
        return {"updates": shown, "available": available}

    def _shown(self, name: str, hours: int | None, installed: str, channel: str | None) -> dict[str, Any]:
        kept = self.kept.get(name, {})
        success, failures = kept.get("success"), int(kept.get("failures", 0))
        found = success if isinstance(success, dict) else {}
        # OwlBear's version to take depends on the channel: one found on another channel is unknown until checked again
        moved = name == "owlbear" and bool(found) and found.get("channel") != channel
        current, latest = installed or found.get("current", ""), found.get("latest", "")
        offered = not moved and bool(found.get("newer")) and _ahead(name, latest, current)  # applied: not offered
        if failures >= SHOWN:
            state = "unknown" if kept.get("offline") else "failed"
        elif offered:
            state = "newer"
        elif found and not moved and not (failures and kept.get("offline")):
            state = "current"
        else:
            state = "unknown"  # never checked, or not reached since: offline is never current
        due = self._next(name, hours)
        return {
            "name": name, "title": TITLES[name], "actionable": ACTIONABLE[name], "state": state,
            "available": offered and ACTIONABLE[name],  # until applied or found withdrawn, whatever a failure says
            "current": current, "latest": latest if offered else current,
            "detail": impeccable.MOVED if moved else found.get("detail", ""),
            "checked_at": found.get("at"), "attempted_at": kept.get("attempt_at"), "failures": failures,
            "reason": kept.get("reason", "") if failures >= SHOWN else "", "checking": name in self.checking,
            "hours": hours, "next_at": _iso(due) if due else None,
        }  # fmt: skip
