"""Storage surface for owlbear-kanban: canonical I/O, corruption detection, quarantine.

Provides a higher-level interface over task_io with:
- Canonical frontmatter field ordering per §2.3 (AC-C13)
- UTC timestamp normalisation on write (AC-C15)
- Legacy ``claimed_by`` stripping on read (AC-C48)
- Corruption detection returning an error value (AC-C16)
- Quarantine operations (AC-C28, AC-C29)
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap

from owlbear_kanban.config_loader import load_config

if TYPE_CHECKING:
    from owlbear_kanban.models import BoardConfig, Task
from owlbear_kanban.task_io import (
    _make_yaml,
    make_task_filename,
    validate_path_containment,
)
from owlbear_kanban.task_io import read_task as _task_io_read_task

# ---------------------------------------------------------------------------
# Canonical frontmatter field order per §2.3
# ---------------------------------------------------------------------------

_CANONICAL_FIELDS: list[str] = [
    "id",
    "title",
    "status",
    "priority",
    "created",
    "updated",
    "tags",
    "parent",
    "depends_on",
    "blocked",
    "block_reason",
    "claimed_at",
    "archival_reason",
    "archival_refs",
]

_CANONICAL_FIELD_SET: frozenset[str] = frozenset(_CANONICAL_FIELDS)

# Timestamp fields that require explicit UTC +00:00
_TS_FIELDS: frozenset[str] = frozenset({"created", "updated", "claimed_at"})

# Matches the base part of an ISO-8601 datetime (groups: base, frac, tz)
_TS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})((?:\.\d+)?)([+-]\d{2}:\d{2}|Z)?$"
)


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class CorruptionError(Exception):
    """A task file contains a corrupt or forbidden field."""

    def __init__(self, code: str, detail: str, path: Path | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.path = path


class MigrationRequiredError(Exception):
    """The board requires migration before it can be used."""

    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_timestamp(ts: str | None) -> str | None:
    """Return *ts* with an explicit UTC +00:00 suffix when it lacks a timezone.

    Non-timestamp strings and ``None`` are returned unchanged.
    Go-style extended nanosecond timestamps that already carry a timezone
    offset are also returned unchanged.
    """
    if ts is None:
        return None
    m = _TS_RE.match(ts.strip())
    if not m:
        return ts
    base, frac, tz = m.groups()
    if tz:
        return ts  # already has timezone info
    return f"{base}{frac}+00:00"


# ---------------------------------------------------------------------------
# Public I/O
# ---------------------------------------------------------------------------


def read_task(path: Path) -> Task:
    """Parse a task file into a :class:`Task`, silently stripping ``claimed_by``.

    Archive files containing the legacy ``claimed_by`` field are read without
    raising :class:`CorruptionError`; the field is stripped from the returned
    model (AC-C48).

    Args:
        path: Path to the task ``.md`` file.

    Returns:
        Populated :class:`Task` with ``claimed_by`` set to ``None``.
    """
    task = _task_io_read_task(path)
    task.claimed_by = None
    return task


def write_task(task: Task, kanban_dir: Path) -> Path:
    """Serialise *task* to the ``tasks/`` directory of *kanban_dir*.

    Frontmatter fields are written in canonical §2.3 order (AC-C13).
    Timestamps are normalised to explicit UTC ``+00:00`` (AC-C15).
    The legacy ``claimed_by`` field is never written to disk.

    Args:
        task:       Task to serialise.
        kanban_dir: Root directory of the kanban board.

    Returns:
        Absolute path of the written file.
    """
    config = load_config(kanban_dir)
    tasks_dir = kanban_dir / config.tasks_dir
    filename = make_task_filename(task.id, task.title)
    path = tasks_dir / filename
    validate_path_containment(tasks_dir, path)

    data: dict[str, Any] = task.model_dump()
    data.pop("body", None)
    body: str = task.body or ""

    # Build ordered frontmatter: canonical fields first (AC-C13), then vendor extras.
    ordered: CommentedMap = CommentedMap()

    for key in _CANONICAL_FIELDS:
        if key not in data:
            continue
        val = data[key]
        if key in _TS_FIELDS and isinstance(val, str):
            val = _normalize_timestamp(val)
        ordered[key] = val

    for key, val in data.items():
        if key not in _CANONICAL_FIELD_SET and key != "claimed_by":
            ordered[key] = val

    stream = io.StringIO()
    _make_yaml().dump(ordered, stream)
    yaml_str = stream.getvalue()
    content = f"---\n{yaml_str}---\n{body}"

    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp).replace(path)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp).unlink()
        raise

    return path


# ---------------------------------------------------------------------------
# Corruption detection
# ---------------------------------------------------------------------------


def detect_corruption(path: Path, config: BoardConfig) -> CorruptionError | None:
    """Check *path* for forbidden frontmatter fields.

    The ``claimed_by`` field is forbidden in ``tasks/`` files but exempt in
    archive files (AC-C16, AC-C48).  Returns a :class:`CorruptionError`
    describing the problem, or ``None`` if the file is clean.

    Args:
        path:   Path to the task file to inspect.
        config: Loaded :class:`BoardConfig` for the board.

    Returns:
        :class:`CorruptionError` if corruption is detected, else ``None``.
    """
    archive_dir_name = Path(config.archive_dir).name
    if path.parent.name == archive_dir_name:
        return None  # Archive files exempt (AC-C48)

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    lines = content.split("\n")
    closing_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return None

    for line in lines[1:closing_idx]:
        if line.startswith("claimed_by:"):
            val = line.split(":", 1)[1].strip()
            if val and val.lower() not in ("null", "~", ""):
                return CorruptionError(
                    code="ERR_CORRUPT_MISSING_FIELD",
                    detail="forbidden field claimed_by present",
                    path=path,
                )

    return None


# ---------------------------------------------------------------------------
# Quarantine
# ---------------------------------------------------------------------------


def move_to_quarantine(task_path: Path, kanban_dir: Path) -> Path:
    """Move *task_path* to the ``quarantine/`` directory under *kanban_dir*.

    Creates ``quarantine/`` if absent (AC-C28).  Returns the new path
    ``quarantine/{original-filename}`` (AC-C29).

    Args:
        task_path:  Path to the corrupt task file.
        kanban_dir: Root directory of the kanban board.

    Returns:
        New path of the quarantined file.
    """
    quarantine_dir = kanban_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / task_path.name
    task_path.replace(dest)
    return dest
