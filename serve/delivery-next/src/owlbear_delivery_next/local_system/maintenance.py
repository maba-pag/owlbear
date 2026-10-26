"""Maintenance SDK leases: durable reservations and workspaces outlive an unknown session termination."""

from __future__ import annotations

import contextlib
import math
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Protocol

import psutil
from pydantic import BaseModel, ConfigDict, Field, field_validator

from owlbear_delivery_next.local_system import local_home, processes
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.local_system.slots import Slots

FILE = "maintenance-sessions.json"
HELD = frozenset({"running", "held"})
type Kind = Literal["pack", "curation", "replay"]


class Record(BaseModel):
    """Strict base: unknown fields are a format error, not silently dropped."""

    model_config = ConfigDict(extra="forbid")


class Outcome(Protocol):
    """What a finished SDK run reports; a runtimes Run satisfies it without this layer importing it."""

    pids: processes.Pids
    termination: processes.Termination | None
    runtime_pid: int | None


class MaintenanceError(RuntimeError):
    """Unreadable ownership is a blocking fault, never an empty ledger."""


class Lease(Record):
    """One immutable admission generation and its recorded identities, recovery and retained workspace."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    project: str
    slot: str
    kind: Kind
    workspace: str
    generation: str = ""  # the imported run's proven identity; empty when none was proven
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
            raise ValueError(  # noqa: TRY003, TRY004
                "maintenance process identities must be a mapping"  # noqa: EM101
            )
        for pid, born in value.items():
            if isinstance(pid, bool) or not str(pid).isdigit() or int(str(pid)) <= 0:
                raise ValueError("maintenance PIDs must be positive integers")  # noqa: TRY003, EM101
            if born is not None and (
                isinstance(born, bool) or not isinstance(born, (float, int)) or not math.isfinite(born) or born <= 0
            ):
                raise ValueError(  # noqa: TRY003
                    "maintenance process birth times must be positive finite numbers"  # noqa: EM101
                )
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
    ) -> str:
        """Import pre-ledger ownership once; no legacy record can prove complete process coverage.

        Returns the slot of the lease it created, or empty when it created none.
        """
        with self._locked() as ledger:
            if source in ledger.imported:
                return ""
            slot = ""
            if pids or interrupted:
                ident = uuid.uuid4().hex
                slot = f"pack:legacy-{ident}"
                lease = Lease(
                    id=ident,
                    project=project,
                    slot=slot,
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
                ledger.imported.append(f"{source}:slot:{slot}")  # the lease and its slot are written together
                self.slots.restore_one(lease.project, lease.slot, 1)
            ledger.imported.append(source)
            self._save(ledger)
            return slot

    def receipted(self, key: str, digest: str) -> str:
        """The generation an older host gave the record version *digest*, when it rewrote that record; else empty."""
        prefix = f"{key}:receipt:{digest}:"
        with self._locked() as ledger:
            return next((s[len(prefix) :] for s in ledger.imported if s.startswith(prefix)), "")

    def receipt(self, key: str, digest: str, generation: str) -> None:
        """Record that record version *digest* is the rewrite of run *generation*, so a restart keeps it."""
        mark = f"{key}:receipt:{digest}:{generation}"
        with self._locked() as ledger:
            if mark not in ledger.imported:
                ledger.imported.append(mark)
                self._save(ledger)

    def imported_slot(self, source: str) -> str:
        """The slot of the lease that *source*'s import created, so a restart still finds it; empty when none."""
        prefix = f"{source}:slot:"
        with self._locked() as ledger:
            return next((s[len(prefix) :] for s in ledger.imported if s.startswith(prefix)), "")

    def recording(self, project: str, kind: Kind, pids: dict[int, float | None], hint: str) -> str:
        """The slot of the lease that records every one of *pids*: *hint* when it is one, else the newest.

        Empty when none does. A lease that records other processes never matches, so a stale hint or import mark
        cannot name it. A settled lease matches only as *hint*: a later process with the same PID and an unknown birth
        is not evidence that it is the settled run's process.
        """
        with self._locked() as ledger:
            found = [
                s
                for s in ledger.sessions
                if s.project == project
                and s.kind == kind
                and (s.state in HELD or s.slot == hint)
                and recorded(s, pids, self.boot())
            ]
        if not found:
            return ""
        return next((s.slot for s in found if s.slot == hint), max(found, key=lambda s: s.started_at).slot)

    def adopt_uncertain(  # noqa: PLR0913 - one import's identity, all needed to decide its generation
        self,
        source: str,
        project: str,
        kind: Kind,
        *,
        workspace: str,
        generation: str = "",
        started: datetime | None = None,
        covers: Callable[[Lease], bool] | None = None,
        pids: processes.Pids | None = None,
        keyed: bool = False,
    ) -> Lease:
        """Import an older host's uncertain work once per proven generation.

        A proven generation is covered by its lease in any state, so a recovered one is never resurrected. An unproven
        one (empty *generation*) is covered only by a held lease, so a later unknown run gets its own hold. *covers*
        replaces that rule for a caller that keys its own history. *pids* are the processes a new lease records.
        A *keyed* import also marks *source* with the lease it created, in the same save, so a retry finds that very
        lease again instead of matching by window.
        """

        def same(s: Lease) -> bool:
            if covers is not None:
                return covers(s)
            if s.project != project or s.kind != kind or s.workspace != workspace or s.generation != generation:
                return False
            return bool(generation) or s.state in HELD

        with self._locked() as ledger:
            if keyed:
                prefix = f"{source}:slot:"
                marked = next((s[len(prefix) :] for s in ledger.imported if s.startswith(prefix)), "")
                owned = next((s for s in ledger.sessions if marked and s.slot == marked), None)
                if owned is not None:
                    return owned
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
                generation=generation,
                started_at=started or datetime.now(UTC),
                boot=self.boot(),
                owner_pid=os.getpid(),
                owner_created=processes.started(os.getpid()),
                state="held",
                reason="legacy maintenance stopped without complete termination proof",
                pids=dict(pids or {}),
            )
            ledger.sessions.append(lease)
            if source not in ledger.imported:
                ledger.imported.append(source)
            if keyed:
                ledger.imported.append(f"{source}:slot:{lease.slot}")
            self._save(ledger)
        self.slots.restore_one(lease.project, lease.slot, 1)
        return lease

    def owns(self, workspace: str) -> bool:
        """Whether a lease in any state already accounts for *workspace*, so its record must not be imported again."""
        with self._locked() as ledger:
            return any(s.workspace == workspace for s in ledger.sessions)

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

    def finished(self, ident: str, run: Outcome) -> None:
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


def recorded(lease: Lease, pids: dict[int, float | None], boot: float) -> bool:
    """Whether a lease recorded every one of these PIDs.

    A birth unknown on either side matches, except that a settled lease covers an unknown birth only up to its end.
    A birth known after the current *boot* cannot be a process the lease started before an earlier boot.
    """
    settled = lease.state not in HELD
    ended = lease.ended_at.timestamp() if lease.ended_at else None
    return bool(pids) and all(
        pid in lease.pids
        and not (lease.boot < boot and born is not None and born >= boot)
        and _same_process(lease.pids[pid], born, settled=settled, ended=ended)
        for pid, born in pids.items()
    )


def _same_process(recorded: float | None, born: float | None, *, settled: bool, ended: float | None) -> bool:
    if recorded is None and born is not None and settled:
        return ended is not None and born <= ended
    return recorded is None or born is None or born == recorded
