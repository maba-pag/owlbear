"""Delivery-next state store in ``~/.owlbear/projects/<id>/``, one folder per project (D4 §3.2, TD-334)."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import socket
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter, ValidationError

from owlbear_delivery_next.change_contracts.inbox import InboxItem, parse_rows
from owlbear_delivery_next.change_contracts.models import FORMAT, Change, Record
from owlbear_delivery_next.change_flow import answer_kinds, loop
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import config as settings_config
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, GlobalLayer, Layer, MachineLayer, Settings
from owlbear_delivery_next.state_store import config_save, profile_share, project_home
from owlbear_delivery_next.state_store.database import (
    STORE_FORMAT,
    Database,
    FormatTooNewError,
    LateWriteError,
    StoreError,
    append_activity,
    put_record,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Step
    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.change_flow.loop import PrState
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.settings.migrations import Migrations

CONFIG = "config.json"  # the project's settings layer (TD-52)
MACHINE_SETTINGS = "settings.json"  # this machine's preference layer in ~/.owlbear (TD-336)
ACTIVITY_LIMIT = 200
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_INBOX: TypeAdapter[InboxItem] = TypeAdapter(InboxItem)
HANDLE = re.compile(r"c\d{1,4}")  # the only handle shape the host issues


class Holder(Record):
    """Who holds a Change's writer lock; written into the lock file for the status line."""

    pid: int
    host: str
    since: datetime


__all__ = ["FormatTooNewError", "StoreError"]  # defined with the database, raised by every store operation


class SharedError(StoreError):
    """The shared settings repository could not be locked or found for a save (TD-57)."""

    action = "Check the shared settings repository, then try again"
    resume = "A settings save completes"


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


def _load[T: Record](path: Path, model: type[T], current: int, forward: Migrations) -> T:
    """Read one versioned record, refusing a newer format and migrating an older one forward."""
    name = path.parent.name if path.name == "change.json" else path.stem
    try:
        raw = path.read_text()
    except (OSError, ValueError) as exc:  # ValueError: bytes that are not UTF-8
        msg = f"state of {name} is unreadable"
        raise StoreError(msg) from exc
    return _parse(raw, name, model, current, forward)


def _parse[T: Record](raw: str, name: str, model: type[T], current: int, forward: Migrations) -> T:
    try:
        data = json.loads(raw)
        version = int(data.get("format", 0))
    except (AttributeError, TypeError, ValueError) as exc:
        msg = f"state of {name} is unreadable"
        raise StoreError(msg) from exc
    if version > current:
        msg = f"{name} has format {version}, newer than {current}"
        raise FormatTooNewError(msg)
    written = version
    try:
        while version < current:
            data = forward[version](data)
            version += 1
            data["format"] = version
        return model.model_validate(data)
    except ValidationError as exc:
        if written < current:
            msg = f"state of {name} cannot be migrated to format {current}"
        else:  # the current format with fields this Delivery does not know: a newer or different one wrote it
            msg = f"state of {name} was written by a newer or different Delivery ({_first(exc)})"
        raise StoreError(msg) from exc
    except (KeyError, TypeError, ValueError) as exc:
        msg = f"state of {name} cannot be migrated to format {current}"
        raise StoreError(msg) from exc


