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
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings.config import MachineValues
from owlbear_delivery_next.state_store import fd_tree, project_home, project_move, switched_authority
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError
from owlbear_delivery_next.state_store.git_images import GitImages
from owlbear_delivery_next.state_store.offline_proof import same_folder

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

MACHINE, LOCK = project_home.MACHINE, "machine.lock"
MACHINE_FORMAT = 8  # 2: the machine's own settings (TD-243, TD-288, TD-300); 3: its sessions (TD-336); 4: `active`;
# 5: one curation setting per trigger; 6: settings inherit Global's and were moved there once (the owner, 2026-10-23);
# 7: Improvement's machine settings: the budgets, Retro's triggers and the enrolled chats (2026-10-25);
# 8: no daily credit budgets; the Retro and paid replay run credit limits (2026-10-27)
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


DAILY = ("spotter_budget", "retro_budget", "retro_verbose_cap")  # format 7's daily credit budgets
BUDGETS_GONE = 8  # the format without them
_BUDGET: TypeAdapter[int | None] = TypeAdapter(Annotated[int, Field(ge=0)] | None)  # as format 7 read them: lax


def _budgets_dropped(settings: Any) -> Any:  # noqa: ANN401 - the raw settings
    """Format 7's daily budgets leave *settings* (D-01M5XCD49YHHR1NQKKY8TQD0C3); one format 7 refused is refused."""
    if not isinstance(settings, dict) or not any(k in settings for k in DAILY):
        return settings
    settings = dict(settings)
    for key in DAILY:
        if key in settings:
            _BUDGET.validate_python(settings.pop(key))
    return settings


class Machine(Record):
    """``machine.json``: the registered projects, the last Resume and the machine's settings."""

    format: int = MACHINE_FORMAT
    projects: list[Project] = Field(default_factory=list)
    resumed_at: datetime | None = None
    settings: Settings = Field(default_factory=Settings)  # each unset inherits Global's
    active: str = ""  # the highest version ever active here: never backwards (self-update build §4)
    settings_moved: bool = False  # its settings were moved into Global once, so it follows Global (2026-10-23)
    settings_moving: Settings | None = None  # the values a move took, kept across its retries until it is done
    settings_pending: str = ""  # why the carry or the move is not done yet; shown on the Settings page
    global_written: list[str] = Field(default_factory=list)  # the digest of the last carry or move write to Global,
    # kept until both are published

    @model_validator(mode="before")
    @classmethod
    def _no_daily_budgets(cls, data: Any) -> Any:  # noqa: ANN401 - the raw registry
        """Before format 8, the daily budgets leave the machine's settings and a move's kept values.

        From format 8 on, a budget is an unknown field and refused.
        """
        if isinstance(data, dict) and isinstance(found := data.get("format", 1), int) and found < BUDGETS_GONE:
            data = dict(data)
            for key in ("settings", "settings_moving"):
                if key in data:
                    data[key] = _budgets_dropped(data[key])
        return data


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


def save(machine: Machine, *, before_replace: Callable[[], None] | None = None) -> None:
    """Write under ``locked()``, owner-readable, optionally rechecking authority after the temporary is synced."""
    path = _home() / MACHINE
    machine.format = MACHINE_FORMAT
    atomic_write(path, machine.model_dump_json(indent=2) + "\n", before_replace=before_replace)
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
    work, store, _ = _canonical(path)
    return work, store


def _marker_at(store: Path, folder_fd: int | None) -> int:
    if folder_fd is None:
        return 0
    try:
        text = fd_tree.read_at(folder_fd, MARKER)
        return int(text) if text is not None else 0
    except (OSError, UnicodeError, ValueError) as exc:
        msg = f"{store / MARKER} is unreadable"
        raise RegistryError(msg) from exc


@contextlib.contextmanager
def _source_images(store: Path) -> Iterator[int | None]:
    """Keep canonical source images stable through all later validation reads, without creating a store."""
    folder_fd = None
    try:
        folder_fd = project_move.pin(store)
        images = (
            {
                name: fd_tree.stat_at(folder_fd, name)
                for name in (MARKER, project_move.CLONE_ID, project_move.MOVE_RECORD, ".")
            }
            if folder_fd is not None
            else {}
        )
        yield folder_fd
        if folder_fd is None:
            try:
                store.lstat()
            except FileNotFoundError:
                return
            msg = f"{store} appeared during canonical validation: nothing was registered"
            raise RegistryError(msg)
        if not all(fd_tree.same_image_at(folder_fd, name, before) for name, before in images.items()):
            found = _marker_at(store, folder_fd)
            if found > STORE_FORMAT and found != int(project_move.FENCE):
                msg = f"{store} has format {found}, newer than {STORE_FORMAT}: nothing was registered"
                raise RegistryError(msg)
            msg = f"{store}'s source witnesses changed during canonical validation: nothing was registered"
            raise RegistryError(msg)
        if not same_folder(store, folder_fd):
            msg = f"{store} no longer names the source being validated: nothing was registered"
            raise RegistryError(msg)
    except (OSError, StoreError) as exc:
        msg = f"{store}'s source witnesses cannot be checked: nothing was registered: {exc}"
        raise RegistryError(msg) from exc
    finally:
        if folder_fd is not None:
            os.close(folder_fd)


