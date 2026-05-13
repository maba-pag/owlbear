"""Public storage persistence surface for owlbear-kanban (Brief C §1.3).

This module provides task/config persistence helpers and selected shared types.
Parsing, corruption scanning/repair, and activity log APIs live in their source
modules and should be imported directly by consumers.

Lower-level modules used by this surface:

- ``storage_io.py``    — atomic write primitive
- ``body_parser.py``   — markdown section parsing / rendering
- ``corruption.py``    — corruption detection and repair
- ``activity_store.py``— activity.jsonl append/query/compact

Public API (per Brief C §1.3):
  read_task, write_task, write_task_if_unchanged
  list_task_files, list_archive_files, move_to_archive, move_to_quarantine
    allocate_next_id, save_config

Re-exported types:
    Section, ConcurrencyError, ActivityEvent, ActivityCompactionResult,
    SessionRecord, MigrationRequiredError
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
from ruamel.yaml.scalarstring import PlainScalarString

if TYPE_CHECKING:
    from collections.abc import Callable

    from ruamel.yaml import YAML

from owlbear_kanban._locking import _exclusive_file_lock
from owlbear_kanban._naming import (
    generate_slug,  # noqa: F401
    make_task_filename,
    move_to_quarantine,
    validate_path_containment,
)
from owlbear_kanban.corruption import (
    ERR_CORRUPT_ID_FILENAME_MISMATCH,
    ERR_CORRUPT_YAML_PARSE,
    CorruptionError,
    detect_corruption,
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


def _make_yaml() -> YAML:
    """Return a round-trip ruamel YAML instance with timestamp resolver disabled."""
    from owlbear_kanban.yaml_rt import make_yaml  # noqa: PLC0415

    return make_yaml()


def _parse_task_file(path: Path) -> dict[str, Any]:
    """Parse a markdown task file into a frontmatter/body dictionary."""
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
    return data


def _is_archive_path(path: Path, board_dir: Path, config: BoardConfig | None) -> bool:
    """Return True when *path* points to the board's archive directory."""
    if config is not None:
        return path.parent == (board_dir / config.paths.archive_dir)
    return path.parent.name == "archive"


def _resolve_board_config(
    path: Path, config: BoardConfig | None
) -> tuple[Path, BoardConfig | None]:
    """Resolve board root and optional config for a task file path."""
    board_dir = path.parent.parent
    if config is not None:
        return board_dir, config
    config_path = board_dir / "config.yml"
    if not config_path.exists():
        return board_dir, None

    from owlbear_kanban.config_loader import load_config as _load_config  # noqa: PLC0415

    return board_dir, _load_config(board_dir)


def _as_plain_timestamp_scalar(value: str) -> str | PlainScalarString:
    """Return timestamp-like strings as plain scalars to avoid quoted YAML output."""
    normalized = _normalize_timestamp(value)
    if normalized is None:
        return value
    if _TS_RE.match(normalized.strip()):
        return PlainScalarString(normalized)
    return normalized


def _unquote_timestamp_scalars(yaml_str: str) -> str:
    """Remove single quotes from timestamp scalar lines in frontmatter YAML."""
    out_lines: list[str] = []
    for line in yaml_str.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        m = re.match(r"^([^:\n]+): '(.*)'$", stripped)
        if m is None:
            out_lines.append(line)
            continue
        key, value = m.groups()
        normalized = _normalize_timestamp(value)
        if normalized is not None and _TS_RE.match(normalized.strip()):
            out_lines.append(f"{key}: {normalized}\n")
            continue
        out_lines.append(line)
    return "".join(out_lines)


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

    Persists only ``next_id``; topology values are product constants.

    Args:
        config:     :class:`BoardConfig` to write.
        kanban_dir: Root directory of the kanban board.
    """
    from owlbear_kanban.yaml_rt import make_yaml  # noqa: PLC0415

    config_path = kanban_dir / "config.yml"
    data = {"next_id": config.next_id}

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
    """Normalise *ts* to an explicit UTC ``+00:00`` form.

    - No timezone: appends ``+00:00``.
    - ``Z`` suffix: replaced with ``+00:00``.
    - Non-UTC offset (e.g. ``+02:00``): converted to UTC via :func:`datetime.astimezone`.
    - Non-timestamp strings: returned unchanged.
    """
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
    board_dir, loaded_config = _resolve_board_config(path, config)

    try:
        data = _parse_task_file(path)
        if _is_archive_path(path, board_dir, loaded_config):
            data.pop("claimed_by", None)
        task = Task.model_validate(data)
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
    if loaded_config is not None:
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
            val = _as_plain_timestamp_scalar(val)
        ordered[key] = val
    # Vendor extras (AC-C15 applies to all timestamp-looking values).
    for key, val in data.items():
        if key not in _CANONICAL_FIELD_SET and key != "claimed_by":
            normalized_val = (
                _as_plain_timestamp_scalar(val) if isinstance(val, str) else val
            )
            ordered[key] = normalized_val

    stream = io.StringIO()
    _make_yaml().dump(ordered, stream)
    yaml_str = _unquote_timestamp_scalars(stream.getvalue())
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


# ---------------------------------------------------------------------------
# ID allocation
# ---------------------------------------------------------------------------


def allocate_next_id(
    kanban_dir: Path,
    *,
    write_task_fn: Callable[[int], None] | None = None,
) -> int:
    """Allocate the next task ID under the shared create lock.

    When ``write_task_fn`` is provided, allocation is scan-based (active+archive
    max prefix + 1) and the callback is executed while the lock is still held so
    callers can keep scan+write in one critical section.

    When ``write_task_fn`` is ``None``, this function still uses scan-based
    allocation and persists the last issued id in ``.next_id.lock`` so repeated
    allocation-only calls remain distinct under concurrency.
    """
    lock_path = kanban_dir / ".next_id.lock"
    with _exclusive_file_lock(lock_path):
        max_id = 0
        for path in [*list_task_files(kanban_dir), *list_archive_files(kanban_dir)]:
            try:
                file_id = int(path.stem.split("-", 1)[0])
            except ValueError:
                continue
            max_id = max(max_id, file_id)

        last_allocated = 0
        try:
            text = lock_path.read_text(encoding="utf-8").strip()
            if text:
                last_allocated = int(text)
        except (OSError, ValueError):
            last_allocated = 0

        if write_task_fn is not None:
            new_id = max_id + 1
            write_task_fn(new_id)
            return new_id

        new_id = max(max_id, last_allocated) + 1
        lock_path.write_text(f"{new_id}\n", encoding="utf-8")
        return new_id


# ---------------------------------------------------------------------------
# Re-exports — selected public symbols accessible from owlbear_kanban.storage
# ---------------------------------------------------------------------------

__all__ = [
    "ActivityCompactionResult",
    "ActivityEvent",
    "ConcurrencyError",
    "MigrationRequiredError",
    "Section",
    "SessionRecord",
    "allocate_next_id",
    "atomic_write",
    "list_archive_files",
    "list_task_files",
    "make_task_filename",
    "move_to_archive",
    "move_to_quarantine",
    "read_task",
    "save_config",
    "validate_path_containment",
    "write_task",
    "write_task_if_unchanged",
]
