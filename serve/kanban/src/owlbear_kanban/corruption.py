"""Corruption detection and repair for kanban task files (Brief C §4).

Defines the 10 ERR_CORRUPT_* codes, CorruptionError, RepairOutcome,
detect_corruption(), attempt_repair(), and scan_and_fix().
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from owlbear_kanban._naming import (
    make_task_filename,
    move_to_quarantine,
)
from owlbear_kanban.errors import KanbanError
from owlbear_kanban.models import DeterministicRepairResult, RepairOutcome, TaskHealthFinding, TaskHealthResult
from owlbear_kanban.storage_io import atomic_write
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

if TYPE_CHECKING:
    from owlbear_kanban.models import BoardConfig

# ---------------------------------------------------------------------------
# The 9 ERR_CORRUPT_* codes (Brief C §4.1)
# ---------------------------------------------------------------------------


def _normalize_code(code: str | type[object]) -> str:
    """Return the canonical string code name from str/class input."""
    if isinstance(code, str):
        return code
    if isinstance(code, type):
        return code.__name__
    return str(code)


# Required frontmatter fields
_REQUIRED_FIELDS = ("id", "title", "status", "priority", "created", "updated")

# Fields with safe defaults for auto-fix (mode 3)
_SAFE_DEFAULTS: dict[str, object] = {
    "priority": None,  # → config.priorities[0]
    "tags": [],
    "depends_on": [],
    "blocked": False,
    "block_reason": None,
    "claimed_at": None,
    "archival_reason": None,
    "archival_refs": [],
    "parent": None,
}


def _configured_statuses(_config: BoardConfig) -> list[str]:
    """Return canonical product statuses (topology is not board-configurable)."""
    return list(PRODUCT_TOPOLOGY.statuses)


def _configured_priorities(_config: BoardConfig) -> list[str]:
    """Return canonical product priorities (topology is not board-configurable)."""
    return list(PRODUCT_TOPOLOGY.priorities)


class CorruptionError(KanbanError):
    """Raised when storage detects unrepairable on-disk state.

    Carries one of the 10 ERR_CORRUPT_* codes from §4.1.
    Accepts both positional ``detail`` and keyword ``user_message`` to satisfy
    the Brief C AC-C21 constructor contract.
    """

    def __init__(
        self,
        code: str | type[object],
        detail: str | None = None,
        path: Path | None = None,
        user_message: str | None = None,
        file_path: str | None = None,
    ) -> None:
        code_name = _normalize_code(code)
        msg = user_message or detail or code_name
        super().__init__(code_name, msg)
        self.detail = detail or user_message or code_name
        self.path = path
        self.file_path = file_path or (str(path) if path else None)


class DuplicateClass(StrEnum):
    """Complete-set duplicate classification from the repair matrix."""

    ARCHIVED_IDENTICAL = "a"
    SAME_DIRECTORY_IDENTICAL = "b"
    SAME_DIRECTORY_LARGEST_BODY = "c"
    TIED_LARGEST_BODY = "d"
    DIFFERENT_FRONTMATTER = "e"
    NON_ARCHIVED_CROSS_DIRECTORY_IDENTICAL = "f"
    CROSS_DIRECTORY_DIFFERENT = "g"
    HETEROGENEOUS = "h"


@dataclass(frozen=True)
class _DuplicateRecord:
    path: Path
    frontmatter: dict
    body: str

    @property
    def normalized_frontmatter(self) -> tuple[tuple[str, object], ...]:
        return _normalized_value(self.frontmatter)

    @property
    def normalized_body(self) -> str:
        return _normalize_body(self.body)


def _normalized_value(value: object) -> object:
    """Return a stable, representation-independent value for comparisons."""
    if isinstance(value, dict):
        return tuple(sorted((str(key), _normalized_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_normalized_value(item) for item in value)
    return value


def _normalize_body(body: str) -> str:
    """Normalize line endings and representation-only trailing whitespace."""
    return "\n".join(line.rstrip() for line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n")).rstrip("\n")


def _body_line_count(body: str) -> int:
    normalized = _normalize_body(body)
    return 0 if not normalized else len(normalized.split("\n"))


def _semantically_equal(left: _DuplicateRecord, right: _DuplicateRecord) -> bool:
    return left.normalized_frontmatter == right.normalized_frontmatter and left.normalized_body == right.normalized_body


def _generated_task_name(path: Path, record: _DuplicateRecord) -> bool:
    return path.name == make_task_filename(record.frontmatter["id"], record.frontmatter.get("title", "task"))


def _classify_duplicate_set(records: list[_DuplicateRecord], tasks_dir: Path) -> DuplicateClass:
    """Classify a complete ID set, applying predicates to every member."""
    minimum_duplicate_count = 2
    if len(records) < minimum_duplicate_count:
        raise ValueError

    same_frontmatter = len({record.normalized_frontmatter for record in records}) == 1
    identical = all(_semantically_equal(records[0], record) for record in records[1:])
    locations = {"tasks" if record.path.parent == tasks_dir else "archive" for record in records}
    same_directory = len(locations) == 1

    if not same_frontmatter:
        return DuplicateClass.DIFFERENT_FRONTMATTER
    if not same_directory:
        if identical:
            return (
                DuplicateClass.ARCHIVED_IDENTICAL
                if all(record.frontmatter.get("status") == "archived" for record in records)
                else DuplicateClass.NON_ARCHIVED_CROSS_DIRECTORY_IDENTICAL
            )
        return DuplicateClass.CROSS_DIRECTORY_DIFFERENT
    if identical:
        return DuplicateClass.SAME_DIRECTORY_IDENTICAL

    body_sizes = [_body_line_count(record.body) for record in records]
    largest = max(body_sizes)
    if body_sizes.count(largest) > 1:
        return DuplicateClass.TIED_LARGEST_BODY
    return DuplicateClass.SAME_DIRECTORY_LARGEST_BODY


def _read_duplicate_records(paths: list[Path]) -> list[_DuplicateRecord] | None:
    records: list[_DuplicateRecord] = []
    for path in paths:
        try:
            _, frontmatter, body = _read_frontmatter(path)
        except CorruptionError:
            return None
        records.append(_DuplicateRecord(path=path, frontmatter=frontmatter, body=body))
    return records


def _duplicate_outcome(
    record: _DuplicateRecord, duplicate_class: DuplicateClass, action: str, detail: str
) -> RepairOutcome:
    code = (
        ERR_CORRUPT_DUPLICATE_LOCATION.__name__
        if duplicate_class
        in {
            DuplicateClass.ARCHIVED_IDENTICAL,
            DuplicateClass.NON_ARCHIVED_CROSS_DIRECTORY_IDENTICAL,
            DuplicateClass.CROSS_DIRECTORY_DIFFERENT,
        }
        else ERR_CORRUPT_DUPLICATE_ID.__name__
    )
    return RepairOutcome(
        task_id=record.frontmatter.get("id"),
        file_path=str(record.path),
        code=code,
        action=action,
        detail=f"class {duplicate_class.value}: {detail}",
    )


def _revalidate_duplicate_set(
    paths: list[Path], expected: list[_DuplicateRecord], tasks_dir: Path
) -> list[_DuplicateRecord] | None:
    current = _read_duplicate_records(paths)
    if current is None or len(current) != len(expected):
        return None
    if any(
        path != record.path or not _semantically_equal(record, expected[index])
        for index, (path, record) in enumerate(zip(paths, current, strict=True))
    ):
        return None
    if _classify_duplicate_set(current, tasks_dir) != _classify_duplicate_set(expected, tasks_dir):
        return None
    return current


def _repair_duplicate_set(
    paths: list[Path], kanban_dir: Path, tasks_dir: Path, archive_dir: Path
) -> list[RepairOutcome]:
    records = _read_duplicate_records(paths)
    if records is None:
        return [
            RepairOutcome(
                task_id=_extract_file_id(path),
                file_path=str(path),
                code=ERR_CORRUPT_DUPLICATE_ID.__name__,
                action="unresolved",
                detail="duplicate set could not be parsed",
            )
            for path in paths
        ]

    duplicate_class = _classify_duplicate_set(records, tasks_dir)
    if duplicate_class in {
        DuplicateClass.TIED_LARGEST_BODY,
        DuplicateClass.DIFFERENT_FRONTMATTER,
        DuplicateClass.NON_ARCHIVED_CROSS_DIRECTORY_IDENTICAL,
        DuplicateClass.CROSS_DIRECTORY_DIFFERENT,
    }:
        return [
            _duplicate_outcome(
                record, duplicate_class, "unresolved", "complete duplicate set is not deterministically repairable"
            )
            for record in records
        ]
    if duplicate_class == DuplicateClass.HETEROGENEOUS:
        return [
            _duplicate_outcome(record, duplicate_class, "unresolved", "heterogeneous duplicate set")
            for record in records
        ]

    current = _revalidate_duplicate_set(paths, records, tasks_dir)
    if current is None:
        return [
            _duplicate_outcome(record, duplicate_class, "skipped", "duplicate candidate changed before repair")
            for record in records
        ]

    if duplicate_class == DuplicateClass.SAME_DIRECTORY_IDENTICAL:
        generated = [record for record in current if _generated_task_name(record.path, record)]
        survivor = generated[0] if generated else min(current, key=lambda record: str(record.path))
        removals = [record for record in current if record.path != survivor.path]
        action = "removed"
    elif duplicate_class == DuplicateClass.ARCHIVED_IDENTICAL:
        archive_records = [record for record in current if record.path.parent == archive_dir]
        survivor = min(archive_records, key=lambda record: str(record.path))
        removals = [record for record in current if record.path != survivor.path]
        action = "removed"
    else:
        survivor = max(current, key=lambda record: _body_line_count(record.body))
        removals = [record for record in current if record.path != survivor.path]
        action = "quarantined"

    outcomes = []
    for record in removals:
        try:
            if action == "quarantined":
                destination = move_to_quarantine(record.path, kanban_dir)
                outcomes.append(_duplicate_outcome(record, duplicate_class, action, f"quarantined to {destination}"))
            else:
                record.path.unlink()
                outcomes.append(_duplicate_outcome(record, duplicate_class, action, f"retained {survivor.path.name}"))
        except OSError as exc:
            outcomes.append(_duplicate_outcome(record, duplicate_class, "failed", str(exc)))
    return outcomes


class _CorruptionCodeType(type):
    """Metaclass for ERR_CORRUPT_* constants with string-name equality."""

    def __eq__(cls, other: object) -> bool:
        if isinstance(other, str):
            return cls.__name__ == other
        return super().__eq__(other)

    def __hash__(cls) -> int:
        return hash(cls.__name__)


def _make_corruption_code_type(name: str) -> type[CorruptionError]:
    """Create an ERR_CORRUPT_* exception subclass with the given name."""
    return _CorruptionCodeType(name, (CorruptionError,), {})


ERR_CORRUPT_DELIMITERS = _make_corruption_code_type("ERR_CORRUPT_DELIMITERS")
ERR_CORRUPT_DUPLICATE_ID = _make_corruption_code_type("ERR_CORRUPT_DUPLICATE_ID")
ERR_CORRUPT_MISSING_FIELD = _make_corruption_code_type("ERR_CORRUPT_MISSING_FIELD")
ERR_CORRUPT_TYPE_MISMATCH = _make_corruption_code_type("ERR_CORRUPT_TYPE_MISMATCH")
ERR_CORRUPT_YAML_PARSE = _make_corruption_code_type("ERR_CORRUPT_YAML_PARSE")
ERR_CORRUPT_ID_FILENAME_MISMATCH = _make_corruption_code_type("ERR_CORRUPT_ID_FILENAME_MISMATCH")
ERR_CORRUPT_DUPLICATE_LOCATION = _make_corruption_code_type("ERR_CORRUPT_DUPLICATE_LOCATION")
ERR_CORRUPT_INVALID_STATUS = _make_corruption_code_type("ERR_CORRUPT_INVALID_STATUS")
ERR_CORRUPT_INVALID_PRIORITY = _make_corruption_code_type("ERR_CORRUPT_INVALID_PRIORITY")
ERR_CORRUPT_ENCODING = _make_corruption_code_type("ERR_CORRUPT_ENCODING")


# _make_yaml removed — dead code; callers use YAML(typ="safe") directly
# or the shared make_yaml from yaml_rt.


def _read_frontmatter(path: Path) -> tuple[str, dict, str]:
    """Read and parse frontmatter from *path*.

    Returns:
        (full_content, frontmatter_dict, body_text) tuple.

    Raises:
        CorruptionError: ERR_CORRUPT_DELIMITERS or ERR_CORRUPT_YAML_PARSE.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CorruptionError(
            code=ERR_CORRUPT_DELIMITERS,
            detail=f"cannot read file: {exc}",
            path=path,
        ) from exc

    if not content.startswith("---"):
        raise CorruptionError(
            code=ERR_CORRUPT_DELIMITERS,
            detail="file does not start with ---",
            path=path,
        )

    lines = content.split("\n")
    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break

    if closing_idx is None:
        raise CorruptionError(
            code=ERR_CORRUPT_DELIMITERS,
            detail="no closing --- delimiter found",
            path=path,
        )

    fm_text = "\n".join(lines[1:closing_idx])
    body_text = "\n".join(lines[closing_idx + 1 :])

    try:
        y = YAML(typ="safe")
        fm = y.load(fm_text) or {}
    except Exception as exc:
        raise CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            detail=f"YAML parse error: {exc}",
            path=path,
        ) from exc

    if not isinstance(fm, dict):
        raise CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            detail="frontmatter is not a YAML mapping",
            path=path,
        )

    return content, fm, body_text