@contextlib.contextmanager
def _git_images(work: Path) -> Iterator[Path]:
    """Keep local worktree/Git-directory binding controls stable through later source validation reads."""
    try:
        with contextlib.ExitStack() as held:
            work_fd = os.open(work, fd_tree.DIR_FLAGS)
            held.callback(os.close, work_fd)
            references = GitImages()
            references.reference(work, ".git", "gitdir: ")
            gitdir = _git(work, "rev-parse", "--absolute-git-dir")
            git_fd = os.open(gitdir, fd_tree.DIR_FLAGS)
            held.callback(os.close, git_fd)
            references.reference(gitdir, "commondir")
            for name in ("gitdir", "config", "config.worktree"):
                references.path(gitdir / name)
            if _git(work, "rev-parse", "--show-toplevel") != work:
                msg = f"{work}'s Git worktree changed during validation: nothing was registered"
                raise RegistryError(msg)
            store = store_of(work)
            common_fd = os.open(store.parent, fd_tree.DIR_FLAGS)
            held.callback(os.close, common_fd)
            for name in ("config", "config.worktree"):
                references.path(store.parent / name)
            yield store
            references.confirm()
            if (
                not same_folder(work, work_fd)
                or not same_folder(gitdir, git_fd)
                or not same_folder(store.parent, common_fd)
            ):
                msg = f"{work}'s Git directory binding changed during validation: nothing was registered"
                raise RegistryError(msg)
    except (OSError, StoreError) as exc:
        msg = f"{work}'s Git directory binding cannot be checked: nothing was registered: {exc}"
        raise RegistryError(msg) from exc


def _canonical(path: Path) -> tuple[Path, Path, str | None]:
    """Canonical paths and the exact clone id their authority admitted, before any durability work."""
    try:
        work = _git(path.resolve(strict=True), "rev-parse", "--show-toplevel")
    except OSError as exc:
        msg = f"{path} does not exist"
        raise RegistryError(msg) from exc
    _owned(work)
    with _git_images(work) as store:
        _owned(store.parent)
        with _source_images(store) as folder_fd:
            found = _marker_at(store, folder_fd)
            pid = clone_id(store)
            switched = _switched(store, pid)  # any move receipt is validated, whatever the marker says
            if not switched and clone_id(store) != pid:
                msg = f"{store}'s clone id changed during canonical validation: nothing was registered"
                raise RegistryError(msg)
            if switched and found != int(project_move.FENCE):
                msg = (
                    f"{work}'s Delivery state has a SWITCHED receipt but format {found}, "
                    f"not {project_move.FENCE}: refusing"
                )
                raise RegistryError(msg)
            if found > STORE_FORMAT and (found != int(project_move.FENCE) or not switched):
                msg = f"{work}'s Delivery state has format {found}, newer than {STORE_FORMAT}: this OwlBear is older"
                raise RegistryError(msg)
            return work, store, pid


def _switched(store: Path, pid: str | None) -> bool:
    """Whether the *store*'s move receipt is a valid SWITCHED one naming its project's store; False when there is none.

    Raises:
        RegistryError: A receipt exists but is bad, pending or names another store, or the clone has no id.
    """
    if pid is None:
        if os.path.lexists(store / project_move.MOVE_RECORD):
            msg = f"{store} has a move receipt but no clone id: nothing was registered"
            raise RegistryError(msg)
        return False
    try:
        return switched_authority.retained_target(store, pid) is not None
    except StoreError as exc:
        raise RegistryError(str(exc)) from exc


def clone_id(store: Path) -> str | None:
    """The id written into the clone's folder, or None when there is none."""
    try:
        return project_home.clone_id(store)
    except StoreError as exc:
        raise RegistryError(str(exc)) from exc


def _ensure_id(work: Path, store: Path, expected: str | None) -> str:
    """Make the admitted id durable, then revalidate authority without changing the id that was admitted."""
    try:
        pid = project_home.ensure_id(store)
    except StoreError as exc:
        raise RegistryError(str(exc)) from exc
    if (expected is not None and pid != expected) or clone_id(store) != pid:
        msg = f"{store}'s clone id changed while it was made durable: nothing was registered"
        raise RegistryError(msg)
    _, checked, actual = _canonical(work)
    if checked != store or actual != pid:
        msg = f"{work}'s clone changed after its id was made durable: nothing was registered"
        raise RegistryError(msg)
    return pid


def _revalidate(work: Path, store: Path, pid: str) -> None:
    """Fence registry publication with the same canonical paths and id admitted before the write."""
    try:
        same = _canonical(work) == (work, store, pid)
    except RegistryError as exc:
        msg = f"{work}'s clone is no longer admissible: nothing was registered; check the clone and retry: {exc}"
        raise RegistryError(msg) from exc
    if not same:
        msg = f"{work}'s clone changed before publication: nothing was registered; check the clone and retry"
        raise RegistryError(msg)


def register(path: Path) -> Project:
    """Add the clone at *path*; refused when it is registered already, under its id or its path."""
    work, store, admitted = _canonical(path)
    with locked():
        machine = load()
        if found := next((p for p in machine.projects if p.path == str(work)), None):
            msg = f"{work} is registered already (project {found.id})"
            raise RegistryError(msg)
        pid = _ensure_id(work, store, admitted)
        if found := next((p for p in machine.projects if p.id == pid), None):
            msg = f"this clone is registered already at {found.path}; remove that project first"
            raise RegistryError(msg)
        project = Project(id=pid, path=str(work), added_at=datetime.now(UTC))
        machine.projects.append(project)
        save(machine, before_replace=lambda: _revalidate(work, store, pid))
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
        work, store, admitted = _canonical(Path(old.path))
        new = Project(id=_ensure_id(work, store, admitted), path=str(work), added_at=datetime.now(UTC))
        if any(p.id == new.id and p.id != pid for p in machine.projects):
            msg = f"this clone is registered already as project {new.id}"
            raise RegistryError(msg)
        machine.projects = [new if p.id == pid else p for p in machine.projects]
        save(machine, before_replace=lambda: _revalidate(work, store, new.id))
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
