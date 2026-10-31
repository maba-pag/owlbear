"""One read of everything Settings shows from outside (#810): at host start, every hour and on Settings' Read again.

A read pulls the shared settings, reads every settings layer, the offered models, Impeccable's releases and this
machine's settings, each source on its own: one that fails is named with where and why while the others still
update. What it found goes to the read state (`settings_seen`), which the Settings and Changes pages show.
"""

from __future__ import annotations

import contextlib
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable import pack_update
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.runtimes.settings_seen import NAME, Failure, Ledger, Seen, flatten
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer
from owlbear_delivery_next.state_store import machine_settings, registry, settings_carry
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, StoreError, read_layer_bytes

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

EVERY = 3600.0  # seconds between the host's reads
DRAIN = 120.0  # seconds a stopping host waits for a running read
SHARED, MODELS, IMPECCABLE, MACHINE = "shared settings", "models", "Impeccable releases", "this machine's settings"
SOURCES = (SHARED, MODELS, IMPECCABLE, MACHINE)

type Missed = list[tuple[str, str]]  # each failure's place (a file, a folder, a service; may be empty) and detail


class Reader:
    """Reads outside data one pass at a time; *stores* are this machine's projects."""

    def __init__(self, say: Callable[[str], None], stores: Callable[[], list[Store]]) -> None:
        self.say, self.stores = say, stores
        self.ledger = Ledger(local_home.root() / NAME, say)
        self.offered = model_choices.Offered()
        self.stopping: threading.Event | None = None  # the loop's; a pass it cuts short records nothing
        self._run = threading.Lock()

    def read(self) -> Seen:
        """Read every source now, after any read already running; record what was found and what failed."""
        with self._run:
            self.ledger.begin()
            failures: list[Failure] = []
            glob, unshared = None, False
            for source in SOURCES:
                if self.stopping is not None and self.stopping.is_set():
                    return self.ledger.load()
                try:
                    if source == SHARED:
                        missed, glob, unshared = self._shared()
                    else:
                        missed = {MODELS: self._models, IMPECCABLE: self._impeccable, MACHINE: self._machine}[source]()
                except Exception as exc:  # noqa: BLE001 - one source's surprise is that source's failure
                    missed = [("", f"{type(exc).__name__}: {exc}")]
                for place, detail in missed:
                    self.say(f"settings read: {source} failed{f' at {place}' if place else ''}: {detail}")
                    error = f"{place}: {detail}" if place else detail
                    failures.append(Failure(source=source, at=datetime.now().astimezone(), error=error[:500]))
            return self.ledger.finish(glob, failures, unshared=unshared, at=datetime.now().astimezone())

    def loop(self, stopping: threading.Event) -> None:
        """The host's reads: one at once, then one every hour until *stopping* is set."""
        self.stopping = stopping
        while not stopping.is_set():
            try:
                self.read()
            except Exception as exc:  # noqa: BLE001 - a failed pass is said; the next hour reads again
                self.say(f"settings read: the read failed: {type(exc).__name__}: {exc}")
            if self.pause(stopping, EVERY):
                return

    def pause(self, stopping: threading.Event, seconds: float) -> bool:
        """Wait for the next read; whether the host is stopping."""
        return stopping.wait(seconds)

    def drain(self) -> None:
        """Wait, bounded, for a running read to end, once the host's stop is set."""
        if self._run.acquire(timeout=DRAIN):
            self._run.release()

    def shown(self) -> dict[str, Any]:
        """The read state for Settings: each notice with where this machine overrides its key."""
        seen = self.ledger.load()
        out = seen.model_dump(mode="json", exclude={"seen"})
        if seen.notices:
            over = self._overrides()
            for n in out["notices"]:
                n["overridden"] = [where for where, keys in over if n["key"] in keys]
        return out

    def polled(self) -> dict[str, Any]:
        """The read state in brief, for every page's poll."""
        seen = self.ledger.load()
        return seen.model_dump(mode="json", include={"read_at", "succeeded_at"}) | {  # as shown() writes them
            "failed": sorted({f.source for f in seen.failures}),
            "notices": [n.id for n in seen.notices],
        }

    def dismiss(self, ids: Collection[str]) -> dict[str, Any]:
        """Remove these notices on every page; the brief state after."""
        self.ledger.dismiss(ids)
        return self.polled()

    def _overrides(self) -> list[tuple[str, set[str]]]:
        """Who on this machine sets which keys above Global; a layer that does not read is skipped here."""
        over: list[tuple[str, set[str]]] = []
        mine: set[str] = set()
        with contextlib.suppress(StoreError):
            mine = set(flatten(read_layer_bytes(local_home.root() / MACHINE_SETTINGS, MachineLayer)[0]))
        try:
            own = registry.load().settings
            mine |= {f"machine.{k}" for k in machine_settings.FIELDS if getattr(own, k) is not None}
        except registry.RegistryError:
            pass
        over.append(("this machine", mine))
        names: set[str] = set()
        for store in self.stores():
            name = store.name or store.root.name
            if name in names:
                continue
            try:
                over.append((name, set(flatten(store.read_config()))))
                names.add(name)
            except StoreError:
                continue
        return over

    def _shared(self) -> tuple[Missed, dict[str, str] | None, bool]:
        """Pull the shared repository and read every layer in it, then the unshared projects' own layers."""
        try:
            shared = data_repo.locate()
        except data_repo.DataRepoError as exc:
            return [("the shared settings location", str(exc))], None, False
        missed: Missed = []
        glob = None
        if shared is not None:
            missed += _sync(shared)
            try:
                glob = flatten(read_layer_bytes(shared.global_path, GlobalLayer)[0])
            except StoreError as exc:
                missed.append((str(shared.global_path), str(exc)))
            missed += _unreadable(sorted(shared.root.glob(f"*/{data_repo.CONFIG}")))
        missed += _unreadable([s.config_path for s in self.stores() if s.shared is None])
        return missed, glob, shared is None

    def _models(self) -> Missed:
        error = self.offered.refresh()["error"]
        return [("the Copilot CLI's model list", error)] if error else []

    def _impeccable(self) -> Missed:
        n = pack_update.notice(refresh=True, force=True)
        if n["state"] in ("unknown", "error"):
            return [(f"GitHub's releases of {n['pack']}", n.get("detail") or "upstream was not reached")]
        return []

    def _machine(self) -> Missed:
        path = local_home.root() / MACHINE_SETTINGS
        missed: Missed = []
        try:
            read_layer_bytes(path, MachineLayer)
        except StoreError as exc:
            missed.append((str(path), str(exc)))
        try:
            machine_settings.current()
        except registry.RegistryError as exc:
            missed.append(("", str(exc)))
        return missed


def _sync(shared: DataRepo) -> Missed:
    """Bring the checkout current; why it is not."""
    try:
        refused = settings_carry.sync(shared, registry.load().global_written)
    except (data_repo.DataRepoError, registry.RegistryError) as exc:
        refused = str(exc)
    return [(str(shared.root), refused)] if refused else []


def _unreadable(paths: list[Path]) -> Missed:
    """The project layers among *paths* that do not read."""
    missed: Missed = []
    for path in paths:
        try:
            read_layer_bytes(path, Layer)
        except StoreError as exc:
            missed.append((str(path), str(exc)))
    return missed
