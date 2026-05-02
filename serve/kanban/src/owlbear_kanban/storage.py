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
    allocate_next_id, save_config
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
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap

if TYPE_CHECKING:
    from ruamel.yaml import YAML

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

# YAML timestamp/bool tags used to preserve frontmatter fidelity.
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_BOOL_TAG = "tag:yaml.org,2002:bool"


class YAML12SafeLoader(yaml.SafeLoader):
    """PyYAML SafeLoader tuned for task frontmatter parsing."""


YAML12SafeLoader.yaml_implicit_resolvers = {
    k: [(tag, regexp) for tag, regexp in v if tag not in (_TIMESTAMP_TAG, _BOOL_TAG)]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
YAML12SafeLoader.add_implicit_resolver(
    _BOOL_TAG,
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)

_WINDOWS_RESERVED: frozenset[str] = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)]
)


def _make_yaml() -> YAML:
    """Return a round-trip ruamel YAML instance with timestamp resolver disabled."""
    from owlbear_kanban.yaml_rt import make_yaml  # noqa: PLC0415

    return make_yaml()


def generate_slug(title: str) -> str:
    """Return a filesystem-safe slug derived from *title*."""
    if not title:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:80]
    if slug in _WINDOWS_RESERVED:
        msg = f"Invalid title: '{slug}' is a Windows reserved filename"
        raise ValueError(msg)
    return slug


def make_task_filename(task_id: int, title: str) -> str:
    """Return canonical task filename ``{id}-{slug}.md``."""
    return f"{task_id}-{generate_slug(title)}.md"


def validate_path_containment(tasks_dir: Path, path: Path) -> None:
    """Raise if *path* is not safely contained within *tasks_dir*."""
    if "\x00" in str(path):
        msg = "Path contains null byte"
        raise ValueError(msg)

    resolved_dir = tasks_dir.resolve()
    resolved_path = path.resolve()

    if resolved_path == resolved_dir:
        msg = f"Path must be a file inside tasks_dir, not tasks_dir itself: {path}"
        raise ValueError(msg)

    try:
        resolved_path.relative_to(resolved_dir)
    except ValueError:
        msg = f"Path is outside tasks_dir '{tasks_dir}': {path}"
        raise PermissionError(msg) from None


