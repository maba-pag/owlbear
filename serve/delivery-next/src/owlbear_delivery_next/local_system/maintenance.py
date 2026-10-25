"""Maintenance SDK leases: durable reservations and workspaces outlive an unknown session termination."""

from __future__ import annotations

import contextlib
import math
import os
import shutil
import tempfile
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import psutil
from pydantic import Field, field_validator

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system import local_home, processes
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run

FILE = "maintenance-sessions.json"
HELD = frozenset({"running", "held"})
type Kind = Literal["pack", "curation", "replay"]


class MaintenanceError(RuntimeError):
    """Unreadable ownership is a blocking fault, never an empty ledger."""


class Lease(Record):
    """One immutable admission generation and its recorded identities, recovery and retained workspace."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    project: str
    slot: str
    kind: Kind
    workspace: str
    started_at: datetime
    boot: float = Field(gt=0, allow_inf_nan=False)
    owner_pid: int = Field(gt=0)
    owner_created: float | None = Field(gt=0, allow_inf_nan=False)
    state: Literal["running", "held", "released", "recovered"] = "running"
    pids: dict[int, float | None] = Field(default_factory=dict)
    complete: bool = False
    reason: str = ""
    ended_at: datetime | None = None

    @field_validator("pids", mode="before")
    @classmethod
    def identities(cls, value: object) -> object:
        """A damaged or fabricated PID never becomes evidence that a session is gone."""
        if not isinstance(value, dict):
            raise ValueError("maintenance process identities must be a mapping")  # noqa: TRY003, TRY004, EM101 - pydantic validation
        for pid, born in value.items():
            if isinstance(pid, bool) or not str(pid).isdigit() or int(str(pid)) <= 0:
                raise ValueError("maintenance PIDs must be positive integers")  # noqa: TRY003, EM101
            if born is not None and (
                isinstance(born, bool) or not isinstance(born, (float, int)) or not math.isfinite(born) or born <= 0
            ):
                raise ValueError("maintenance process birth times must be positive finite numbers")  # noqa: TRY003, EM101
        return value


class Ledger(Record):
    """Both active ownership and completed recovery history remain on disk."""

    format: Literal[1] = 1
    sessions: list[Lease] = Field(default_factory=list)
    imported: list[str] = Field(default_factory=list)


class Maintenance:
    """One machine's ledger; every reader and writer uses the same no-follow filesystem lock."""

    def __init__(
        self,
        slots: Slots,
        *,
        boot: Callable[[], float] | None = None,
        observe: processes.Observe | None = None,
    ) -> None:
        self.slots, self.boot, self.observe = slots, boot or psutil.boot_time, observe or processes.alive
        with self._locked() as ledger:
            changed = False
            for lease in ledger.sessions:
                if lease.state == "running" and self.observe(lease.owner_pid, lease.owner_created) is False:
                    lease.state, lease.reason = "held", "the maintenance caller ended without a termination result"
                    changed = True
                if lease.state in HELD:
                    self.slots.restore_one(lease.project, lease.slot, 1)
            if changed:
                self._save(ledger)

    @property
    def path(self) -> Path:
        """This machine's ledger file."""
        return local_home.root() / FILE

    @contextlib.contextmanager
    def _locked(self) -> Iterator[Ledger]:
        root = local_home.root()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            lock = open_lock(directory, blocking=True, name=".maintenance.lock")
        finally:
            os.close(directory)
        try:
            try:
                try:
                    fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
                except FileNotFoundError:
                    ledger = Ledger()
                else:
                    with os.fdopen(fd, encoding="utf-8") as source:
                        ledger = Ledger.model_validate_json(source.read())
            except (OSError, ValueError) as exc:
                msg = f"maintenance ownership could not be read: {exc}"
                raise MaintenanceError(msg) from exc
            yield ledger
        finally:
            os.close(lock)

    def _save(self, ledger: Ledger) -> None:
        try:
            atomic_write(self.path, ledger.model_dump_json(indent=2) + "\n")
        except OSError as exc:
            msg = f"maintenance ownership could not be saved: {exc}"
            raise MaintenanceError(msg) from exc

    @staticmethod
    def _lease(ledger: Ledger, ident: str) -> Lease:
        lease = next((lease for lease in ledger.sessions if lease.id == ident), None)
        if lease is None or lease.state not in HELD:
            msg = "this maintenance session is no longer held; reload its state"
            raise LookupError(msg)
        return lease

    def begin(self, project: str, slot: str, kind: Kind, workspace: str, *, now: datetime | None = None) -> str:
        """Persist ownership after slot grant and before calling any SDK entry point."""
        lease = Lease(
            id=uuid.uuid4().hex,
            project=project,
            slot=slot,
            kind=kind,
            workspace=workspace,
            started_at=now or datetime.now(UTC),
            boot=self.boot(),
            owner_pid=os.getpid(),
            owner_created=processes.started(os.getpid()),
        )
        with self._locked() as ledger:
            if any(s.project == project and s.slot == slot and s.state in HELD for s in ledger.sessions):
                raise MaintenanceError("this maintenance reservation is already owned")  # noqa: TRY003, EM101
            ledger.sessions.append(lease)
            self._save(ledger)
        return lease.id

    def adopt(  # noqa: PLR0913 - one import record's fields, all needed to write its lease
        self, source: str, project: str, kind: Kind, pids: processes.Pids, *, interrupted: bool, workspace: str = ""
    ) -> None:
        """Import pre-ledger ownership once; no legacy record can prove complete process coverage."""
        with self._locked() as ledger:
            if source in ledger.imported:
                return
            if pids or interrupted:
                ident = uuid.uuid4().hex
                lease = Lease(
                    id=ident,
                    project=project,
                    slot=f"pack:legacy-{ident}",
                    kind=kind,
                    workspace=workspace,
                    started_at=datetime.now(UTC),
                    boot=self.boot(),
                    owner_pid=os.getpid(),
                    owner_created=processes.started(os.getpid()),
                    pids=dict(pids),
                    state="held",
                    reason="legacy maintenance stopped without complete termination proof",
                )
                ledger.sessions.append(lease)
                self.slots.restore_one(lease.project, lease.slot, 1)
            ledger.imported.append(source)
            self._save(ledger)

    def adopt_uncertain(
        self,
        source: str,
        project: str,
        kind: Kind,
        *,
        workspace: str,
        covers: Callable[[Lease], bool] | None = None,
    ) -> Lease:
        """Import an older host's uncertain work, unless a lease already covers it in any state.

        An empty import receipt never suppresses this; only genuine ledger history does, so a recovered
        generation is not resurrected and a current lease is not duplicated.
        """
        same = covers or (lambda s: s.project == project and s.kind == kind and s.workspace == workspace)
        with self._locked() as ledger:
            known = [s for s in ledger.sessions if same(s)]
            if known:
                return max(known, key=lambda s: s.started_at)
            ident = uuid.uuid4().hex
            lease = Lease(
                id=ident,
                project=project,
                slot=f"pack:legacy-{ident}",
                kind=kind,
                workspace=workspace,
                started_at=datetime.now(UTC),
                boot=self.boot(),
                owner_pid=os.getpid(),
                owner_created=processes.started(os.getpid()),
                state="held",
                reason="legacy maintenance stopped without complete termination proof",
            )
            ledger.sessions.append(lease)
            if source not in ledger.imported:
                ledger.imported.append(source)
            self._save(ledger)
        self.slots.restore_one(lease.project, lease.slot, 1)
        return lease

    def held(self, project: str, slot: str) -> bool:
        """Whether a particular admitted reservation still belongs to uncertain work."""
        with self._locked() as ledger:
            return any(s.project == project and s.slot == slot and s.state in HELD for s in ledger.sessions)

    def pending(self, kind: Kind | None = None) -> bool:
        """Any uncertain or active session in the requested maintenance lane, also after a host restart."""
        self.sweep()
        with self._locked() as ledger:
            return any(s.state in HELD and (kind is None or s.kind == kind) for s in ledger.sessions)

    @staticmethod
    def _record(lease: Lease, found: processes.Pids) -> None:
        Lease.identities(dict(found))
        for pid, born in found.items():
            previous = lease.pids.get(pid)
            if previous is not None and born is not None and previous != born:
                lease.reason = "a recorded PID has conflicting process identities"
                lease.complete = False
            lease.pids[pid] = previous if previous is not None else born

    def record(self, ident: str, pids: processes.Pids) -> None:
        """Keep every observed identity; a later unknown start never erases a known birth time."""
        with self._locked() as ledger:
            lease = self._lease(ledger, ident)
            self._record(lease, pids)
            self._save(ledger)

    def run(
        self,
        cfg: Session,
        execute: Callable[[Session], Run],
        *,
        project: str,
        slot: str,
        kind: Kind,
    ) -> Run:
        """Enter SDK only after admission is durable; keep its lease after every exception or uncertain result."""
        try:
            ident = self.begin(project, slot, kind, str(cfg.worktree))
        except BaseException:
            self.slots.give(project, slot)  # SDK entry has not happened
            raise

        def event(found: dict[str, object]) -> None:
            if found.get("event") == "pids":
                raw = found.get("pids")
                Lease.identities(raw)
                if not isinstance(raw, dict):
                    raise MaintenanceError("the SDK returned invalid process identities")  # noqa: TRY003, EM101
                self.record(ident, {int(pid): born for pid, born in raw.items()})
            cfg.journal.event(found)

        try:
            done = execute(replace(cfg, journal=replace(cfg.journal, event=event)))
        except BaseException as primary:
            try:
                self.failed(ident, primary)
            except BaseException as cleanup:  # noqa: BLE001 - recorded for any exit, then re-raised
                primary.add_note(f"maintenance ownership also failed to persist ({type(cleanup).__name__})")
            raise
        self.finished(ident, done)
        return done

    @contextlib.contextmanager
    def workspace(self, prefix: str) -> Iterator[Path]:
        """Remove a newly created workspace only if no held or recovered lease retains it."""
        from pathlib import Path  # noqa: PLC0415 - paths are otherwise needed only for typing

        root = Path(tempfile.mkdtemp(prefix=prefix))
        try:
            yield root
        finally:
            if not self.retained(str(root)):
                shutil.rmtree(root)

    def failed(self, ident: str, error: BaseException) -> None:
        """An exception without a returned Run proves neither absence nor complete process coverage."""
        with self._locked() as ledger:
            lease = self._lease(ledger, ident)
            lease.state, lease.complete = "held", False
            lease.reason = f"session ended without termination proof ({type(error).__name__})"
            self._save(ledger)

    def finished(self, ident: str, run: Run) -> None:
        """Persist complete termination evidence before releasing a reservation; unknown work remains held."""
        with self._locked() as ledger:
            lease = self._lease(ledger, ident)
            self._record(lease, run.pids)
            termination = run.termination
            if termination:
                self._record(lease, dict.fromkeys((*termination.survivors, *termination.unknown)))
            if termination and termination.confirmed and not lease.reason:
                lease.state, lease.ended_at = "released", datetime.now(UTC)
                lease.reason = "the SDK confirmed termination"
            else:
                lease.complete = bool(
                    termination
                    and not termination.problems
                    and run.runtime_pid in lease.pids
                    and lease.pids
                    and all(born is not None for born in lease.pids.values())
                    and not lease.reason
                )
                lease.state = "held"
                lease.reason = (
                    "; ".join(termination.problems)
                    if termination and termination.problems
                    else (
                        "recorded processes remain" if lease.complete else "process coverage or termination is unknown"
                    )
                )
            self._save(ledger)
            released = lease.state == "released"
        if released:
            self.slots.give(lease.project, lease.slot)

    def sweep(self) -> None:
        """Release complete identified sessions only on positive identity-aware absence, never empty evidence."""
        released = []
        with self._locked() as ledger:
            for lease in ledger.sessions:
                if lease.state != "held" or not lease.complete or not lease.pids:
                    continue
                if processes.verdict(lease.pids, self.observe).confirmed:
                    lease.state, lease.ended_at = "released", datetime.now(UTC)
                    lease.reason = "every recorded process identity was confirmed gone"
                    released.append((lease.project, lease.slot))
            if released:
                self._save(ledger)
        for project, slot in released:
            self.slots.give(project, slot)

    def retained(self, workspace: str) -> bool:
        """A recovered unknown workspace stays for inspection, even after its reservation is explicitly released."""
        with self._locked() as ledger:
            return any(s.workspace == workspace and s.state in {*HELD, "recovered"} for s in ledger.sessions)

    def read(self) -> dict[str, list[dict[str, object]]]:
        """Public state omits process details but retains completed history and captured immutable session IDs."""
        self.sweep()
        with self._locked() as ledger:
            return {
                "sessions": [
                    {
                        "id": s.id,
                        "project": s.project,
                        "kind": s.kind,
                        "started_at": s.started_at.isoformat(),
                        "workspace": s.workspace,
                        "reason": s.reason,
                        "state": s.state,
                        "recoverable": s.state == "held" and self.boot() > s.boot,
                    }
                    for s in ledger.sessions
                ]
            }

    def recover(self, ident: str, *, rebooted: bool) -> dict[str, list[dict[str, object]]]:
        """Explicit generation-bound reboot recovery releases a reservation, never a workspace or its history."""
        if rebooted is not True:
            raise ValueError("confirm the computer rebooted since this session")  # noqa: TRY003, EM101
        with self._locked() as ledger:
            lease = self._lease(ledger, ident)
            if lease.state != "held" or self.boot() <= lease.boot:
                raise ValueError("a reboot since the failed session is required")  # noqa: TRY003, EM101
            lease.state, lease.ended_at = "recovered", datetime.now(UTC)
            lease.reason = "the owner confirmed a reboot; workspace and history retained"
            self._save(ledger)
        self.slots.give(lease.project, lease.slot)
        return self.read()
