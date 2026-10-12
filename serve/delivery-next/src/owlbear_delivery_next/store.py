"""Delivery-next state store in ``<git-common-dir>/owlbear-delivery/`` (D4 §3.2)."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter, ValidationError

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.config import CONFIG_FORMAT, Agent, GlobalLayer, Layer, Settings, resolve
from owlbear_delivery_next.inbox import InboxItem
from owlbear_delivery_next.models import FORMAT, Change, ErrorKind, Record, Role, Stop
from owlbear_delivery_next.profile_record import PROFILE_FORMAT, Profile, RoleModel
from owlbear_delivery_next.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.loop import PrState
    from owlbear_delivery_next.models import Step

STORE_DIR = "owlbear-delivery"
CONFIG = "config.json"  # the project's settings layer (TD-52)
ROLES_MOVED = "roles-moved"  # marks that a format-1 profile's role overrides were merged into CONFIG
ACTIVITY_LIMIT = 200
type Migrations = dict[int, Callable[[dict[str, Any]], dict[str, Any]]]
_ROLES: TypeAdapter[dict[Role, RoleModel]] = TypeAdapter(dict[Role, RoleModel])


def _roles_moved(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 1 to 2: the role overrides moved to the project settings; each is checked, then dropped."""
    _ROLES.validate_python(data.pop("roles", {}))
    return data


def _with_roles(layer: Layer, found: dict[Role, RoleModel]) -> Layer:
    """The layer with old role overrides filling only the model and effort fields it leaves empty."""
    agents = dict(layer.agents)
    for role, old in found.items():
        own = agents.get(role, Agent())
        agents[role] = own.model_copy(update={"model": own.model or old.model, "effort": own.effort or old.effort})
    return layer.model_copy(update={"agents": agents})


# Forward migrations of a Change or profile record, keyed by the format they upgrade from.
MIGRATIONS: Migrations = {}
PROFILE_MIGRATIONS: Migrations = {1: _roles_moved}
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_INBOX: TypeAdapter[InboxItem] = TypeAdapter(InboxItem)
HANDLE = re.compile(r"c\d{1,4}")  # the only handle shape the host issues


class Holder(Record):
    """Who holds a Change's writer lock; written into the lock file for the status line."""

    pid: int
    host: str
    since: datetime


class StoreError(Exception):
    """State that cannot be used; the loop shows it as a ``state`` stop."""

    action = "Restore the previous state"
    resume = "State loads"

    def stop(self, now: datetime) -> Stop:
        """Return the stop record for this error."""
        return Stop(kind=ErrorKind.STATE, reason=str(self), action=self.action, resume=self.resume, at=now)


class FormatTooNewError(StoreError):
    """The state was written by a newer OwlBear."""

    action = "Upgrade OwlBear"
    resume = "State loads on the newer OwlBear"


class LockHeldError(RuntimeError):
    """Another process holds the Change's writer lock."""

    def __init__(self, holder: Holder | None) -> None:
        super().__init__(f"Change lock held by {holder.pid if holder else 'an unknown process'}")
        self.holder = holder


class Lock:
    """Proof that this process holds one Change's writer lock."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.held = True

    def check(self, slug: str) -> None:
        """Raise unless this lock is held for *slug*."""
        if not (self.held and self.slug == slug):
            msg = f"writer lock for {slug} is not held"
            raise RuntimeError(msg)


def git_common_dir(cwd: Path) -> Path:
    """Return the clone's common git directory; the same from every worktree."""
    git = shutil.which("git") or "git"
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [git, "rev-parse", "--git-common-dir"], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()
    return (cwd / out).resolve()


def _load[T: Record](path: Path, model: type[T], current: int, migrations: Migrations) -> T:
    """Read one versioned record, refusing a newer format and migrating an older one forward."""
    name = path.parent.name if path.name == "change.json" else path.stem
    try:
        raw = path.read_text()
    except (OSError, ValueError) as exc:  # ValueError: bytes that are not UTF-8
        msg = f"state of {name} is unreadable"
        raise StoreError(msg) from exc
    return _parse(raw, name, model, current, migrations)


