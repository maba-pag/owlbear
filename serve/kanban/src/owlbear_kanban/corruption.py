"""Corruption detection and repair for kanban task files (Brief C §4).

Defines the 10 ERR_CORRUPT_* codes, CorruptionError, RepairOutcome,
detect_corruption(), attempt_repair(), and scan_and_fix().
"""

from __future__ import annotations

import io
import re
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from owlbear_kanban._naming import (
    make_task_filename,
    move_to_quarantine,
)
from owlbear_kanban.errors import KanbanError
from owlbear_kanban.models import RepairOutcome
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


def scan_and_fix(kanban_dir: Path, config: BoardConfig) -> list[RepairOutcome]:  # noqa: C901, PLR0912
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
            # Check if same ID exists in both tasks/ and archive/ (mode 7)
            in_tasks = [p for p in paths if p.parent == tasks_dir]
            in_archive = [p for p in paths if p.parent == archive_dir]
            if in_tasks and in_archive:
                # Mode 7: archive wins; remove tasks/ copy
                for tp in in_tasks:
                    outcome = attempt_repair(tp, ERR_CORRUPT_DUPLICATE_LOCATION, config)
                    outcomes.append(outcome)
            else:
                # Mode 2: duplicate ID in same directory — quarantine both
                quarantined_ids.add(fid)
                # This will raise from list_tasks; we log as quarantined
                for p in paths:
                    try:
                        qp = move_to_quarantine(p, kanban_dir)
                        outcomes.append(
                            RepairOutcome(
                                task_id=fid,
                                file_path=str(p),
                                code=ERR_CORRUPT_DUPLICATE_ID.__name__,
                                action="quarantined",
                                detail=f"duplicate ID {fid} quarantined to {qp}",
                            )
                        )
                    except Exception as exc:  # noqa: BLE001
                        outcomes.append(
                            RepairOutcome(
                                task_id=fid,
                                file_path=str(p),
                                code=ERR_CORRUPT_DUPLICATE_ID.__name__,
                                action="failed",
                                detail=str(exc),
                            )
                        )

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
    return path.parent.name == config.paths.archive_dir.split("/")[-1]
