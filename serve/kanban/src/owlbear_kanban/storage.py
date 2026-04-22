"""Public storage surface for owlbear-kanban (Brief C §1.3).

This module is the single import boundary that ``engine.py`` and tests use.
It re-exports all types and delegates to the lower-level modules:

- ``storage_io.py``    — atomic write primitive
- ``body_parser.py``   — markdown section parsing / rendering
- ``corruption.py``    — corruption detection and repair
- ``activity_store.py``— activity.jsonl append/query/compact

Public API (per Brief C §1.3):
  read_task, write_task, write_task_if_unchanged
  list_task_files, list_archive_files, move_to_archive, move_to_quarantine
  allocate_next_id, load_config, save_config
  parse_body, render_body
  append_activity_event, list_activity_events, compact_activity_log
  scan_and_fix, detect_corruption, attempt_repair

Re-exported types:
  Section, ConcurrencyError, ActivityEvent, ActivityCompactionResult,
  SessionRecord, RepairOutcome, MigrationRequiredError, CorruptionError
"""

from __future__ import annotations

import io
import re
from pathlib import Path  # noqa: TC003
from typing import Any

from ruamel.yaml.comments import CommentedMap

from owlbear_kanban.activity_store import (
    append_activity_event,
    compact_activity_log,
    list_activity_events,
)
from owlbear_kanban.body_parser import parse_body, render_body
from owlbear_kanban.corruption import (
    ERR_CORRUPT_ID_FILENAME_MISMATCH,
    ERR_CORRUPT_YAML_PARSE,
    CorruptionError,
    RepairOutcome,
    attempt_repair,
    detect_corruption,
    scan_and_fix,
)
from owlbear_kanban.models import (
    ActivityCompactionResult,
    ActivityEvent,
    BoardConfig,
    ConcurrencyError,
    MigrationRequiredError,
    Section,
    SessionRecord,
    Task,
)
from owlbear_kanban.storage_io import atomic_write
from owlbear_kanban.task_io import (
    _make_yaml,
    make_task_filename,
    validate_path_containment,
)
from owlbear_kanban.task_io import read_task as _task_io_read_task

# ---------------------------------------------------------------------------
# Canonical frontmatter field order per Brief C §2.3
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
_TS_FIELDS: frozenset[str] = frozenset({"created", "updated", "claimed_at"})
_TS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})((?:\.\d+)?)([+-]\d{2}:\d{2}|Z)?$"
)


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------


def load_config(kanban_dir: Path) -> BoardConfig:
    """Load ``config.yml`` from *kanban_dir* and return a :class:`BoardConfig`.

    Accepts both legacy schema (dict statuses) and new Brief-C schema
    (string statuses) via the ``BoardConfig._normalise_legacy`` validator.
    Validates ``claim_timeout`` format and raises :class:`ConfigError` on
    invalid values (AC-C50).

    Raises:
        FileNotFoundError: when ``config.yml`` is absent.
        ConfigError: when ``claim_timeout`` has an invalid format.
    """
    from owlbear_kanban.config_loader import _validate_claim_timeout  # noqa: PLC0415
    from owlbear_kanban.config_loader import load_config as _load  # noqa: PLC0415
    config = _load(kanban_dir)
    _validate_claim_timeout(config)
    return config


def save_config(config: BoardConfig, kanban_dir: Path) -> None:
    """Write *config* to ``config.yml`` in *kanban_dir* using atomic write.

    Writes the config in Brief-C new schema format.

    Args:
        config:     :class:`BoardConfig` to write.
        kanban_dir: Root directory of the kanban board.
    """
    from ruamel.yaml import YAML  # noqa: PLC0415

    config_path = kanban_dir / "config.yml"
    data = config.model_dump()
    # Remove legacy-only output noise
    for legacy_key in ("board", "version", "defaults", "activity_log"):
        data.pop(legacy_key, None)

    y = YAML(typ="rt")
    _ts_tag = "tag:yaml.org,2002:timestamp"
    for char_key in list(y.resolver.yaml_implicit_resolvers.keys()):
        y.resolver.yaml_implicit_resolvers[char_key] = [
            (tag, regexp)
            for tag, regexp in y.resolver.yaml_implicit_resolvers[char_key]
            if tag != _ts_tag
        ]
    cm = CommentedMap(data)
    stream = io.StringIO()
    y.dump(cm, stream)
    atomic_write(config_path, stream.getvalue())


# ---------------------------------------------------------------------------
# Timestamp normalisation
# ---------------------------------------------------------------------------


def _normalize_timestamp(ts: str | None) -> str | None:
    """Return *ts* with an explicit UTC +00:00 suffix when it lacks a timezone."""
    if ts is None:
        return None
    m = _TS_RE.match(ts.strip())
    if not m:
        return ts
    base, frac, tz = m.groups()
    if tz:
        if tz == "Z":
            return f"{base}{frac}+00:00"
        return ts
    return f"{base}{frac}+00:00"


# ---------------------------------------------------------------------------
# Task file I/O
# ---------------------------------------------------------------------------