def _parse_task_file(path: Path) -> Task:
    """Parse a markdown task file into a validated Task model."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")

    if not content.startswith("---"):
        msg = f"Task file has no YAML frontmatter (missing opening '---'): {path}"
        raise ValueError(msg)

    lines = content.split("\n")
    closing_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break
    if closing_idx is None:
        msg = f"Task file has no closing '---' frontmatter delimiter: {path}"
        raise ValueError(msg)

    frontmatter_str = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])
    data: dict[str, Any] = yaml.load(frontmatter_str, Loader=YAML12SafeLoader) or {}  # noqa: S506
    data["body"] = body
    return Task.model_validate(data)


def _validation_to_corruption(path: Path, exc: ValidationError) -> CorruptionError:
    """Map pydantic validation errors to corruption mode codes."""
    code = "ERR_CORRUPT_TYPE_MISMATCH"
    for error in exc.errors():
        if error.get("type") in ("missing", "value_error"):
            code = "ERR_CORRUPT_MISSING_FIELD"
            break
    detail = (
        "required field missing"
        if code == "ERR_CORRUPT_MISSING_FIELD"
        else "field type mismatch"
    )
    return CorruptionError(
        code=code,
        user_message=f"{detail} in {path.name}: {exc}",
        file_path=str(path),
    )


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
_CONFIG_WRITE_EXCLUDE: frozenset[str] = frozenset({"board", "version"})
_TS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})((?:\.\d+)?)([+-]\d{2}:\d{2}|Z)?$"
)


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------


def save_config(config: BoardConfig, kanban_dir: Path) -> None:
    """Write *config* to ``config.yml`` in *kanban_dir* using atomic write.

    Writes the config in grouped schema format (``schema: grouped``) with
    nested ``paths``, ``pipeline``, ``agents``, and ``policy`` sub-sections.

    Args:
        config:     :class:`BoardConfig` to write.
        kanban_dir: Root directory of the kanban board.
    """
    from owlbear_kanban.yaml_rt import make_yaml  # noqa: PLC0415

    config_path = kanban_dir / "config.yml"
    data = {
        "schema": "grouped",
        "statuses": config.statuses,
        "priorities": config.priorities,
        "next_id": config.next_id,
        "activity_log": config.activity_log,
        "paths": {
            "tasks_dir": config.paths.tasks_dir,
            "archive_dir": config.paths.archive_dir,
        },
        "pipeline": {
            "entry_status": config.pipeline.entry_status,
            "terminal_status": config.pipeline.terminal_status,
            "wave_size": config.pipeline.wave_size,
            "claim_timeout": config.pipeline.claim_timeout,
            "default_priority": config.pipeline.default_priority,
        },
        "agents": {
            "agent_map": config.agents.agent_map,
            "agent_types": config.agents.agent_types,
            "agent_compatibility": config.agents.agent_compatibility,
        },
        "policy": {
            "non_impl_tags": config.policy.non_impl_tags,
            "archival_reasons": config.policy.archival_reasons,
            "status_predicates": config.policy.status_predicates,
        },
    }

    if config.model_extra:
        for key, value in config.model_extra.items():
            if key not in data:
                data[key] = value

    data = _yaml_safe_value(data)

    y = make_yaml(explicit_start=True)
    cm = CommentedMap(data)
    stream = io.StringIO()
    y.dump(cm, stream)
    atomic_write(config_path, stream.getvalue())


def _yaml_safe_value(value: object) -> object:
    """Recursively convert non-YAML-safe values emitted by model_dump()."""
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, dict):
        return {k: _yaml_safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_yaml_safe_value(v) for v in value]
    if isinstance(value, tuple):
        return [_yaml_safe_value(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Timestamp normalisation
# ---------------------------------------------------------------------------


def _normalize_timestamp(ts: str | None) -> str | None:
    """Return *ts* with an explicit UTC +00:00 suffix when it lacks a timezone."""
    if ts is None:
        return None
    normalized = ts.strip()
    m = _TS_RE.match(normalized)
    if not m:
        return ts
    base, frac, tz = m.groups()
    if tz:
        if tz == "Z":
            return f"{base}{frac}+00:00"
        return datetime.fromisoformat(normalized).astimezone(UTC).isoformat()
    return f"{base}{frac}+00:00"


# ---------------------------------------------------------------------------
# Task file I/O
# ---------------------------------------------------------------------------


def read_task(path: Path, *, config: BoardConfig | None = None) -> Task:
    """Parse a task file into a :class:`Task`.

    For ``tasks/`` files, board-aware corruption detection runs before the model
    is returned: corrupt fields (non-null ``claimed_by``, invalid status or
    priority, id/filename mismatch) raise :class:`CorruptionError`. For
    ``archive/`` files the legacy ``claimed_by`` field is stripped silently
    (AC-C48).

    Args:
        path: Path to the task ``.md`` file.
        config: Optional pre-resolved board config used for corruption detection.
            When provided, corruption detection runs without reading ``config.yml``.

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
    try:
        task = _parse_task_file(path)
    except yaml.YAMLError as exc:
        raise CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            user_message=f"YAML parse error in {path.name}: {exc}",
            file_path=str(path),
        ) from exc
    except ValidationError as exc:
        raise _validation_to_corruption(path, exc) from exc
    except ValueError as exc:
        raise CorruptionError(
            code="ERR_CORRUPT_DELIMITERS",
            user_message=f"missing --- delimiters in {path.name}: {exc}",
            file_path=str(path),
        ) from exc

    # Targeted reads (e.g. show_task) must surface board-level corruption modes.
    board_dir = path.parent.parent
    if config is not None:
        corruption = detect_corruption(path, config)
        if corruption is not None:
            raise corruption
    else:
        config_path = board_dir / "config.yml"
        if config_path.exists():
            from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

            loaded_config = _load_config(board_dir)
            corruption = detect_corruption(path, loaded_config)
            if corruption is not None:
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

    return task