def _parse[T: Record](raw: str, name: str, model: type[T], current: int, migrations: Migrations) -> T:
    try:
        data = json.loads(raw)
        version = int(data.get("format", 0))
    except (AttributeError, TypeError, ValueError) as exc:
        msg = f"state of {name} is unreadable"
        raise StoreError(msg) from exc
    if version > current:
        msg = f"{name} has format {version}, newer than {current}"
        raise FormatTooNewError(msg)
    try:
        while version < current:
            data = migrations[version](data)
            version += 1
            data["format"] = version
        return model.model_validate(data)
    except (KeyError, TypeError, ValueError) as exc:
        msg = f"state of {name} cannot be migrated to format {current}"
        raise StoreError(msg) from exc


def read_layer[T: Layer](path: Path, model: type[T]) -> T:
    """One settings layer under its format gate; an empty layer before the first save."""
    return read_layer_bytes(path, model)[0]


def read_layer_bytes[T: Layer](path: Path, model: type[T]) -> tuple[T, bytes]:
    """One settings layer and the exact bytes it was parsed from; an absent file is the empty layer."""
    try:
        raw = path.read_bytes()
        text = raw.decode()
    except FileNotFoundError:
        return model(), b""
    except (OSError, ValueError) as exc:  # ValueError: bytes that are not UTF-8
        msg = f"state of {path.stem} is unreadable"
        raise StoreError(msg) from exc
    return _parse(text, path.stem, model, CONFIG_FORMAT, {}), raw