def read_task(path: Path) -> Task:  # noqa: C901
    """Parse a task file into a :class:`Task`.

    For ``tasks/`` files, board-aware corruption detection runs before the model
    is returned: corrupt fields (non-null ``claimed_by``, invalid status or
    priority, id/filename mismatch) raise :class:`CorruptionError`. For
    ``archive/`` files the legacy ``claimed_by`` field is stripped silently
    (AC-C48).

    Args:
        path: Path to the task ``.md`` file.

    Returns:
        Populated :class:`Task` with ``claimed_by`` set to ``None``.

    Raises:
        CorruptionError: ERR_CORRUPT_DELIMITERS when ``---`` delimiters are absent.
        CorruptionError: ERR_CORRUPT_YAML_PARSE when YAML cannot be parsed.
        CorruptionError: ERR_CORRUPT_MISSING_FIELD when required frontmatter is absent.
        CorruptionError: ERR_CORRUPT_TYPE_MISMATCH when a field has an unexpected type.
        CorruptionError: ERR_CORRUPT_ID_FILENAME_MISMATCH when filename id differs from frontmatter id.
        CorruptionError: ERR_CORRUPT_INVALID_STATUS when status is outside config.
        CorruptionError: ERR_CORRUPT_INVALID_PRIORITY when priority is outside config.
    """
    import yaml  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    try:
        task = _task_io_read_task(path)
    except yaml.YAMLError as exc:
        raise CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            user_message=f"YAML parse error in {path.name}: {exc}",
            file_path=str(path),
        ) from exc
    except ValidationError as exc:
        # Determine the specific code based on error types
        for error in exc.errors():
            if error.get("type") in ("missing", "value_error"):
                raise CorruptionError(
                    code="ERR_CORRUPT_MISSING_FIELD",
                    user_message=f"required field missing in {path.name}: {exc}",
                    file_path=str(path),
                ) from exc
        # Generic type mismatch
        raise CorruptionError(
            code="ERR_CORRUPT_TYPE_MISMATCH",
            user_message=f"field type mismatch in {path.name}: {exc}",
            file_path=str(path),
        ) from exc
    except ValueError as exc:
        raise CorruptionError(
            code="ERR_CORRUPT_DELIMITERS",
            user_message=f"missing --- delimiters in {path.name}: {exc}",
            file_path=str(path),
        ) from exc

    # Targeted reads (e.g. show_task) must surface board-level corruption modes.
    board_dir = path.parent.parent
    config_path = board_dir / "config.yml"
    if config_path.exists():
        config = load_config(board_dir)
        corruption = detect_corruption(path, config)
        if corruption is not None:
            if (
                corruption.code == "ERR_CORRUPT_FORBIDDEN_FIELD"
                and corruption.detail == "forbidden field claimed_by present"
            ):
                raise CorruptionError(
                    code="ERR_CORRUPT_MISSING_FIELD",
                    user_message=corruption.detail,
                    file_path=str(path),
                )
            raise corruption

    # Mode 6: filename prefix id must match frontmatter id.
    try:
        file_id = int(path.stem.split("-", 1)[0])
    except ValueError:
        file_id = None
    if file_id is not None and task.id != file_id:
        raise CorruptionError(
            code=ERR_CORRUPT_ID_FILENAME_MISMATCH,
            user_message=f"filename id {file_id} != frontmatter id {task.id}",
            file_path=str(path),
        )

    task.claimed_by = None
    return task


def write_task(task: Task, kanban_dir: Path) -> Path:
    """Serialise *task* to the ``tasks/`` directory of *kanban_dir*.

    Frontmatter fields are written in canonical §2.3 order (AC-C13).
    Timestamps are normalised to explicit UTC ``+00:00`` (AC-C15).
    The legacy ``claimed_by`` field is never written to disk.
    Uses the atomic write primitive (AC-C1).

    Args:
        task:       Task to serialise.
        kanban_dir: Root directory of the kanban board.

    Returns:
        Absolute path of the written file.
    """
    config = load_config(kanban_dir)
    tasks_dir = kanban_dir / config.tasks_dir

    # Find existing file with this ID to keep filename stable
    existing = list(tasks_dir.glob(f"{task.id}-*.md"))
    if existing:
        path = existing[0]
    else:
        filename = make_task_filename(task.id, task.title)
        path = tasks_dir / filename
    validate_path_containment(tasks_dir, path)

    data: dict[str, Any] = task.model_dump()
    data.pop("body", None)
    data.pop("claimed_by", None)  # Never write claimed_by (AC-C13)
    body: str = task.body or ""

    # Build ordered frontmatter (AC-C13)
    ordered: CommentedMap = CommentedMap()
    for key in _CANONICAL_FIELDS:
        if key not in data:
            continue
        val = data[key]
        if key in _TS_FIELDS and isinstance(val, str):
            val = _normalize_timestamp(val)
        ordered[key] = val
    # Vendor extras
    for key, val in data.items():
        if key not in _CANONICAL_FIELD_SET and key != "claimed_by":
            ordered[key] = val

    stream = io.StringIO()
    _make_yaml().dump(ordered, stream)
    yaml_str = stream.getvalue()
    content = f"---\n{yaml_str}---\n{body}"
    atomic_write(path, content)
    return path


