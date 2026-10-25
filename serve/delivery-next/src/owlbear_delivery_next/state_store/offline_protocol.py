"""Prepare, reboot, finish: the gates a cross-volume store move must pass before any state changes.

Prepare records the source folder's identity and the boot session it was prepared in, and installs the
future-format fence every older runtime already refuses. Finish refuses unless a different boot session is
readable, the record and the fence still match the folder, and every legacy producer is proven fenced.
"""

import json
import re
import subprocess
import sys
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.state_store import project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.legacy_family import Gap, open_gaps

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PREPARED = project_move.PREPARED
FENCE = project_move.FENCE
UUID = re.compile(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}")
SYSCTL = "/usr/sbin/sysctl"


def boot_session() -> str:
    """Return the kernel boot-session UUID; refuse when the facility is missing, unreadable or malformed."""
    if sys.platform != "darwin":
        msg = "no boot-session facility on this platform: refusing the offline move"
        raise StoreError(msg)
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, no shell, no input
            [SYSCTL, "-n", "kern.bootsessionuuid"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"boot-session UUID is unreadable ({exc}): refusing the offline move"
        raise StoreError(msg) from exc
    text = done.stdout.strip()
    if done.returncode != 0 or not UUID.fullmatch(text):
        msg = "boot-session UUID is missing or malformed: refusing the offline move"
        raise StoreError(msg)
    return text


def _identity(folder: Path) -> list[int]:
    st = folder.stat(follow_symlinks=False)
    return [st.st_dev, st.st_ino]


def _record(folder: Path) -> dict:
    path = folder / PREPARED
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        msg = f"{path} is missing: nothing was prepared, so nothing moves"
        raise StoreError(msg) from exc
    except (OSError, ValueError) as exc:
        msg = f"{path} is unreadable: refusing the offline move"
        raise StoreError(msg) from exc
    if not isinstance(data, dict) or set(data) != {"boot", "folder", "marker"} or not _witnessed(data):
        msg = f"{path} is not a preparation record OwlBear wrote: refusing the offline move"
        raise StoreError(msg)
    return data


def _witnessed(data: dict) -> bool:
    """A stored boot is a UUID and the folder identity two integers; anything else is unknown, never a new boot."""
    folder = data["folder"]
    return (
        isinstance(data["boot"], str)
        and UUID.fullmatch(data["boot"].upper()) is not None
        and isinstance(folder, list)
        and len(folder) == 2  # noqa: PLR2004 - a (device, inode) pair
        and all(type(part) is int for part in folder)
        and isinstance(data["marker"], str)
    )


def prepare(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Record the folder's identity and boot session and install the fence; refuse first if a producer is unfenced."""
    boot = boot_session()
    open_gaps = gaps()
    if open_gaps:
        msg = _unfenced(open_gaps)
        raise StoreError(msg)
    marker = folder / MARKER
    current = marker.read_text().strip() if marker.exists() else ""
    if current == FENCE:
        # Repeated prepare keeps the existing generation; the fence is never recorded as the prior format.
        return _record(folder)
    if current and not current.isdigit():
        msg = f"the format marker {current!r} is malformed: refusing the offline move"
        raise StoreError(msg)
    if current and int(current) >= int(FENCE):
        msg = f"the format marker {current} is not a prior format: refusing the offline move"
        raise StoreError(msg)
    previous = marker.read_text() if marker.exists() else ""
    record = {"boot": boot, "folder": _identity(folder), "marker": previous}
    atomic_write(folder / PREPARED, json.dumps(record) + "\n")
    atomic_write(marker, f"{FENCE}\n")
    return record


def finish(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> project_move.OfflineProof:
    """Verify every precondition; return the only proof the migrator accepts, or raise before any state changes."""
    record = _record(folder)
    boot = boot_session()
    if boot.upper() == record["boot"].upper():  # UUID case variants name the same boot session
        msg = "still the boot session the source was prepared in: reboot before finishing; nothing moves"
        raise StoreError(msg)
    if record["folder"] != _identity(folder):
        msg = f"{folder} is not the folder that was prepared: refusing the offline move"
        raise StoreError(msg)
    marker = folder / MARKER
    if not marker.exists() or marker.read_text().strip() != FENCE:
        msg = f"the format fence on {folder} is missing or altered: refusing the offline move"
        raise StoreError(msg)
    open_gaps = gaps()
    if open_gaps:
        raise StoreError(_unfenced(open_gaps))
    return project_move.OfflineProof(folder, str(record["marker"]))


def prepare_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Prepare the clone's own store folder for the offline move; the only entry that installs the fence."""
    folder = project_home.clone_dir(cwd)
    return prepare(folder, gaps)


def finish_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> Path:
    """Finish after reboot: prove the preparation, then run the whole-store move; return the project's home."""
    folder = project_home.clone_dir(cwd)
    proof = finish(folder, gaps)
    return project_home.migrated(cwd, proof)


def _unfenced(found: tuple[Gap, ...]) -> str:
    detail = "; ".join(f"{g.path} ({g.version}): {g.reason}" for g in found)
    return f"legacy producers are not proven fenced, so the offline move is refused, nothing was changed: {detail}"