def update_layer[T: Layer](path: Path, model: type[T], change: Callable[[T], T]) -> T:
    """Read, change and write one layer under its own lock, so no concurrent save is lost; invalid writes nothing."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dir_fd = os.open(path.parent, _DIR_FLAGS)
    try:
        fd = open_lock(dir_fd, blocking=True, name=f".{path.name}.lock")
    finally:
        os.close(dir_fd)
    try:
        new = model.model_validate(change(read_layer(path, model)).model_dump())
        atomic_write(path, new.model_dump_json(indent=1))
        return new
    finally:
        os.close(fd)


class Store:
    """Change records, locks, inboxes and activity logs of one clone."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def open(cls, cwd: Path) -> Store:
        """Open or create the store for the clone containing *cwd* and gate its format."""
        store = cls(git_common_dir(cwd) / STORE_DIR)
        store.root.mkdir(mode=0o700, exist_ok=True)
        marker = store.root / "format"
        try:
            found = int(marker.read_text()) if marker.exists() else 0
        except (OSError, ValueError) as exc:
            msg = "store format marker is unreadable"
            raise StoreError(msg) from exc
        if found > FORMAT:
            msg = f"store format {found} is newer than {FORMAT}"
            raise FormatTooNewError(msg)
        if found < FORMAT:
            atomic_write(marker, f"{FORMAT}\n")
        store.move_roles()
        return store

    def move_roles(self) -> None:
        """Merge a format-1 profile's role overrides into the project settings, once.

        Fields the settings already set win; the old values fill only the empty ones. A marker then records the
        move, so an override cleared later never returns while the old profile is still on disk. An unreadable or
        invalid profile or settings file is left to ``read_profile`` and ``read_config`` to report.
        """
        path, config, marker = self.root / "profile.json", self.root / CONFIG, self.root / ROLES_MOVED
        if marker.exists() or not path.exists():
            return
        dir_fd = os.open(self.root, _DIR_FLAGS)
        try:
            fd = open_lock(dir_fd, blocking=True, name=f".{ROLES_MOVED}.lock")
        finally:
            os.close(dir_fd)
        try:
            if marker.exists():  # another opener finished the move while this one waited
                return
            try:
                data = json.loads(path.read_text())
                found = _ROLES.validate_python(data.get("roles", {})) if int(data.get("format", 0)) == 1 else {}
            except AttributeError, OSError, TypeError, ValueError:
                return  # read_profile reports the damaged profile
            if found:
                try:
                    update_layer(config, Layer, lambda cur: _with_roles(cur, found))
                except StoreError:
                    return  # refused before writing; read_config reports the damaged settings
            atomic_write(marker, "the format-1 profile's role overrides are merged into config.json\n")
        finally:
            os.close(fd)

    def read_config(self) -> Layer:
        """The project's settings layer."""
        return read_layer(self.root / CONFIG, Layer)

    def update_config(self, change: Callable[[Layer], Layer]) -> Layer:
        """Change the project's settings layer under its lock."""
        return update_layer(self.root / CONFIG, Layer, change)

    def settings(self, glob: GlobalLayer | None = None) -> Settings:
        """The resolved settings; the caller passes the global layer, whose location is the owner's decision."""
        return resolve(glob, self.read_config())

    def _dir(self, slug: str) -> Path:
        path = self.root / "changes" / slug
        (path / "inbox").mkdir(parents=True, exist_ok=True)
        return path

    def visual_dir(self, slug: str, head: str) -> Path:
        """The screenshots of one Change's visual check at *head*."""
        return self.root / "changes" / slug / "visual" / head[:7]

    def before_dir(self, slug: str, base: str) -> Path:
        """The "before" screenshots of one Change at its merge-base *base* (TD-24)."""
        return self.root / "changes" / slug / "before" / base[:7]

    def read(self, slug: str) -> Change:
        """Read one Change, migrating an older format forward."""
        return _load(self._dir(slug) / "change.json", Change, FORMAT, MIGRATIONS)

    def raw_handle(self, slug: str) -> str | None:
        """The handle in the Change file without loading it, for a Change that cannot be read; None if absent."""
        try:
            handle = json.loads((self.root / "changes" / slug / "change.json").read_text()).get("handle")
        except AttributeError, OSError, ValueError:
            return None
        return handle if isinstance(handle, str) and HANDLE.fullmatch(handle) else None

    def issued(self) -> int:
        """The highest handle number ever issued here, kept apart so a lost or restored Change file never frees one."""
        try:
            number = json.loads((self.root / "handles.json").read_text()).get("issued")
        except AttributeError, OSError, ValueError:
            return 0
        return number if isinstance(number, int) else 0

    def issue(self, number: int) -> None:
        """Record *number* as issued, atomically; the mark never goes down."""
        if number > self.issued():
            atomic_write(self.root / "handles.json", json.dumps({"issued": number}))

    def read_profile(self) -> Profile | None:
        """Read the confirmed project profile under its own format gate; None before confirmation."""
        path = self.root / "profile.json"
        return _load(path, Profile, PROFILE_FORMAT, PROFILE_MIGRATIONS) if path.exists() else None

    def write_profile(self, profile: Profile) -> None:
        """Write the project profile atomically."""
        atomic_write(self.root / "profile.json", profile.model_dump_json(indent=1))

    def write(self, lock: Lock, change: Change) -> None:
        """Write one Change atomically, keeping the previous file as ``.prev``."""
        lock.check(change.slug)
        path, text = self._dir(change.slug) / "change.json", change.model_dump_json(indent=1)
        old = path.read_text() if path.exists() else None
        if old == text:
            return
        if old is not None:
            atomic_write(path.with_name("change.json.prev"), old)
        atomic_write(path, text)

    def slugs(self) -> list[str]:
        """Return every Change of this clone."""
        return sorted(p.parent.name for p in (self.root / "changes").glob("*/change.json"))

    def restore(self, lock: Lock, slug: str) -> None:
        """Replace the current Change file with its previous version."""
        lock.check(slug)
        path = self._dir(slug) / "change.json"
        atomic_write(path, path.with_name("change.json.prev").read_text())

    @contextlib.contextmanager
    def lock(self, slug: str) -> Iterator[Lock]:
        """Hold the Change's writer lock without waiting and record its holder.

        Raises:
            LockHeldError: Another process holds the lock.
        """
        dir_fd = os.open(self._dir(slug), _DIR_FLAGS)
        try:
            fd = open_lock(dir_fd, blocking=False, name="lock")
        except BlockingIOError as exc:
            raise LockHeldError(self.holder(slug)) from exc
        finally:
            os.close(dir_fd)
        held = Lock(slug)
        try:
            record = Holder(pid=os.getpid(), host=socket.gethostname(), since=datetime.now(UTC))
            os.ftruncate(fd, 0)
            os.pwrite(fd, record.model_dump_json().encode(), 0)
            yield held
        finally:
            held.held = False
            os.close(fd)

    @contextlib.contextmanager
    def merge_lock(self, target: str) -> Iterator[bool]:
        """Hold the per-target merge lock without waiting; yield False when another Change holds it."""
        name = "merge-" + "".join(ch if ch.isalnum() or ch in "._-" else f"%{ord(ch):02X}" for ch in target) + ".lock"
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        dir_fd = os.open(self.root, _DIR_FLAGS)
        try:
            fd = open_lock(dir_fd, blocking=False, name=name)
        except BlockingIOError:
            fd = None
        finally:
            os.close(dir_fd)
        try:
            yield fd is not None
        finally:
            if fd is not None:
                os.close(fd)

    def holder(self, slug: str) -> Holder | None:
        """Return the live holder of the Change lock, or None when nobody holds it."""
        try:
            fd = os.open(self._dir(slug) / "lock", os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            with contextlib.suppress(ValidationError):
                return Holder.model_validate_json(os.pread(fd, 4096, 0))
            return None
        finally:
            os.close(fd)
        return None

    def put_inbox(self, slug: str, item: InboxItem) -> None:
        """Write one inbox item without the Change lock; only a lock holder folds it."""
        name = f"{time.time_ns():020d}-{uuid.uuid4().hex[:8]}.json"
        atomic_write(self._dir(slug) / "inbox" / name, _INBOX.dump_json(item).decode())

    def fold(
        self, lock: Lock, slug: str, now: datetime, pr_state: PrState | None = None, *, moved: bool = False
    ) -> tuple[Change, Step | None]:
        """Fold the inbox under the lock; consumed item names are saved with the Change, so a replay skips them."""
        lock.check(slug)
        change = self.read(slug)
        present = sorted((self._dir(slug) / "inbox").glob("*.json"))
        acked = [n for n in change.inbox_acked if n in {p.name for p in present}]
        files: list[Path] = []
        items: list[InboxItem] = []
        for path in (p for p in present if p.name not in acked):
            try:
                items.append(_INBOX.validate_json(path.read_bytes()))
                files.append(path)
            except ValidationError:
                path.rename(path.with_suffix(".rejected"))
        asked = loop.open_question(change) if loop.waiting_consent(change) else None
        asking = profile.value(self.read_profile() or Profile(), profile.ASK) == "yes"
        change, step = loop.schedule(change, items, now, pr_state, moved=moved, asking=asking)
        change.inbox_acked = acked + [p.name for p in files]
        self.write(lock, change)
        if asked and any(q.id == asked.id and q.answer and q.answer.option == loop.OBSOLETE for q in change.questions):
            at = now.isoformat(timespec="seconds")
            self.log(lock, slug, {"event": "consent-obsolete", "at": at, "question": asked.id})
        for path in present:
            path.unlink(missing_ok=True)
        return change, step

    def events(self, slug: str) -> list[dict[str, Any]]:
        """Return the retained activity events, oldest first."""
        path = self._dir(slug) / "activity.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []

    def log(self, lock: Lock, slug: str, event: dict[str, Any]) -> None:
        """Append one activity event, keeping only the last ``ACTIVITY_LIMIT``."""
        lock.check(slug)
        path = self._dir(slug) / "activity.jsonl"
        lines = path.read_text().splitlines() if path.exists() else []
        lines.append(json.dumps(event, default=str, sort_keys=True))
        atomic_write(path, "\n".join(lines[-ACTIVITY_LIMIT:]) + "\n")

    def now(self, slug: str) -> dict[str, Any] | None:
        """Return the step's latest tool call, or None when none was recorded or it is unreadable."""
        path = self._dir(slug) / "now.json"
        try:
            data = json.loads(path.read_text())
        except OSError, ValueError:
            return None
        return data if isinstance(data, dict) else None

    def write_now(self, lock: Lock, slug: str, data: dict[str, Any]) -> None:
        """Overwrite the now line; it is a hint for status and never part of activity."""
        lock.check(slug)
        atomic_write(self._dir(slug) / "now.json", json.dumps(data, sort_keys=True))