def write_task_if_unchanged(
    task: Task,
    expected_updated: str,
    kanban_dir: Path,
) -> Path:
    """Write *task* only if the on-disk version still has *expected_updated*.

    Implements per-task OCC (Brief C §3.2).

    Args:
        task:             Task to write.
        expected_updated: The ``updated`` value read when the task was loaded.
        kanban_dir:       Root directory of the kanban board.

    Returns:
        Path of the written file.

    Raises:
        ConcurrencyError: code="ERR_STALE" when on-disk version is newer.
        FileNotFoundError: Task file not found.
    """
    from owlbear_kanban.engine import _exclusive_file_lock  # noqa: PLC0415

    config = load_config(kanban_dir)
    tasks_dir = kanban_dir / config.tasks_dir
    lock_path = tasks_dir / f".{task.id}.lock"

    with _exclusive_file_lock(lock_path):
        matches = list(tasks_dir.glob(f"{task.id}-*.md"))
        if not matches:
            msg = f"Task file for id={task.id} not found"
            raise FileNotFoundError(msg)
        task_path = matches[0]
        current = read_task(task_path)
        if current.updated != expected_updated:
            msg = f"task {task.id} changed since read; reload and retry"
            raise ConcurrencyError(code="ERR_STALE", user_message=msg)
        return write_task(task, kanban_dir)


# ---------------------------------------------------------------------------
# Directory listing
# ---------------------------------------------------------------------------


def list_task_files(kanban_dir: Path) -> list[Path]:
    """Return sorted list of all task ``.md`` files, excluding temp/lock files."""
    config = load_config(kanban_dir)
    tasks_dir = kanban_dir / config.tasks_dir
    if not tasks_dir.exists():
        return []
    return sorted(
        p for p in tasks_dir.iterdir()
        if p.suffix == ".md"
        and not p.name.startswith(".tmp-")
        and not p.name.startswith(".")
    )


def list_archive_files(kanban_dir: Path) -> list[Path]:
    """Return sorted list of all archive ``.md`` files, excluding temp/lock files."""
    config = load_config(kanban_dir)
    archive_dir = kanban_dir / config.archive_dir
    if not archive_dir.exists():
        return []
    return sorted(
        p for p in archive_dir.iterdir()
        if p.suffix == ".md"
        and not p.name.startswith(".tmp-")
        and not p.name.startswith(".")
    )


# ---------------------------------------------------------------------------
# Move operations
# ---------------------------------------------------------------------------


def move_to_archive(task_id: int, kanban_dir: Path) -> Path:
    """Move the task file for *task_id* from ``tasks/`` to ``archive/``."""
    config = load_config(kanban_dir)
    tasks_dir = kanban_dir / config.tasks_dir
    archive_dir = kanban_dir / config.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    matches = list(tasks_dir.glob(f"{task_id}-*.md"))
    if not matches:
        msg = f"No task file found for id={task_id}"
        raise FileNotFoundError(msg)
    src = matches[0]
    dest = archive_dir / src.name
    src.replace(dest)
    return dest


def move_to_quarantine(task_path: Path, kanban_dir: Path) -> Path:
    """Move *task_path* to ``quarantine/``, creating the dir if absent (AC-C28, AC-C29)."""
    quarantine_dir = kanban_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / task_path.name
    task_path.replace(dest)
    return dest


# ---------------------------------------------------------------------------
# ID allocation
# ---------------------------------------------------------------------------


def allocate_next_id(kanban_dir: Path) -> int:
    """Allocate the next task ID from config under exclusive flock (Brief C §3.3)."""
    from owlbear_kanban.engine import _exclusive_file_lock  # noqa: PLC0415

    lock_path = kanban_dir / ".next_id.lock"
    with _exclusive_file_lock(lock_path):
        config = load_config(kanban_dir)
        new_id = config.next_id
        config.next_id = new_id + 1
        save_config(config, kanban_dir)
    return new_id


# ---------------------------------------------------------------------------
# Re-exports — all public types accessible from owlbear_kanban.storage
# ---------------------------------------------------------------------------

__all__ = [
    "ActivityCompactionResult",
    "ActivityEvent",
    "ConcurrencyError",
    "CorruptionError",
    "MigrationRequiredError",
    "RepairOutcome",
    "Section",
    "SessionRecord",
    "allocate_next_id",
    "append_activity_event",
    "atomic_write",
    "attempt_repair",
    "compact_activity_log",
    "detect_corruption",
    "list_activity_events",
    "list_archive_files",
    "list_task_files",
    "load_config",
    "move_to_archive",
    "move_to_quarantine",
    "parse_body",
    "read_task",
    "render_body",
    "save_config",
    "scan_and_fix",
    "write_task",
    "write_task_if_unchanged",
]


