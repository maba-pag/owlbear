"""Dependencies in the Change's read-only worktree: a package's install command runs again when its inputs change.

The reset before each session keeps ignored files, so what an install put there stays for the next session. The digest
of each package's install inputs at its last successful install is kept in the Change's store folder.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.steps import check, worktree
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Lock, Store

STATE = "ro-installs.json"
INPUTS = (
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
    "pyproject.toml", "uv.lock", "poetry.lock", "Pipfile.lock",
)  # fmt: skip


def ready(store: Store, lock: Lock, change: Change, at: Path) -> str:
    """Install the Change's packages in *at* whose inputs changed since; one line per failed install, else empty."""
    folder = store.root / "changes" / change.slug
    done = _read(folder / STATE)
    scope = sorted({p for t in (change.plan.tasks if change.plan else []) for p in t.scope} | set(change.brief.scope))
    notes = []
    for package, command in worktree.installs(store.read_profile() or Profile(), scope):
        home = at / package.strip("/") if package.strip("/") not in {"", "."} else at
        if not home.is_dir() or done.get(package) == (digest := _digest(home, command)):
            continue
        start = time.monotonic()
        failed = check.run(shlex.split(command), home, lambda e: store.log(lock, change.slug, e))
        seconds = round(time.monotonic() - start, 1)
        now = datetime.now(UTC).isoformat(timespec="seconds")
        event = {"event": "ro-install", "at": now, "package": package, "command": command, "seconds": seconds}
        store.log(lock, change.slug, event | {"ok": not failed})
        if failed:
            done.pop(package, None)
            notes.append(f"Dependencies could not be installed in {package or '.'}: {failed}")
        else:
            done[package] = digest
        folder.mkdir(parents=True, exist_ok=True)
        atomic_write(folder / STATE, json.dumps(done, sort_keys=True))
    return "\n".join(notes)


def forget(folder: Path) -> None:
    """A new read-only worktree holds no dependencies yet."""
    (folder / STATE).unlink(missing_ok=True)


def _digest(home: Path, command: str) -> str:
    files = [home / n for n in INPUTS] + sorted(home.glob("requirements*.txt"))
    h = hashlib.sha256(command.encode())
    for f in (f for f in files if f.is_file()):
        h.update(f"\0{f.name}\0".encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def _read(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
