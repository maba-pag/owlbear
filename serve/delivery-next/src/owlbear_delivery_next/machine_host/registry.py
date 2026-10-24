"""The machine's registered projects (TD-242): ``~/.owlbear/machine.json``, written under ``machine.lock``.

A project is a clone. Registering one writes only its Delivery folder into it, holding ``clone-id``, the project's id;
the store itself lives in ``~/.owlbear/projects/<id>`` (TD-334). Loading checks the id again, so a re-clone at the
same path shows as replaced (Remove or Adopt) and never inherits the old registration.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings.config import MachineValues
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.database import STORE_FORMAT, StoreError

if TYPE_CHECKING:
    from collections.abc import Iterator

MACHINE, LOCK = project_home.MACHINE, "machine.lock"
MACHINE_FORMAT = 6  # 2: the machine's own settings (TD-243, TD-288, TD-300); 3: its sessions (TD-336); 4: `active`;
# 5: one curation setting per trigger; 6: settings inherit Global's and were moved there once (the owner, 2026-10-23)
STALE = "the machine settings changed since this page loaded them"


class RegistryError(Exception):
    """A project that cannot be registered or loaded, or a registry this code cannot read; the text says why."""


class Project(Record):
    """One registered clone: its id (the store's ``clone-id``), canonical work tree and when it was added."""

    id: str
    path: str
    added_at: datetime


class Settings(MachineValues):
    """This machine's own settings, each overriding Global's; changed only in Settings → This machine."""

    model_config = ConfigDict(extra="forbid", strict=False)  # machine.json as earlier formats wrote it

    @model_validator(mode="before")
    @classmethod
    def _one_switch(cls, data: Any) -> Any:  # noqa: ANN401 - the raw settings
        """Format 4's one switch for both triggers becomes their two settings: on, or on even while paused."""
        if isinstance(data, dict) and "curate_while_paused" in data:
            data = dict(data)
            both = "paused" if TypeAdapter(bool).validate_python(data.pop("curate_while_paused")) else "on"
            data.setdefault("curate_after_merge", both)
            data.setdefault("curate_when_idle", both)
        return data


class Machine(Record):
    """``machine.json``: the registered projects, the last Resume and the machine's settings."""

    format: int = MACHINE_FORMAT
    projects: list[Project] = Field(default_factory=list)
    resumed_at: datetime | None = None
    settings: Settings = Field(default_factory=Settings)  # each unset inherits Global's
    active: str = ""  # the highest version ever active here: never backwards (self-update build §4)
    settings_moved: bool = False  # its settings were moved into Global once, so it follows Global (2026-10-23)
    settings_moving: Settings | None = None  # the values a move took, kept across its retries until it is done


def _home() -> Path:
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    return home


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """Hold ``machine.lock``: every registry change and every ``clone-id`` creation happens under it."""
    fd = os.open(_home(), os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock = open_lock(fd, blocking=True, name=LOCK)
    finally:
        os.close(fd)
    try:
        yield
    finally:
        os.close(lock)


def load() -> Machine:
    """The registry; empty before the first project, refused when another release wrote a newer one."""
    path = _home() / MACHINE
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return Machine()
    except (OSError, ValueError) as exc:
        msg = f"{path} is unreadable: {exc}"
        raise RegistryError(msg) from exc
    try:
        machine = Machine.model_validate_json(raw)
    except ValidationError as exc:
        msg = f"{path} is unreadable: {exc.errors()[0]['msg']}"
        raise RegistryError(msg) from exc
    if machine.format > MACHINE_FORMAT:
        msg = f"{path} has format {machine.format}, newer than {MACHINE_FORMAT}: this OwlBear is older"
        raise RegistryError(msg)
    return machine


def save(machine: Machine) -> None:
    """Write the registry atomically in this format, readable only by the owner; call it under ``locked()``."""
    path = _home() / MACHINE
    machine.format = MACHINE_FORMAT
    atomic_write(path, machine.model_dump_json(indent=2) + "\n")
    path.chmod(0o600)


def revision(settings: Settings) -> str:
    """What the page names when it saves: any other save since then refuses the page's."""
    return hashlib.sha256(settings.model_dump_json().encode()).hexdigest()


def configure(settings: Settings, rev: str) -> Settings:
    """Replace the machine's settings, refused when they changed since *rev* was read."""
    with locked():
        machine = load()
        if revision(machine.settings) != rev:
            raise RegistryError(STALE)
        machine.settings = settings
        save(machine)
    return settings


def _git(cwd: Path, *args: str) -> Path:
    git = shutil.which("git") or "git"
    try:
        out = subprocess.run(  # noqa: S603 - fixed git argument vector
            [git, *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=30
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"{cwd} is not a git work tree"
        raise RegistryError(msg) from exc
    return (cwd / out).resolve()


def _owned(path: Path) -> None:
    if path.stat().st_uid != os.getuid():
        msg = f"{path} belongs to another user; OwlBear serves only your own clones"
        raise RegistryError(msg)


def store_of(work: Path) -> Path:
    """The clone's own Delivery folder at *work*: ``<git common dir>/owlbear-delivery``, its id and format marker."""
    return _git(work, "rev-parse", "--git-common-dir") / project_home.STORE_DIR


def canonical(path: Path) -> tuple[Path, Path]:
    """The clone's work tree and store, as real paths; refused unless it is the owner's git work tree."""
    try:
        work = _git(path.resolve(strict=True), "rev-parse", "--show-toplevel")
    except OSError as exc:
        msg = f"{path} does not exist"
        raise RegistryError(msg) from exc
    store = store_of(work)
    for owned in (work, store.parent):
        _owned(owned)
    marker = store / "format"
    try:
        found = int(marker.read_text()) if marker.exists() else 0
    except (OSError, ValueError) as exc:
        msg = f"{marker} is unreadable"
        raise RegistryError(msg) from exc
    if found > STORE_FORMAT:
        msg = f"{work}'s Delivery state has format {found}, newer than {STORE_FORMAT}: this OwlBear is older"
        raise RegistryError(msg)
    return work, store


def clone_id(store: Path) -> str | None:
    """The id written into the clone's folder, or None when there is none."""
    try:
        return project_home.clone_id(store)
    except StoreError as exc:
        raise RegistryError(str(exc)) from exc


def _ensure_id(store: Path) -> str:
    """The clone's id: reused when present, else created once; never rewritten."""
    try:
        return project_home.ensure_id(store)
    except StoreError as exc:
        raise RegistryError(str(exc)) from exc


def register(path: Path) -> Project:
    """Add the clone at *path*; refused when it is registered already, under its id or its path."""
    work, store = canonical(path)
    with locked():
        machine = load()
        if found := next((p for p in machine.projects if p.path == str(work)), None):
            msg = f"{work} is registered already (project {found.id})"
            raise RegistryError(msg)
        pid = _ensure_id(store)
        if found := next((p for p in machine.projects if p.id == pid), None):
            msg = f"this clone is registered already at {found.path}; remove that project first"
            raise RegistryError(msg)
        project = Project(id=pid, path=str(work), added_at=datetime.now(UTC))
        machine.projects.append(project)
        save(machine)
    return project


def replaced(project: Project) -> str | None:
    """Why the registered clone is not the one at its path now; None when it is."""
    work = Path(project.path)
    if not work.is_dir():
        return f"{work} is gone; Remove the project"
    try:
        found = clone_id(store_of(work))
    except RegistryError as exc:
        return str(exc)
    if found != project.id:
        return f"the clone at {work} is not the one registered; Remove or Adopt it"
    return None


def adopt(pid: str) -> Project:
    """Let the clone now at a replaced project's path take its place, under that clone's own id."""
    with locked():
        machine = load()
        old = next((p for p in machine.projects if p.id == pid), None)
        if old is None:
            msg = f"no project {pid} is registered"
            raise RegistryError(msg)
        work, store = canonical(Path(old.path))
        new = Project(id=_ensure_id(store), path=str(work), added_at=datetime.now(UTC))
        if any(p.id == new.id and p.id != pid for p in machine.projects):
            msg = f"this clone is registered already as project {new.id}"
            raise RegistryError(msg)
        machine.projects = [new if p.id == pid else p for p in machine.projects]
        save(machine)
    return new


def remove(pid: str) -> None:
    """Forget a project; its clone keeps its store and ``clone-id``. The caller stops it first."""
    with locked():
        machine = load()
        machine.projects = [p for p in machine.projects if p.id != pid]
        save(machine)


def resumed(at: datetime) -> None:
    """Record the owner's Resume."""
    with locked():
        machine = load()
        machine.resumed_at = at
        save(machine)