def _first(exc: ValidationError) -> str:
    error = exc.errors()[0]
    said = {"extra_forbidden": "unknown field", "missing": "missing field"}.get(error["type"], "invalid field")
    return f"{said} {'.'.join(map(str, error['loc']))}"


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
    return _parse(text, path.stem, model, CONFIG_FORMAT, migrations.CONFIG), raw


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
    """Change records, locks, inboxes and activity logs of one clone; the records live in its database (TD-265)."""

    def __init__(self, root: Path, shared: DataRepo | None = None, name: str = "") -> None:
        self.root, self.shared, self.name = root, shared, name
        self.global_path = shared.global_path if shared else None
        self.db = Database(root)

    @property
    def config_path(self) -> Path:
        """The project's settings layer: in its shared folder, which a rename moves (TD-98), else in the clone."""
        return self.shared.project_path(self.name) if self.shared else self.root / CONFIG

    @classmethod
    def open(cls, cwd: Path) -> Store:
        """Open or create the store for the clone containing *cwd* and gate its format."""
        try:
            shared = data_repo.locate()
            name = data_repo.folder(shared, cwd) if shared else ""
        except data_repo.DataRepoError as exc:
            raise StoreError(str(exc)) from exc
        store = cls(project_home.located(cwd), shared, name)
        if (found := store.db.marker()) > STORE_FORMAT:  # the database itself opens with the first operation
            msg = f"store format {found} is newer than {STORE_FORMAT}"
            raise FormatTooNewError(msg)
        try:
            store.adopt(data_repo.identity(cwd) if shared else "")
            profile_share.move_roles(store)
            profile_share.adopt(store)
        except data_repo.DataRepoError as exc:
            raise StoreError(str(exc)) from exc
        return store

    def adopt(self, identity: str) -> None:
        """Claim the project's shared folder, then move the clone's own settings there once; the old file stays.

        A publication that fails stays visible on the settings page (``DataRepo.pending``) until a later save sends it.
        """
        if not self.shared:
            return
        local, claim = self.root / CONFIG, self.shared.root / self.name / data_repo.CLAIM
        moving = local.exists() and not self.config_path.exists()
        if not moving and claim.exists() and claim.read_text().strip() == identity:
            return  # nothing to do, so no wait for a save that holds the lock
        with self.shared.locked():
            if self.shared.claim(self.name, identity):
                self.shared.publish(claim, f"settings: the folder {self.name} is {identity}")
            if not local.exists() or self.config_path.exists():
                return
            read_layer(local, Layer)  # a damaged clone file is reported, never copied
            atomic_write(self.config_path, local.read_text())
            self.shared.publish(self.config_path, f"settings: {self.name} moved from its clone")
            local.replace(local.with_name(f"{CONFIG}.moved"))  # kept as the recovery copy

    def save[T: Layer](
        self, path: Path, model: type[T], change: Callable[[T], T], what: str, *, owner: bool = False
    ) -> str:
        """Change one settings layer and publish it; what the owner should know about the publication, else nothing."""
        if not self.shared:
            update_layer(path, model, change)
            return ""
        try:
            until = time.monotonic() + data_repo.SAVE_SECONDS  # the lock wait and every git command share it
            return config_save.locked_save(self, path, model, change, f"settings: {what}", until, owner=owner)
        except data_repo.DataRepoError as exc:
            raise SharedError(str(exc)) from exc

    def read_config(self) -> Layer:
        """The project's settings layer."""
        return read_layer(self.config_path, Layer)

    @property
    def machine_path(self) -> Path:
        """This machine's preference layer in ``~/.owlbear``: local, never published (TD-336)."""
        return local_home.root() / MACHINE_SETTINGS

    def update_config(self, change: Callable[[Layer], Layer], what: str = "project layer") -> str:
        """Change and publish the project's settings layer; the publication notice, else nothing."""
        return self.save(self.config_path, Layer, change, f"{self.name or 'the project'}: {what}")

    def settings(self) -> Settings:
        """The resolved settings: the project layer over this machine's over the global one; no code defaults (R15)."""
        glob = read_layer(self.global_path, GlobalLayer) if self.global_path else None
        try:
            return settings_config.resolve(glob, self.read_config(), read_layer(self.machine_path, MachineLayer))
        except ValidationError as exc:  # each layer is valid, their combination is not (TD-209)
            msg = f"the settings do not combine: {exc.errors()[0]['msg']}"
            raise StoreError(msg) from exc

    def _dir(self, slug: str) -> Path:
        """The Change's folder of run locks and artifacts."""
        if "." in slug or "/" in slug:
            msg = f"{slug} is not a Change name: it holds a dot or a slash"
            raise StoreError(msg)
        path = self.root / "changes" / slug
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path

    def visual_dir(self, slug: str, head: str) -> Path:
        """The screenshots of one Change's visual check at *head*."""
        return self.root / "changes" / slug / "visual" / head[:7]

    def before_dir(self, slug: str, base: str) -> Path:
        """The "before" screenshots of one Change at its merge-base *base* (TD-24)."""
        return self.root / "changes" / slug / "before" / base[:7]

    def _record(self, slug: str) -> str:
        with self.db.read() as db:
            row = db.execute("SELECT record FROM changes WHERE slug = ?", (slug,)).fetchone()
        if (late := self.root / "changes" / slug / "change.json").exists():  # never silently ignored (TD-265)
            msg = f"an older OwlBear wrote {late} after {slug} moved to the database"
            raise LateWriteError(msg)
        if row is None:
            msg = f"state of {slug} is unreadable"
            raise StoreError(msg)
        return row[0]

    def read(self, slug: str) -> Change:
        """Read one Change, migrating an older format forward."""
        return _parse(self._record(slug), slug, Change, FORMAT, migrations.CHANGE)

    def rev(self, slug: str) -> int | None:
        """How often the Change's record was written; None when there is none."""
        with self.db.read() as db:
            row = db.execute("SELECT rev FROM changes WHERE slug = ?", (slug,)).fetchone()
        return row[0] if row else None

    def raw_handle(self, slug: str) -> str | None:
        """The handle in the Change record without loading it, for a Change that cannot be read; None if absent."""
        try:
            handle = json.loads(self._record(slug)).get("handle")
        except AttributeError, StoreError, ValueError:
            return None
        return handle if isinstance(handle, str) and HANDLE.fullmatch(handle) else None

    def issued(self) -> int:
        """The highest handle number ever issued here, kept apart so a lost or restored Change never frees one."""
        with self.db.read() as db:
            row = db.execute("SELECT value FROM meta WHERE key = 'issued'").fetchone()
        return int(row[0]) if row and row[0].isdigit() else 0

    def issue(self, number: int) -> None:
        """Record *number* as issued; the mark never goes down."""
        with self.db.write() as db:
            row = db.execute("SELECT value FROM meta WHERE key = 'issued'").fetchone()
            if not (row and row[0].isdigit() and int(row[0]) >= number):
                db.execute("INSERT OR REPLACE INTO meta VALUES ('issued', ?)", (str(number),))

    def read_profile(self) -> Profile | None:
        """Read the confirmed project profile under its own format gate; None before confirmation."""
        return profile_share.read(self)

    def write_profile(self, profile: Profile, *, replace_unreadable: bool = False) -> str:
        """Write the project profile atomically, published when shared (TD-147); the publication notice."""
        try:
            return profile_share.write(self, profile, replace_unreadable=replace_unreadable)
        except data_repo.DataRepoError as exc:
            raise SharedError(str(exc)) from exc

    mark_prefs_import = profile_share.mark  # a method: profile_share.mark takes the store first
    retry_prefs_import = profile_share.retry

    def write(self, lock: Lock, change: Change) -> None:
        """Write one Change, keeping the previous record as ``prev``."""
        lock.check(change.slug)
        self._dir(change.slug)
        with self.db.write() as db:
            put_record(db, change.slug, change.model_dump_json(indent=1))

    def slugs(self) -> list[str]:
        """Return every Change of this clone."""
        with self.db.read() as db:
            stored = {row[0] for row in db.execute("SELECT slug FROM changes")}
        return sorted(stored | set(self.db.legacy_slugs()))  # one an older OwlBear wrote since shows as unreadable

    def restore(self, lock: Lock, slug: str) -> None:
        """Replace the current Change record with its previous version."""
        lock.check(slug)
        with self.db.write() as db:
            row = db.execute("SELECT prev FROM changes WHERE slug = ?", (slug,)).fetchone()
            if not (row and row[0] is not None):
                msg = f"{slug} has no previous state"
                raise StoreError(msg)
            db.execute("UPDATE changes SET record = prev, rev = rev + 1 WHERE slug = ?", (slug,))

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
        """Add one inbox item without the Change lock; only a lock holder folds it."""
        name = f"{time.time_ns():020d}-{uuid.uuid4().hex[:8]}.json"
        self._dir(slug)
        with self.db.write() as db:
            db.execute(
                "INSERT INTO inbox(slug, name, item) VALUES (?, ?, ?)", (slug, name, _INBOX.dump_json(item).decode())
            )

    def fold(  # noqa: PLR0913 - the PR observation and the queue barrier
        self,
        lock: Lock,
        slug: str,
        now: datetime,
        pr_state: PrState | None = None,
        *,
        moved: bool = False,
        leave: Callable[[Change, Change], Change | None] | None = None,
    ) -> tuple[Change, Step | None]:
        """Fold the inbox under the lock: the Change and the removal of exactly the items it took commit together.

        No transaction spans the computation or ``leave``, which sees the Change before and after folding; None
        keeps every item waiting and nothing is written. Items an older process left as files are taken first.
        """
        lock.check(slug)
        self.db.ingest(slug, self._dir(slug) / "inbox")
        change = self.read(slug)
        before = change
        with self.db.read() as db:
            rows = db.execute("SELECT id, item FROM inbox WHERE slug = ? ORDER BY name, id", (slug,)).fetchall()
        items, rejected = parse_rows(rows)  # rejected items are taken all the same, and kept in the activity
        at = now.isoformat(timespec="seconds")
        events = [{"event": "inbox-rejected", "at": at, "item": text[:2000]} for text in rejected]
        asked = loop.open_question(change) if loop.waiting_consent(change) else None
        try:
            asking = self.settings().prefs.ask_before_merge is not False  # unset asks; only an explicit no turns it off
        except StoreError:  # unreadable or invalid settings: the owner's controls still fold; the runner reports it
            asking = True
        change, step = loop.schedule(change, items, now, pr_state, moved=moved, asking=asking)
        if leave is not None:
            kept = leave(before, change)
            if kept is None:  # a queued PR could not be taken out yet: the items wait for the next pass
                return before, loop.next_step(before, now)
            change = kept
        change.inbox_acked = []
        if asked and any(q.id == asked.id and q.answer and q.answer.option == loop.OBSOLETE for q in change.questions):
            events.append({"event": "consent-obsolete", "at": now.isoformat(timespec="seconds"), "question": asked.id})
        events += answer_kinds.logged(change, items, now)  # TD-461: each answer's class
        with self.db.write() as db:
            put_record(db, change.slug, change.model_dump_json(indent=1))
            db.executemany("DELETE FROM inbox WHERE id = ?", [(row[0],) for row in rows])
            for event in events:
                append_activity(db, slug, json.dumps(event, default=str, sort_keys=True), ACTIVITY_LIMIT)
        return change, step

    def events(self, slug: str) -> list[dict[str, Any]]:
        """Return the retained activity events, oldest first."""
        with self.db.read() as db:
            rows = db.execute("SELECT event FROM activity WHERE slug = ? ORDER BY id", (slug,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def log(self, lock: Lock, slug: str, event: dict[str, Any]) -> None:
        """Append one activity event, keeping only the last ``ACTIVITY_LIMIT``."""
        lock.check(slug)
        with self.db.write() as db:
            append_activity(db, slug, json.dumps(event, default=str, sort_keys=True), ACTIVITY_LIMIT)

    def now(self, slug: str) -> dict[str, Any] | None:
        """Return the step's latest tool call, or None when none was recorded or it is unreadable."""
        with self.db.read() as db:
            row = db.execute("SELECT data FROM now WHERE slug = ?", (slug,)).fetchone()
        try:
            data = json.loads(row[0]) if row else None
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def write_now(self, lock: Lock, slug: str, data: dict[str, Any]) -> None:
        """Overwrite the now line; it is a hint for status and never part of activity."""
        lock.check(slug)
        with self.db.write() as db:
            db.execute("INSERT OR REPLACE INTO now VALUES (?, ?)", (slug, json.dumps(data, sort_keys=True)))
