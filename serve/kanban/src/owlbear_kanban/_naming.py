"""Shared filename/path safety helpers for kanban storage modules."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING

from owlbear_kanban.errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

_WINDOWS_RESERVED: frozenset[str] = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)]
)


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


def validate_config_path_containment(path_value: str) -> None:
    """Reject config path strings that can escape the board directory."""
    if not path_value.strip():
        raise ConfigError(
            code="ERR_PATH_ESCAPE",
            user_message="Configured path must be a non-empty board-relative subdirectory.",
        )

    if (
        PurePosixPath(path_value).is_absolute()
        or PureWindowsPath(path_value).is_absolute()
    ):
        raise ConfigError(
            code="ERR_PATH_ESCAPE",
            user_message=(
                "Configured path must be board-relative and must not be absolute: "
                f"{path_value!r}"
            ),
        )

    posix_parts = PurePosixPath(path_value).parts
    windows_parts = PureWindowsPath(path_value).parts
    if any(part == ".." for part in (*posix_parts, *windows_parts)):
        raise ConfigError(
            code="ERR_PATH_ESCAPE",
            user_message=(
                "Configured path must be board-relative and must not contain '..': "
                f"{path_value!r}"
            ),
        )


def move_to_quarantine(task_path: Path, kanban_dir: Path) -> Path:
    """Move *task_path* to ``quarantine/``, creating the dir if absent."""
    if task_path.name.startswith(".") and task_path.name.endswith(".lock"):
        return task_path

    validate_path_containment(kanban_dir, task_path)

    quarantine_dir = kanban_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / task_path.name
    task_path.replace(dest)
    return dest