def detect_corruption(path: Path, config: BoardConfig) -> CorruptionError | None:  # noqa: C901, PLR0911, PLR0912
    """Check *path* for all 9 corruption modes.

    Returns a :class:`CorruptionError` (without raising) if corruption is
    detected, or ``None`` if the file is clean. Does not repair anything.

    Args:
        path:   Path to the task ``.md`` file.
        config: Loaded :class:`BoardConfig` for the board.

    Returns:
        :class:`CorruptionError` if corrupt, else ``None``.
    """
    # Mode 1: delimiter check
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return CorruptionError(
            code=ERR_CORRUPT_ENCODING,
            detail=f"UTF-8 decode error: {exc}",
            path=path,
        )
    except OSError:
        return None

    if not content.startswith("---"):
        return CorruptionError(
            code=ERR_CORRUPT_DELIMITERS,
            detail="file does not start with ---",
            path=path,
        )

    lines = content.split("\n")
    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return CorruptionError(
            code=ERR_CORRUPT_DELIMITERS,
            detail="no closing --- delimiter found",
            path=path,
        )

    fm_text = "\n".join(lines[1:closing_idx])

    # Mode 5: YAML parse error
    try:
        y = YAML(typ="safe")
        fm = y.load(fm_text) or {}
    except Exception:  # noqa: BLE001
        return CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            detail="YAML parse error in frontmatter",
            path=path,
        )

    if not isinstance(fm, dict):
        return CorruptionError(
            code=ERR_CORRUPT_YAML_PARSE,
            detail="frontmatter is not a YAML mapping",
            path=path,
        )

    # Mode 3: forbidden field claimed_by in tasks/ (archive files are exempt)
    is_archive = _is_archive_path(path, config)
    if not is_archive and "claimed_by" in fm:
        val = fm["claimed_by"]
        if val not in (None, ""):
            return CorruptionError(
                code=ERR_CORRUPT_MISSING_FIELD,
                detail="forbidden field claimed_by present",
                path=path,
            )

    # Mode 3: missing required field
    for field in _REQUIRED_FIELDS:
        if field not in fm:
            return CorruptionError(
                code=ERR_CORRUPT_MISSING_FIELD,
                detail=f"required field '{field}' absent",
                path=path,
            )

    # Mode 4: type mismatch
    id_val = fm.get("id")
    if id_val is not None and not isinstance(id_val, int):
        return CorruptionError(
            code=ERR_CORRUPT_TYPE_MISMATCH,
            detail=f"field 'id' has type {type(id_val).__name__}, expected int",
            path=path,
        )

    blocked_val = fm.get("blocked")
    if blocked_val is not None and not isinstance(blocked_val, bool):
        return CorruptionError(
            code=ERR_CORRUPT_TYPE_MISMATCH,
            detail=f"field 'blocked' has type {type(blocked_val).__name__}, expected bool",
            path=path,
        )

    # Mode 6: ID/filename mismatch
    file_id = _extract_file_id(path)
    if file_id is not None and isinstance(fm.get("id"), int) and fm["id"] != file_id:
        return CorruptionError(
            code=ERR_CORRUPT_ID_FILENAME_MISMATCH,
            detail=f"filename id {file_id} != frontmatter id {fm['id']}",
            path=path,
        )

    # Mode 8: invalid status
    status_val = fm.get("status")
    if status_val is not None:
        valid_statuses = set(_configured_statuses(config)) | {"archived"}
        if status_val not in valid_statuses:
            return CorruptionError(
                code=ERR_CORRUPT_INVALID_STATUS,
                detail=f"status '{status_val}' not in configured statuses",
                path=path,
            )

    # Mode 9: invalid priority
    priority_val = fm.get("priority")
    if priority_val is not None and priority_val not in _configured_priorities(config):
        return CorruptionError(
            code=ERR_CORRUPT_INVALID_PRIORITY,
            detail=f"priority '{priority_val}' not in configured priorities",
            path=path,
        )

    return None