def write_task(task: Task, kanban_dir: Path, *, target_dir: Path | None = None) -> Path:
    """Serialise *task* to *target_dir* (or ``tasks/``) under *kanban_dir*.

    Frontmatter fields are written in canonical §2.3 order (AC-C13).
    Timestamps are normalised to explicit UTC ``+00:00`` (AC-C15).
    The legacy ``claimed_by`` field is never written to disk.
    Uses the atomic write primitive (AC-C1).

    Args:
        task:       Task to serialise.
        kanban_dir: Root directory of the kanban board.
        target_dir: Optional destination directory for the task file.

    Returns:
        Absolute path of the written file.
    """
    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

    config = _load_config(kanban_dir)
    tasks_dir = target_dir or (kanban_dir / config.paths.tasks_dir)

    # Find existing file with this ID to keep filename stable
    existing = list(tasks_dir.glob(f"{task.id}-*.md"))
    if existing:
        path = existing[0]
    else:
        filename = make_task_filename(task.id, task.title)
        path = tasks_dir / filename
    validate_path_containment(kanban_dir, tasks_dir)
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
    # Vendor extras (AC-C15 applies to all timestamp-looking values).
    for key, val in data.items():
        if key not in _CANONICAL_FIELD_SET and key != "claimed_by":
            normalized_val = _normalize_timestamp(val) if isinstance(val, str) else val
            ordered[key] = normalized_val

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
        FileNotFoundError: Task file not found in tasks/ or archive/.
    """
    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415
    from owlbear_kanban.engine import _exclusive_file_lock  # noqa: PLC0415

    config = _load_config(kanban_dir)
    tasks_dir = kanban_dir / config.paths.tasks_dir
    archive_dir = kanban_dir / config.paths.archive_dir
    lock_path = tasks_dir / f".{task.id}.lock"
    archive_lock_path = archive_dir / f".{task.id}.lock"

    with _exclusive_file_lock(lock_path), _exclusive_file_lock(archive_lock_path):
        matches = list(tasks_dir.glob(f"{task.id}-*.md"))
        if not matches:
            matches = list(archive_dir.glob(f"{task.id}-*.md"))
        if not matches:
            msg = f"Task file for id={task.id} not found"
            raise FileNotFoundError(msg)
        task_path = matches[0]
        current = read_task(task_path)
        if current.updated != expected_updated:
            msg = f"task {task.id} changed since read; reload and retry"
            raise ConcurrencyError(code="ERR_STALE", user_message=msg)
        return write_task(task, kanban_dir, target_dir=task_path.parent)


# ---------------------------------------------------------------------------
# Directory listing
# ---------------------------------------------------------------------------


def list_task_files(kanban_dir: Path) -> list[Path]:
    """Return sorted list of all task ``.md`` files, excluding temp/lock files."""
    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

    config = _load_config(kanban_dir)
    tasks_dir = kanban_dir / config.paths.tasks_dir
    if not tasks_dir.exists():
        return []
    return sorted(
        p
        for p in tasks_dir.iterdir()
        if p.is_file()
        and p.suffix == ".md"
        and not p.name.startswith(".tmp-")
        and not p.name.startswith(".")
    )


def list_archive_files(kanban_dir: Path) -> list[Path]:
    """Return sorted list of all archive ``.md`` files, excluding temp/lock files."""
    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

    config = _load_config(kanban_dir)
    archive_dir = kanban_dir / config.paths.archive_dir
    if not archive_dir.exists():
        return []
    return sorted(
        p
        for p in archive_dir.iterdir()
        if p.is_file()
        and p.suffix == ".md"
        and not p.name.startswith(".tmp-")
        and not p.name.startswith(".")
    )


# ---------------------------------------------------------------------------
# Move operations
# ---------------------------------------------------------------------------


def move_to_archive(task_id: int, kanban_dir: Path) -> Path:
    """Move the task file for *task_id* from ``tasks/`` to ``archive/``."""
    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415
    from owlbear_kanban.engine import _exclusive_file_lock  # noqa: PLC0415

    config = _load_config(kanban_dir)
    tasks_dir = kanban_dir / config.paths.tasks_dir
    archive_dir = kanban_dir / config.paths.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    task_lock_path = tasks_dir / f".{task_id}.lock"
    archive_lock_path = archive_dir / f".{task_id}.lock"

    # Keep lock order consistent with write_task_if_unchanged to avoid deadlocks.
    with _exclusive_file_lock(task_lock_path), _exclusive_file_lock(archive_lock_path):
        matches = list(tasks_dir.glob(f"{task_id}-*.md"))
        if not matches:
            msg = f"No task file found for id={task_id}"
            raise FileNotFoundError(msg)
        src = matches[0]
        dest = archive_dir / src.name
        src.replace(dest)
        return dest


def move_to_quarantine(task_path: Path, kanban_dir: Path) -> Path:
    """Move *task_path* to ``quarantine/``, creating the dir if absent (AC-C28, AC-C29).

    Lock files (hidden ``.lock`` files) are skipped: the function returns *task_path*
    unchanged without moving or creating any quarantine directory entry.

    Raises:
        PermissionError: when *task_path* is outside *kanban_dir*.
    """
    if task_path.name.startswith(".") and task_path.name.endswith(".lock"):
        return task_path

    validate_path_containment(kanban_dir, task_path)

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
        from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

        config = _load_config(kanban_dir)
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
    "make_task_filename",
    "move_to_archive",
    "move_to_quarantine",
    "parse_body",
    "read_task",
    "render_body",
    "save_config",
    "scan_and_fix",
    "validate_path_containment",
    "write_task",
    "write_task_if_unchanged",
]