def collect_task_health_findings(path: Path, config: BoardConfig) -> list[TaskHealthFinding]:  # noqa: C901
    """Collect every independently detectable persisted-field defect in *path*."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [TaskHealthFinding(code="TASK_READ_FAILED", detail=f"cannot read file: {exc}", path=str(path))]

    if not content.startswith("---"):
        return [TaskHealthFinding(code="ERR_CORRUPT_DELIMITERS", detail="file does not start with ---", path=str(path))]
    lines = content.split("\n")
    closing_idx = next((i for i, line in enumerate(lines[1:], start=1) if line == "---"), None)
    if closing_idx is None:
        return [
            TaskHealthFinding(code="ERR_CORRUPT_DELIMITERS", detail="no closing --- delimiter found", path=str(path))
        ]
    try:
        frontmatter = YAML(typ="safe").load("\n".join(lines[1:closing_idx])) or {}
    except Exception as exc:  # noqa: BLE001
        return [TaskHealthFinding(code="ERR_CORRUPT_YAML_PARSE", detail=f"YAML parse error: {exc}", path=str(path))]
    if not isinstance(frontmatter, dict):
        return [
            TaskHealthFinding(code="ERR_CORRUPT_YAML_PARSE", detail="frontmatter is not a YAML mapping", path=str(path))
        ]

    task_id = frontmatter.get("id") if isinstance(frontmatter.get("id"), int) else None
    findings = [
        TaskHealthFinding(
            code="ERR_CORRUPT_MISSING_FIELD",
            detail=f"required field '{field}' absent",
            path=str(path),
            task_id=task_id,
            field=field,
        )
        for field in _REQUIRED_FIELDS
        if field not in frontmatter
    ]
    if "id" in frontmatter and not isinstance(frontmatter["id"], int):
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_TYPE_MISMATCH", detail="field 'id' is not an integer", path=str(path), field="id"
            )
        )
    if "blocked" in frontmatter and not isinstance(frontmatter["blocked"], bool):
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_TYPE_MISMATCH",
                detail="field 'blocked' is not a boolean",
                path=str(path),
                task_id=task_id,
                field="blocked",
            )
        )
    file_id = _extract_file_id(path)
    if file_id is not None and isinstance(frontmatter.get("id"), int) and frontmatter["id"] != file_id:
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_ID_FILENAME_MISMATCH",
                detail=f"filename id {file_id} != frontmatter id {frontmatter['id']}",
                path=str(path),
                task_id=task_id,
                field="id",
            )
        )
    status = frontmatter.get("status")
    if status is not None and status not in set(_configured_statuses(config)) | {"archived"}:
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_INVALID_STATUS",
                detail=f"status '{status}' not in configured statuses",
                path=str(path),
                task_id=task_id,
                field="status",
            )
        )
    priority = frontmatter.get("priority")
    if priority is not None and priority not in _configured_priorities(config):
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_INVALID_PRIORITY",
                detail=f"priority '{priority}' not in configured priorities",
                path=str(path),
                task_id=task_id,
                field="priority",
            )
        )
    if not _is_archive_path(path, config) and frontmatter.get("claimed_by") not in (None, ""):
        findings.append(
            TaskHealthFinding(
                code="ERR_CORRUPT_MISSING_FIELD",
                detail="forbidden field claimed_by present",
                path=str(path),
                task_id=task_id,
                field="claimed_by",
            )
        )
    return findings


def attempt_repair(  # noqa: C901, PLR0911, PLR0912, PLR0915
    path: Path,
    code: str | type[object],
    config: BoardConfig,
) -> RepairOutcome:
    """Attempt to repair a corrupt file according to *code*.

    Auto-fixes are applied for modes 3 (safe defaults), 4 (coercions),
    6 (rename file), 9 (coerce to first priority). Non-fixable modes
    quarantine the file.

    Args:
        path:   Path to the corrupt file.
        code:   One of the 10 ERR_CORRUPT_* codes.
        config: Loaded :class:`BoardConfig`.

    Returns:
        :class:`RepairOutcome` with action='fixed', 'quarantined', or 'failed'.
    """
    try:
        task_id = _extract_file_id(path)
    except Exception:  # noqa: BLE001
        task_id = None
    code_name = _normalize_code(code)

    def _quarantine() -> RepairOutcome:
        kanban_dir = path.parent.parent
        try:
            quarantine_path = move_to_quarantine(path, kanban_dir)
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="quarantined",
                detail=f"quarantined to {quarantine_path}",
            )
        except Exception as exc:  # noqa: BLE001
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="failed",
                detail=f"quarantine failed: {exc}",
            )

    # Modes that always quarantine
    if code_name in (
        ERR_CORRUPT_DELIMITERS.__name__,
        ERR_CORRUPT_YAML_PARSE.__name__,
        ERR_CORRUPT_INVALID_STATUS.__name__,
        ERR_CORRUPT_ENCODING.__name__,
    ):
        return _quarantine()

    # Mode 7: duplicate location — archive wins
    if code_name == ERR_CORRUPT_DUPLICATE_LOCATION.__name__:
        try:
            path.unlink()
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="fixed",
                detail="tasks/ copy removed; archive/ copy retained",
            )
        except Exception as exc:  # noqa: BLE001
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="failed",
                detail=f"unlink failed: {exc}",
            )

    # Read frontmatter for fixable modes
    try:
        _, fm, body_text = _read_frontmatter(path)
    except CorruptionError as exc:
        return RepairOutcome(
            task_id=task_id,
            file_path=str(path),
            code=code_name,
            action="failed",
            detail=f"cannot read for repair: {exc.detail}",
        )

    # Mode 6: ID/filename mismatch — rename file
    if code_name == ERR_CORRUPT_ID_FILENAME_MISMATCH.__name__:
        fm_id = fm.get("id")
        if not isinstance(fm_id, int):
            return _quarantine()

        title = fm.get("title", "task")
        new_name = make_task_filename(fm_id, title)
        new_path = path.parent / new_name
        if new_path.exists():
            kanban_dir = path.parent.parent
            try:
                quarantine_path = move_to_quarantine(path, kanban_dir)
                return RepairOutcome(
                    task_id=task_id,
                    file_path=str(path),
                    code=code_name,
                    action="quarantined",
                    detail=(f"rename collision on {new_path.name}; quarantined to {quarantine_path}"),
                )
            except Exception as exc:  # noqa: BLE001
                return RepairOutcome(
                    task_id=task_id,
                    file_path=str(path),
                    code=code_name,
                    action="failed",
                    detail=f"rename collision quarantine failed: {exc}",
                )
        try:
            path.replace(new_path)
            return RepairOutcome(
                task_id=fm_id,
                file_path=str(path),
                code=code_name,
                action="fixed",
                detail=f"renamed to {new_path.name}",
            )
        except Exception as exc:  # noqa: BLE001
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="failed",
                detail=f"rename failed: {exc}",
            )

    # Mode 3: missing required field
    if code_name == ERR_CORRUPT_MISSING_FIELD.__name__:
        # Forbidden field claimed_by → quarantine (treated as migration required)
        if "claimed_by" in fm and fm.get("claimed_by") not in (None, ""):
            return _quarantine()

        # Required fields without safe defaults must quarantine when missing.
        missing_required = {"id", "title", "status", "created", "updated"} - set(fm)
        if missing_required:
            return _quarantine()

        # Other missing fields → apply safe defaults
        changed = False
        configured_priorities = _configured_priorities(config)
        for field, default in _SAFE_DEFAULTS.items():
            if field not in fm:
                fm[field] = configured_priorities[0] if field == "priority" else default
                changed = True

        if not changed:
            return RepairOutcome(
                task_id=task_id,
                file_path=str(path),
                code=code_name,
                action="fixed",
                detail="no changes needed",
            )

        return _write_repaired(path, fm, body_text, code_name, task_id)

    # Mode 4: type mismatch
    if code_name == ERR_CORRUPT_TYPE_MISMATCH.__name__:
        id_val = fm.get("id")
        if isinstance(id_val, str):
            if id_val.isdigit():
                fm["id"] = int(id_val)
                task_id = int(id_val)
            else:
                return _quarantine()

        blocked_val = fm.get("blocked")
        if isinstance(blocked_val, str):
            lower = blocked_val.lower()
            if lower == "true":
                fm["blocked"] = True
            elif lower == "false":
                fm["blocked"] = False
            else:
                return _quarantine()

        return _write_repaired(path, fm, body_text, code_name, task_id)

    # Mode 9: invalid priority → coerce to first configured priority
    if code_name == ERR_CORRUPT_INVALID_PRIORITY.__name__:
        fm["priority"] = _configured_priorities(config)[0]
        return _write_repaired(path, fm, body_text, code_name, task_id)

    # Unknown code
    return _quarantine()


def _write_repaired(
    path: Path,
    fm: dict,
    body_text: str,
    code: str,
    task_id: int | None,
) -> RepairOutcome:
    """Serialise the repaired frontmatter back to *path* atomically."""
    try:
        from owlbear_kanban.yaml_rt import make_yaml  # noqa: PLC0415

        y = make_yaml()
        cm = CommentedMap(fm)
        stream = io.StringIO()
        y.dump(cm, stream)
        yaml_str = stream.getvalue()
        for key, value in fm.items():
            if value is None:
                pattern = rf"(?m)^{re.escape(str(key))}:\s*$"
                yaml_str = re.sub(pattern, f"{key}: null", yaml_str)
        new_content = f"---\n{yaml_str}---\n{body_text}"
        atomic_write(path, new_content)
        return RepairOutcome(
            task_id=task_id,
            file_path=str(path),
            code=code,
            action="fixed",
            detail="frontmatter repaired",
        )
    except Exception as exc:  # noqa: BLE001
        return RepairOutcome(
            task_id=task_id,
            file_path=str(path),
            code=code,
            action="failed",
            detail=f"write failed: {exc}",
        )


def scan_and_fix(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]:
    """Phase 1 of two-phase repair: file operations only, no AR task creation.

    Scans ``tasks/`` and ``archive/`` for corruption. For each corrupt file,
    applies auto-fix or quarantine. Does NOT create AR tasks (that's Phase 2
    in engine.repair_storage()).

    Handles mode 2 (duplicate IDs) by quarantining both duplicates.

    Args:
        kanban_dir: Root directory of the kanban board.
        config:     Loaded :class:`BoardConfig`.

    Returns:
        List of :class:`RepairOutcome` — items with action='quarantined' need AR tasks.
    """
    outcomes: list[RepairOutcome] = []

    tasks_dir = kanban_dir / config.paths.tasks_dir
    archive_dir = kanban_dir / config.paths.archive_dir

    # Collect all files
    task_files: list[Path] = []
    archive_files: list[Path] = []

    if tasks_dir.exists():
        task_files = [p for p in sorted(tasks_dir.glob("*.md")) if not p.name.startswith(".tmp-")]
    if archive_dir.exists():
        archive_files = [p for p in sorted(archive_dir.glob("*.md")) if not p.name.startswith(".tmp-")]

    # Mode 2: duplicate IDs — quarantine both
    id_to_paths: dict[int, list[Path]] = {}
    for p in task_files + archive_files:
        fid = _extract_file_id(p)
        if fid is not None:
            id_to_paths.setdefault(fid, []).append(p)

    quarantined_ids: set[int] = set()
    for fid, paths in id_to_paths.items():
        if len(paths) > 1:
            outcomes.extend(_repair_duplicate_set(paths, kanban_dir, tasks_dir, archive_dir))
            quarantined_ids.add(fid)

    # Scan remaining files (skip already quarantined IDs)
    for p in task_files + archive_files:
        fid = _extract_file_id(p)
        if fid in quarantined_ids:
            continue
        error = detect_corruption(p, config)
        if error is None:
            continue
        outcome = attempt_repair(p, error.code, config)
        outcomes.append(outcome)

    return outcomes


def _outcome_counts(outcomes: list[RepairOutcome]) -> dict[str, int]:
    counts = {"removed": 0, "moved": 0, "quarantined": 0, "skipped": 0, "failed": 0, "unresolved": 0}
    for outcome in outcomes:
        if outcome.action in counts:
            counts[outcome.action] += 1
        elif outcome.action == "fixed":
            counts["moved"] += 1
    return counts


def _task_health_after_repair(kanban_dir: Path, config: BoardConfig) -> TaskHealthResult:
    checked_paths: list[str] = []
    findings: list[TaskHealthFinding] = []
    for directory in (kanban_dir / config.paths.tasks_dir, kanban_dir / config.paths.archive_dir):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            checked_paths.append(str(path))
            findings.extend(collect_task_health_findings(path, config))
    return TaskHealthResult(
        findings=findings,
        repairable_count=sum(1 for finding in findings if finding.repairable),
        checked_paths=checked_paths,
    )


def _archive_reconciliation_outcome(path: Path, task_id: int | None, action: str, detail: str) -> RepairOutcome:
    return RepairOutcome(
        task_id=task_id,
        file_path=str(path),
        code="ARCHIVE_RECONCILIATION",
        action=action,
        detail=detail,
    )


def _reconcile_archived_task(
    path: Path,
    kanban_dir: Path,
    tasks_dir: Path,
    archive_dir: Path,
    all_paths_by_id: dict[int, list[Path]],
) -> list[RepairOutcome]:
    try:
        _, frontmatter, body = _read_frontmatter(path)
    except CorruptionError:
        return []
    if frontmatter.get("status") != "archived":
        return []

    task_id = frontmatter.get("id")
    destination = archive_dir / path.name
    if destination.exists():
        records = _read_duplicate_records([path, destination])
        if records is None:
            outcomes = [
                _archive_reconciliation_outcome(
                    path, task_id, "unresolved", "archive destination conflict could not be parsed"
                )
            ]
        else:
            duplicate_paths = all_paths_by_id.get(task_id, [path, destination])
            outcomes = _repair_duplicate_set(duplicate_paths, kanban_dir, tasks_dir, archive_dir)
    else:
        try:
            _, current_frontmatter, current_body = _read_frontmatter(path)
            if current_frontmatter != frontmatter or _normalize_body(current_body) != _normalize_body(body):
                outcomes = [_archive_reconciliation_outcome(path, task_id, "skipped", "candidate changed before move")]
            else:
                archive_dir.mkdir(parents=True, exist_ok=True)
                destination.hardlink_to(path)
                path.unlink()
                outcomes = [_archive_reconciliation_outcome(path, task_id, "moved", f"moved to {destination}")]
        except FileExistsError:
            outcomes = [
                _archive_reconciliation_outcome(path, task_id, "skipped", "archive destination appeared before move")
            ]
        except OSError as exc:
            outcomes = [_archive_reconciliation_outcome(path, task_id, "failed", f"archive move failed: {exc}")]
    return outcomes


def _reconcile_archived_tasks(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]:
    tasks_dir = kanban_dir / config.paths.tasks_dir
    archive_dir = kanban_dir / config.paths.archive_dir
    if not tasks_dir.exists():
        return []

    all_paths_by_id: dict[int, list[Path]] = {}
    for directory in (tasks_dir, archive_dir):
        if not directory.exists():
            continue
        for candidate in sorted(directory.glob("*.md")):
            file_id = _extract_file_id(candidate)
            if file_id is not None:
                all_paths_by_id.setdefault(file_id, []).append(candidate)

    outcomes: list[RepairOutcome] = []
    for path in sorted(tasks_dir.glob("*.md")):
        outcomes.extend(_reconcile_archived_task(path, kanban_dir, tasks_dir, archive_dir, all_paths_by_id))
    return outcomes


def repair_task_storage(kanban_dir: Path, config: BoardConfig) -> DeterministicRepairResult:
    """Run convergent repair and return terminal outcomes plus post-scan evidence."""
    started_at = datetime.now().astimezone()
    outcomes = scan_and_fix(kanban_dir, config)
    outcomes.extend(_reconcile_archived_tasks(kanban_dir, config))
    health = _task_health_after_repair(kanban_dir, config)
    unresolved = [finding for finding in health.findings if not finding.repairable]
    counts = _outcome_counts(outcomes)
    return DeterministicRepairResult(
        status="completed",
        started_at=started_at,
        completed_at=datetime.now().astimezone(),
        removed_count=counts["removed"],
        moved_count=counts["moved"],
        quarantined_count=counts["quarantined"],
        skipped_count=counts["skipped"],
        failed_count=counts["failed"],
        unresolved_count=counts["unresolved"] + len(unresolved),
        outcomes=outcomes,
        unresolved_findings=unresolved,
        task_health_result=health,
    )


def _extract_file_id(path: Path) -> int | None:
    """Extract the integer ID prefix from the filename, e.g. '1042-slug.md' → 1042."""
    name = path.stem  # filename without extension
    prefix = name.split("-")[0]
    try:
        return int(prefix)
    except ValueError:
        return None


def _is_archive_path(path: Path, config: BoardConfig) -> bool:
    """Return True if *path* is inside the archive directory."""
    return path.parent.name == Path(config.paths.archive_dir).name
